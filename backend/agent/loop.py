"""The agent loop (Instance A).

Drives Claude with native tool use and yields the frozen SSE event models from
schemas.py. Instance B's redacting emitter serializes these (and redacts secrets
in tool_call/tool_result) before they leave the process — the loop emits RAW.

Guards (CLAUDE.md rule 9 / NOTES #5):
  * max_iterations per turn (default 12) — hard stop on runaway tool loops.
  * token usage + cost_usd accumulated across iterations, reported in the `done`
    event AND printed to the console cost line.

Import layout: `backend` is the package root. Run/import as `backend.agent.loop`
from the repo root (e.g. `from backend.agent.loop import run_turn`).
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
from .llm_client import LLMClient, cached_system
from .prompts import SYSTEM_PROMPT
from .tools_spec import TOOL_DEFS, dispatch


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_turn(
    messages: list[dict[str, Any]],
    client: LLMClient | None = None,
    system: str = SYSTEM_PROMPT,
) -> Iterator[SSEEvent]:
    """Run one conversational turn to completion (through any tool calls).

    `messages` is the running conversation history; it is APPENDED to in place
    (assistant turns + tool_result turns) so the caller keeps the updated history
    for the next turn. Yields SSEEvent objects: token / tool_call / tool_result /
    error, then exactly one done event with cumulative usage + cost.
    """
    client = client or LLMClient()
    cfg: AgentConfig = client.config
    cached_sys = cached_system(system)

    total_in = 0
    total_out = 0
    total_cost = 0.0
    iterations = 0

    try:
        for iterations in range(1, cfg.max_iterations + 1):
            with client.stream(messages, system=cached_sys, tools=TOOL_DEFS) as stream:
                for event in stream:
                    if (
                        event.type == "content_block_delta"
                        and getattr(event.delta, "type", None) == "text_delta"
                    ):
                        yield TokenEvent(text=event.delta.text)
                    # thinking_delta is internal reasoning (English) — not streamed
                    # to the farmer-facing token channel.
                final = stream.get_final_message()

            # cost accounting for this iteration
            u = client.cost_from_usage(final.usage)
            total_in += u["in_tokens"]
            total_out += u["out_tokens"]
            total_cost += u["cost_usd"]

            # record the assistant turn (incl. tool_use / thinking blocks) verbatim
            messages.append({"role": "assistant", "content": final.content})

            tool_uses = [b for b in final.content if getattr(b, "type", None) == "tool_use"]
            if final.stop_reason != "tool_use" or not tool_uses:
                break  # natural end of turn

            # execute every requested tool, return all results in one user turn
            tool_result_blocks: list[dict[str, Any]] = []
            for tu in tool_uses:
                yield ToolCallEvent(id=tu.id, name=tu.name, params=dict(tu.input), ts=_now())
                result = dispatch(tu.name, dict(tu.input))
                yield ToolResultEvent(id=tu.id, name=tu.name, result_raw=result, ts=_now())
                tool_result_blocks.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "content": json.dumps(result, ensure_ascii=False),
                        "is_error": bool(isinstance(result, dict) and result.get("error")),
                    }
                )
            messages.append({"role": "user", "content": tool_result_blocks})
        else:
            # loop exhausted while still wanting tools — guard tripped
            yield ErrorEvent(
                message=f"iteration guard: stopped after {cfg.max_iterations} tool rounds"
            )
    except Exception as e:  # noqa: BLE001 — surface API/network failure, still emit done
        yield ErrorEvent(message=f"agent error: {e}")

    # console cost line (rule 9) + done event
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
    # Live end-to-end smoke: one Bangla planning turn (needs ANTHROPIC_API_KEY).
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
