"""The agent loop (Instance A) — provider-neutral, with a session-aware async
entrypoint matching B's frozen API contract.

Two layers:
  * `run_turn_sync` — the pure engine. Drives the LLM (OpenAI backend today)
    through native tool use and yields the frozen SSE event models from
    schemas.py. Takes an explicit `messages` list (native provider history)
    and appends to it in place.
  * `run_turn` — the real entrypoint B's `/api/chat` imports (see
    backend/api/chat.py): `async def run_turn(session_id, farm_id, message)
    -> AsyncIterator[dict]`. Loads the session's history from
    backend/memory/store.py, runs the sync engine (bridged onto a worker
    thread so the blocking OpenAI call never stalls FastAPI's event loop),
    saves the updated history back, and yields PLAIN DICTS. tool_call/
    tool_result are built via B's `sse.tool_call`/`sse.tool_result` so
    redaction happens by construction (CLAUDE.md rule 5) — this file does not
    reimplement redaction.

`farm_id` is accepted (matches the contract) but not yet used to seed context
— returning-farmer memory injection is a Tier 1 follow-up, not built here;
tracked honestly rather than half-wired.

Guards (rule 9 / NOTES #5): max_iterations per turn; token usage + cost
accumulated across iterations -> `done` event + cost line.

Import as `backend.agent.loop` from the repo root.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Iterator

from ..schemas import (
    DoneEvent,
    ErrorEvent,
    FinanceProjection,
    FinanceUpdateEvent,
    PlanUpdateEvent,
    SeasonPlan,
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


def _panel_event(tool_name: str, result: Any) -> SSEEvent | None:
    """Turn a tool result into a panel-update event, when it is one.

    Some tools produce structured objects the UI renders in a tab rather than
    prose the model narrates. Emitting those directly means the Finance and
    Plan tabs fill from the tool's own output — the same numbers the trace
    shows — instead of from anything the model retypes.

    Returns None for everything else, and never raises: a malformed result must
    cost us a panel update, not the turn.
    """
    if not isinstance(result, dict) or result.get("error"):
        return None
    try:
        if tool_name == "finance_projection" and "projection" in result:
            return FinanceUpdateEvent(
                finance=FinanceProjection.model_validate(result["projection"])
            )
        if tool_name == "season_plan" and "plan" in result:
            return PlanUpdateEvent(plan=SeasonPlan.model_validate(result["plan"]))
    except Exception:  # noqa: BLE001 — a bad shape loses the panel, not the turn
        return None
    return None


def run_turn_sync(
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
                # A costing is structured data, not just narration material: the
                # Finance tab renders it from this event while the model is
                # still writing its Bangla summary.
                panel = _panel_event(tc.name, result)
                if panel is not None:
                    yield panel
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


_SENTINEL = object()


async def _sync_iter_to_async(sync_gen: Iterator[Any]) -> AsyncIterator[Any]:
    """Bridge a blocking sync generator into an async iterator without stalling
    the event loop: each `next()` call (including the blocking OpenAI stream
    read inside it) runs in a worker thread via asyncio.to_thread."""
    it = iter(sync_gen)

    def _next() -> Any:
        try:
            return next(it)
        except StopIteration:
            return _SENTINEL

    while True:
        item = await asyncio.to_thread(_next)
        if item is _SENTINEL:
            return
        yield item


async def run_turn(
    session_id: str,
    farm_id: str | None,
    message: str,
    client: ChatBackend | None = None,
) -> AsyncIterator[dict]:
    """The real agent entrypoint — this is what backend/api/chat.py imports.

    Loads `session_id`'s stored conversation history, appends `message`, runs
    the pure engine, persists the updated history, and yields plain dicts on
    the exact PLAN §2 wire shape. tool_call/tool_result go through B's
    sse.tool_call/sse.tool_result (redaction is structural there, never
    reimplemented here — CLAUDE.md rule 5); every other event is
    `.model_dump()`'d directly from its pydantic SSEEvent.
    """
    from ..api import sse  # B's redacting constructors (import, not reimplement)
    from ..memory.store import get_session_messages, save_session_messages

    messages = get_session_messages(session_id)
    messages.append({"role": "user", "content": message})

    async for event in _sync_iter_to_async(run_turn_sync(messages, client=client)):
        if isinstance(event, ToolCallEvent):
            yield sse.tool_call(event.id, event.name, event.params)
        elif isinstance(event, ToolResultEvent):
            yield sse.tool_result(event.id, event.name, event.result_raw)
        elif isinstance(event, TokenEvent):
            yield sse.token(event.text)
        elif isinstance(event, ErrorEvent):
            yield sse.error(event.message)
        elif isinstance(event, DoneEvent):
            yield sse.done(event.usage.in_tokens, event.usage.out_tokens, event.usage.cost_usd)
        else:
            yield event.model_dump()  # plan_update/finance_update/alert/input_request

    save_session_messages(session_id, messages)


if __name__ == "__main__":
    # Live end-to-end smoke: one Bangla planning turn (needs OPENAI_API_KEY).
    # Force UTF-8 stdout — Windows cp1252 can't print Bangla tokens / arrows.
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        pass
    history: list[dict[str, Any]] = [
        {"role": "user", "content": "রাজশাহীতে আমার জমির জন্য আবহাওয়া দেখে পরামর্শ দাও।"}
    ]
    for ev in run_turn_sync(history):
        if isinstance(ev, TokenEvent):
            print(ev.text, end="", flush=True)
        elif isinstance(ev, ToolCallEvent):
            print(f"\n  -> tool_call {ev.name}({ev.params})")
        elif isinstance(ev, ToolResultEvent):
            keys = list(ev.result_raw)[:5] if isinstance(ev.result_raw, dict) else ev.result_raw
            print(f"  <- tool_result {ev.name}: {keys}")
        elif isinstance(ev, ErrorEvent):
            print(f"\n[error] {ev.message}")
        elif isinstance(ev, DoneEvent):
            print(f"\n[done] {ev.usage.model_dump()}")
