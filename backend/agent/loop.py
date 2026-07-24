"""The agent loop (Instance A) — provider-neutral.

Drives the LLM (OpenAI backend today) through native tool use and yields the
frozen SSE event models from schemas.py. Instance B's redacting emitter serializes
these (and redacts secrets in tool_call/tool_result) before they leave the
process — the loop emits RAW.

The loop depends only on the `ChatBackend` interface (llm_client.py), so switching
providers never touches this file. Guards (rule 9 / NOTES #5): max_iterations per
turn; token usage + cost accumulated across iterations → `done` event + cost line.

Import as `backend.agent.loop` from the repo root.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any, Iterator

from ..schemas import (
    DoneEvent,
    ErrorEvent,
    SSEEvent,
    TokenEvent,
    ToolCallEvent,
    ToolResultEvent,
    Usage,
)
from .config import AgentConfig
from .llm_client import ChatBackend, LLMClient
from .prompts import SYSTEM_PROMPT
from .tools_spec import TOOL_DEFS, dispatch


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_turn(
    messages: list[dict[str, Any]],
    client: ChatBackend | None = None,
    system: str = SYSTEM_PROMPT,
) -> Iterator[SSEEvent]:
    """Run one conversational turn to completion (through any tool calls).

    `messages` is the running conversation history (native provider message dicts);
    it is APPENDED to in place (assistant turns + tool-result turns) so the caller
    keeps the updated history. Yields SSEEvent objects: token / tool_call /
    tool_result / error, then exactly one done event with cumulative usage + cost.
    """
    client = client or LLMClient()
    cfg: AgentConfig = client.config

    total_in = 0
    total_out = 0
    total_cost = 0.0
    iterations = 0

    try:
        for iterations in range(1, cfg.max_iterations + 1):
            with client.stream(messages, system=system, tools=TOOL_DEFS) as stream:
                for delta in stream:
                    yield TokenEvent(text=delta)
                res = stream.result()

            total_in += res.usage["in_tokens"]
            total_out += res.usage["out_tokens"]
            total_cost += res.usage["cost_usd"]

            messages.append(res.assistant_message)

            if res.finish_reason != "tool_calls" or not res.tool_calls:
                break  # natural end of turn

            for tc in res.tool_calls:
                yield ToolCallEvent(id=tc.id, name=tc.name, params=tc.args, ts=_now())
                result = dispatch(tc.name, tc.args)
                yield ToolResultEvent(id=tc.id, name=tc.name, result_raw=result, ts=_now())
                messages.append(
                    client.tool_result_message(
                        tc.id,
                        json.dumps(result, ensure_ascii=False),
                        bool(isinstance(result, dict) and result.get("error")),
                    )
                )
        else:
            yield ErrorEvent(
                message=f"iteration guard: stopped after {cfg.max_iterations} tool rounds"
            )
    except Exception as e:  # noqa: BLE001 — surface API/network failure, still emit done
        yield ErrorEvent(message=f"agent error: {e}")

    print(
        f"[turn] model={cfg.model} iters={iterations} "
        f"in={total_in} out={total_out} cost=${total_cost:.4f}",
        file=sys.stderr,
        flush=True,
    )
    yield DoneEvent(
        usage=Usage(in_tokens=total_in, out_tokens=total_out, cost_usd=round(total_cost, 6))
    )


if __name__ == "__main__":
    # Live end-to-end smoke: one Bangla planning turn (needs OPENAI_API_KEY).
    history: list[dict[str, Any]] = [
        {"role": "user", "content": "রাজশাহীতে আমার জমির জন্য আবহাওয়া দেখে পরামর্শ দাও।"}
    ]
    for ev in run_turn(history):
        if isinstance(ev, TokenEvent):
            print(ev.text, end="", flush=True)
        elif isinstance(ev, ToolCallEvent):
            print(f"\n  → tool_call {ev.name}({ev.params})")
        elif isinstance(ev, ToolResultEvent):
            keys = list(ev.result_raw)[:5] if isinstance(ev.result_raw, dict) else ev.result_raw
            print(f"  ← tool_result {ev.name}: {keys}")
        elif isinstance(ev, ErrorEvent):
            print(f"\n[error] {ev.message}")
        elif isinstance(ev, DoneEvent):
            print(f"\n[done] {ev.usage.model_dump()}")
