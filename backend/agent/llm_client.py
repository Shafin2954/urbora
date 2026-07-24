"""
LLM client abstraction — Claude Sonnet primary, swappable.

Why an abstraction and not raw anthropic calls scattered around:
  * ONE place resolves the model (env-var switch only, PRD §11).
  * ONE place computes per-turn token usage + cost_usd for the `done` event and
    console line (CLAUDE.md rule 9 / NOTES #5 — two Pro accounts are not infinite).
  * ONE place applies prompt caching on the static system prompt.
  * A thin ChatBackend Protocol keeps the door open for a second provider without
    touching the agent loop. Concrete impl today: Claude via the anthropic SDK.

The agent loop (next block) drives this; it never talks to anthropic directly.
"""

from __future__ import annotations

from typing import Any, Protocol

import anthropic

from .config import AgentConfig

# ─────────────────────────────────────────────────────────────────────────────
# Pricing (USD per 1M tokens) for the `done` event / cost line. Standard rates —
# deliberately not the intro discount, so the cost line over-estimates rather than
# under-estimates what the credits burn. Update if a model is swapped in.
# cache read  = 0.10x input ; cache write (5m) = 1.25x input.
# ─────────────────────────────────────────────────────────────────────────────
_PRICING: dict[str, tuple[float, float]] = {
    "claude-sonnet-5": (3.0, 15.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-opus-4-7": (5.0, 25.0),
    "claude-haiku-4-5": (1.0, 5.0),
}
_CACHE_READ_MULT = 0.10
_CACHE_WRITE_MULT = 1.25


def _rates_for(model: str) -> tuple[float, float]:
    if model in _PRICING:
        return _PRICING[model]
    for key, rate in _PRICING.items():          # prefix fallback for dated/variant ids
        if model.startswith(key):
            return rate
    return _PRICING["claude-sonnet-5"]           # safe default; log if this fires


class ChatBackend(Protocol):
    """Minimal surface the agent loop depends on. Swap Claude for another provider
    by implementing this; the loop stays unchanged."""

    def stream(
        self,
        messages: list[dict[str, Any]],
        system: str | list[dict[str, Any]] | None = ...,
        tools: list[dict[str, Any]] | None = ...,
        tool_choice: dict[str, Any] | None = ...,
    ) -> Any: ...

    def cost_from_usage(self, usage: Any) -> dict[str, Any]: ...


def cached_system(text: str) -> list[dict[str, Any]]:
    """Wrap a static system prompt as a single cache-controlled block.

    The system prompt is large and identical across turns → cache it so repeated
    turns pay ~0.1x for the prefix instead of full price. Keep it byte-stable:
    never interpolate timestamps / session ids into it (that silently breaks the
    cache). Volatile context goes into `messages`, not here.
    """
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]


class LLMClient:
    """Claude-backed ChatBackend."""

    def __init__(self, config: AgentConfig | None = None) -> None:
        self.config = config or AgentConfig.from_env()
        # anthropic() also resolves ANTHROPIC_API_KEY from env; pass explicitly
        # when config carries it so a caller-injected key wins.
        self._client = anthropic.Anthropic(api_key=self.config.api_key or None)

    @property
    def model(self) -> str:
        return self.config.model

    # ── request assembly ────────────────────────────────────────────────────
    def _base_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "output_config": {"effort": self.config.effort},
        }
        if self.config.thinking == "adaptive":
            # summarized display gives the trace visible "reasoning" progress
            # during streaming; billing is identical to omitted.
            kwargs["thinking"] = {"type": "adaptive", "display": "summarized"}
        elif self.config.thinking == "off":
            kwargs["thinking"] = {"type": "disabled"}
        return kwargs

    def stream(
        self,
        messages: list[dict[str, Any]],
        system: str | list[dict[str, Any]] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | None = None,
    ):
        """Return the anthropic streaming context manager.

        Usage:
            with client.stream(messages, system=sys, tools=tools) as stream:
                for event in stream:
                    ...
                final = stream.get_final_message()
        Streaming is mandatory here — max_tokens can be large and non-streaming
        risks HTTP timeouts.
        """
        kwargs = self._base_kwargs()
        kwargs["messages"] = messages
        if system is not None:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice
        return self._client.messages.stream(**kwargs)

    # ── cost accounting for the `done` event (rule 9) ─────────────────────────
    def cost_from_usage(self, usage: Any) -> dict[str, Any]:
        """Turn an anthropic usage object into {in_tokens, out_tokens, cost_usd}.

        in_tokens = every prompt token billed this turn (fresh + cache read +
        cache write). out_tokens = generated tokens. cost_usd applies the correct
        per-category rate.
        """
        in_rate, out_rate = _rates_for(self.config.model)

        def _get(name: str) -> int:
            return int(getattr(usage, name, 0) or 0)

        fresh_in = _get("input_tokens")
        cache_read = _get("cache_read_input_tokens")
        cache_write = _get("cache_creation_input_tokens")
        out = _get("output_tokens")

        cost = (
            fresh_in / 1e6 * in_rate
            + cache_read / 1e6 * in_rate * _CACHE_READ_MULT
            + cache_write / 1e6 * in_rate * _CACHE_WRITE_MULT
            + out / 1e6 * out_rate
        )
        return {
            "in_tokens": fresh_in + cache_read + cache_write,
            "out_tokens": out,
            "cost_usd": round(cost, 6),
        }


if __name__ == "__main__":
    # Offline sanity print — no API call, safe without a key.
    cfg = AgentConfig.from_env()
    client = LLMClient(cfg)
    print("AgriSense LLM client")
    print(f"  model          : {client.model}")
    print(f"  max_tokens     : {cfg.max_tokens}")
    print(f"  effort         : {cfg.effort}")
    print(f"  thinking       : {cfg.thinking}")
    print(f"  max_iterations : {cfg.max_iterations}")
    print(f"  api_key set    : {bool(cfg.api_key)}")

    class _FakeUsage:
        input_tokens = 1200
        cache_read_input_tokens = 8000
        cache_creation_input_tokens = 0
        output_tokens = 350

    print(f"  sample cost    : {client.cost_from_usage(_FakeUsage())}")
