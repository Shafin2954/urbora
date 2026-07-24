"""
LLM client abstraction — OpenAI backend (swappable).

Provider is OpenAI (human A's call; deviates from PRD §11 — logged). The agent
loop depends only on the provider-neutral `ChatBackend` Protocol below, so the
loop / tools / prompts / frozen SSE schema are untouched by the provider swap.
A Claude backend could be dropped back in behind the same Protocol.

Responsibilities kept in ONE place:
  * resolve the model (env-var switch only).
  * translate our tool defs (Anthropic-style {name,description,input_schema})
    into OpenAI function tools.
  * stream text deltas + collect tool calls into a normalized TurnResult.
  * per-turn token usage + cost_usd for the `done` event / console cost line
    (CLAUDE.md rule 9). OpenAI prompt caching is automatic — no cache_control.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterator, Protocol

from openai import OpenAI

from .config import AgentConfig

# ─────────────────────────────────────────────────────────────────────────────
# Pricing (USD per 1M tokens) for the `done` event / cost line. VERIFY against
# your account + current date — OpenAI prices change. Unknown model → cost 0.0
# but token counts stay accurate (tokens are the real spend signal). cached input
# is billed lower; we approximate it at 0.5x input.
# ─────────────────────────────────────────────────────────────────────────────
_PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
}
_CACHE_READ_MULT = 0.5


def _rates_for(model: str) -> tuple[float, float]:
    if model in _PRICING:
        return _PRICING[model]
    for key, rate in _PRICING.items():
        if model.startswith(key):
            return rate
    return (0.0, 0.0)  # unknown → don't guess a price; tokens still reported


# ── normalized turn types (provider-neutral, what the loop sees) ──────────────
@dataclass
class NormToolCall:
    id: str
    name: str
    args: dict[str, Any]


@dataclass
class TurnResult:
    text: str
    tool_calls: list[NormToolCall]
    assistant_message: dict[str, Any]   # native (OpenAI) message to append to history
    finish_reason: str
    usage: dict[str, Any]               # {in_tokens, out_tokens, cost_usd}


class ChatBackend(Protocol):
    """Provider-neutral surface the agent loop depends on."""

    def stream(
        self,
        messages: list[dict[str, Any]],
        system: str,
        tools: list[dict[str, Any]] | None,
    ) -> "TurnStream": ...

    def tool_result_message(
        self, call_id: str, content: str, is_error: bool = ...
    ) -> dict[str, Any]: ...


def to_openai_tools(tool_defs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Anthropic-style {name,description,input_schema} → OpenAI function tools."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
            },
        }
        for t in tool_defs
    ]


@dataclass
class TurnStream:
    """Context manager: iterate for text deltas, then call .result().

        with backend.stream(messages, system, tools) as s:
            for delta in s:      # yields assistant text as it streams
                ...
            res = s.result()     # normalized TurnResult
    """

    _stream: Any
    _model: str
    _cost_fn: Any
    _text_parts: list[str] = field(default_factory=list)
    # tool calls accumulate by streamed index → {id,name,args_str}
    _tool_acc: dict[int, dict[str, str]] = field(default_factory=dict)
    _finish_reason: str = "stop"
    _usage_obj: Any = None

    def __enter__(self) -> "TurnStream":
        return self

    def __exit__(self, *exc: Any) -> None:
        close = getattr(self._stream, "close", None)
        if close:
            try:
                close()
            except Exception:  # noqa: BLE001
                pass

    def __iter__(self) -> Iterator[str]:
        for chunk in self._stream:
            if getattr(chunk, "usage", None):
                self._usage_obj = chunk.usage
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta
            if getattr(choice, "finish_reason", None):
                self._finish_reason = choice.finish_reason
            if getattr(delta, "content", None):
                self._text_parts.append(delta.content)
                yield delta.content
            for tc in getattr(delta, "tool_calls", None) or []:
                slot = self._tool_acc.setdefault(tc.index, {"id": "", "name": "", "args": ""})
                if tc.id:
                    slot["id"] = tc.id
                if tc.function and tc.function.name:
                    slot["name"] = tc.function.name
                if tc.function and tc.function.arguments:
                    slot["args"] += tc.function.arguments

    def result(self) -> TurnResult:
        text = "".join(self._text_parts)
        tool_calls: list[NormToolCall] = []
        native_tool_calls: list[dict[str, Any]] = []
        for idx in sorted(self._tool_acc):
            slot = self._tool_acc[idx]
            if not slot["name"]:
                continue
            raw_args = slot["args"].strip()
            try:
                args = json.loads(raw_args) if raw_args else {}
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(NormToolCall(id=slot["id"], name=slot["name"], args=args))
            native_tool_calls.append(
                {
                    "id": slot["id"],
                    "type": "function",
                    "function": {"name": slot["name"], "arguments": slot["args"] or "{}"},
                }
            )
        assistant: dict[str, Any] = {"role": "assistant", "content": text or None}
        if native_tool_calls:
            assistant["tool_calls"] = native_tool_calls
        return TurnResult(
            text=text,
            tool_calls=tool_calls,
            assistant_message=assistant,
            finish_reason=self._finish_reason,
            usage=self._cost_fn(self._usage_obj),
        )


class OpenAIClient:
    """OpenAI-backed ChatBackend (Chat Completions + function tools + streaming)."""

    def __init__(self, config: AgentConfig | None = None) -> None:
        self.config = config or AgentConfig.from_env()
        self._client = OpenAI(
            api_key=self.config.api_key or None,
            base_url=self.config.base_url,
        )

    @property
    def model(self) -> str:
        return self.config.model

    def stream(
        self,
        messages: list[dict[str, Any]],
        system: str,
        tools: list[dict[str, Any]] | None = None,
    ) -> TurnStream:
        full_messages = [{"role": "system", "content": system}, *messages]
        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "messages": full_messages,
            "max_tokens": self.config.max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if self.config.temperature is not None:
            kwargs["temperature"] = self.config.temperature
        if tools:
            kwargs["tools"] = to_openai_tools(tools)
            kwargs["tool_choice"] = "auto"
        stream = self._client.chat.completions.create(**kwargs)
        return TurnStream(_stream=stream, _model=self.config.model, _cost_fn=self.cost_from_usage)

    def tool_result_message(
        self, call_id: str, content: str, is_error: bool = False
    ) -> dict[str, Any]:
        # OpenAI tool result: role=tool, tool_call_id links back to the call.
        return {"role": "tool", "tool_call_id": call_id, "content": content}

    def cost_from_usage(self, usage: Any) -> dict[str, Any]:
        """OpenAI usage → {in_tokens, out_tokens, cost_usd}."""
        in_rate, out_rate = _rates_for(self.config.model)
        if usage is None:
            return {"in_tokens": 0, "out_tokens": 0, "cost_usd": 0.0}

        prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion = int(getattr(usage, "completion_tokens", 0) or 0)
        cached = 0
        details = getattr(usage, "prompt_tokens_details", None)
        if details is not None:
            cached = int(getattr(details, "cached_tokens", 0) or 0)
        fresh = max(prompt - cached, 0)

        cost = (
            fresh / 1e6 * in_rate
            + cached / 1e6 * in_rate * _CACHE_READ_MULT
            + completion / 1e6 * out_rate
        )
        return {"in_tokens": prompt, "out_tokens": completion, "cost_usd": round(cost, 6)}


# Backwards-compatible alias — existing imports of LLMClient keep working.
LLMClient = OpenAIClient


if __name__ == "__main__":
    from dataclasses import replace

    cfg = AgentConfig.from_env()
    # OpenAI() requires a key at construction; use a placeholder for the offline
    # print (cost_from_usage / tool translation never hit the network).
    client = OpenAIClient(cfg if cfg.api_key else replace(cfg, api_key="sk-offline-demo"))
    print("AgriSense LLM client (OpenAI backend)")
    print(f"  model          : {client.model}")
    print(f"  max_tokens     : {cfg.max_tokens}")
    print(f"  temperature    : {cfg.temperature}")
    print(f"  max_iterations : {cfg.max_iterations}")
    print(f"  api_key set    : {bool(cfg.api_key)}")
    print(f"  base_url       : {cfg.base_url}")

    class _FakeDetails:
        cached_tokens = 8000

    class _FakeUsage:
        prompt_tokens = 9200
        completion_tokens = 350
        prompt_tokens_details = _FakeDetails()

    print(f"  sample cost    : {client.cost_from_usage(_FakeUsage())}")
    print(f"  tool xlate     : {to_openai_tools([{'name':'x','description':'d','input_schema':{'type':'object'}}])[0]['type']}")
