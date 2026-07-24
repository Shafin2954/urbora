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

For a fresh session, `farm_id` is injected as an authoritative server note so
tools that persist a plan cannot substitute a model-invented identifier. Returning
farm-profile injection remains a later enhancement.

Guards (rule 9 / NOTES #5): max_iterations per turn; token usage + cost
accumulated across iterations -> `done` event + cost line.

Import as `backend.agent.loop` from the repo root.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Iterator

from ..schemas import (
    DoneEvent,
    ErrorEvent,
    FinanceProjection,
    FinanceUpdateEvent,
    InputRequestEvent,
    PlanUpdateEvent,
    SeasonPlan,
    SSEEvent,
    TokenEvent,
    ToolCallEvent,
    ToolResultEvent,
    Usage,
)
from ..tools.ask import DISTRICT_BN
from ..tools.districts import ALIASES, DISTRICTS
from .config import AgentConfig
from .llm_client import ChatBackend, LLMClient
from .prompts import SYSTEM_PROMPT
from .tools_spec import TOOL_DEFS, dispatch


# ─────────────────────────────────────────────────────────────────────────────
# Deterministic intake extraction (CLAUDE.md rule 2's spirit applied to intake:
# a regex is more reliable than prompt-hoping that the model will notice six
# fields buried in one dense Bangla sentence). This is a mechanical parse, NOT
# an inference engine — it only returns a field when an explicit keyword or
# number+unit pattern matches, never a guess or a default. Absence from the
# returned dict means "not detected in this message", not "confirmed empty";
# the model still owns asking about anything genuinely missing (prompts.py's
# intake section), this just gives it an authoritative answer for what it can
# stop asking about. Traceable: every value here is copied verbatim from the
# farmer's own words (mapped through a fixed table), never invented.
#
# Bangla synonym source: prompts.py's own intake section ("Extract fields the
# farmer already stated") plus schemas.py's SoilType/WaterSource/Season
# literals — keep this table in sync with those if either changes.
# ─────────────────────────────────────────────────────────────────────────────

_BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def _bn_to_western_digits(text: str) -> str:
    return text.translate(_BN_DIGITS)


# Bangla district name -> canonical English name (from the intake widget's own
# label table, so extraction and the ask_farmer dropdown never disagree).
_DISTRICT_BN_TO_EN: list[tuple[str, str]] = sorted(
    ((bn, en) for en, bn in DISTRICT_BN.items()),
    key=lambda pair: len(pair[0]),
    reverse=True,
)
# English canonical names + known alias spellings, longest first so "Cox's
# Bazar" is tried before any shorter accidental overlap.
_DISTRICT_EN_NAMES: list[tuple[str, str]] = sorted(
    [(name, name) for name in DISTRICTS] + [(alias, canon) for alias, canon in ALIASES.items()],
    key=lambda pair: len(pair[0]),
    reverse=True,
)

# Compound soil terms MUST be checked before their substrings ("এঁটেল দোআঁশ"
# contains both "এঁটেল" and "দোআঁশ"; matching in this order keeps the exact
# mapping prompts.py documents).
_SOIL_TERMS: list[tuple[str, str]] = [
    ("এঁটেল দোআঁশ", "clay_loam"),
    ("বেলে দোআঁশ", "sandy_loam"),
    ("দোআঁশ", "loam"),
    ("এঁটেল", "clay"),
    ("বেলে", "sandy"),
    ("পলি মাটি", "silt"),
    ("পিট মাটি", "peat"),
    ("clay loam", "clay_loam"),
    ("clay_loam", "clay_loam"),
    ("sandy loam", "sandy_loam"),
    ("sandy_loam", "sandy_loam"),
    ("loam", "loam"),
    ("clay", "clay"),
    ("sandy", "sandy"),
    ("silt", "silt"),
    ("peat", "peat"),
]

_WATER_TERMS: list[tuple[str, str]] = [
    ("গভীর নলকূপ", "tubewell"),
    ("অগভীর নলকূপ", "tubewell"),
    ("নলকূপ", "tubewell"),
    ("বৃষ্টি নির্ভর", "rainfed"),
    ("বৃষ্টিনির্ভর", "rainfed"),
    ("বৃষ্টি-নির্ভর", "rainfed"),
    ("খাল", "canal"),
    ("সেচ", "irrigated"),
    ("tubewell", "tubewell"),
    ("rainfed", "rainfed"),
    ("canal", "canal"),
    ("irrigated", "irrigated"),
    ("irrigation", "irrigated"),
]

_SEASON_TERMS: list[tuple[str, str]] = [
    ("খরিপ-১", "kharif1"), ("খরিপ ১", "kharif1"), ("খরিপ১", "kharif1"),
    ("খরিপ-২", "kharif2"), ("খরিপ ২", "kharif2"), ("খরিপ২", "kharif2"),
    ("রবি", "rabi"),
    ("kharif1", "kharif1"), ("kharif 1", "kharif1"), ("kharif-1", "kharif1"),
    ("kharif2", "kharif2"), ("kharif 2", "kharif2"), ("kharif-2", "kharif2"),
    ("rabi", "rabi"),
]

# (search term, canonical unit key) — matched against western-digit text via
# the regex below, longest-first so "hectare" beats "ha", etc.
_AREA_UNIT_TERMS: list[tuple[str, str]] = sorted(
    [
        ("বিঘা", "bigha"), ("কাঠা", "katha"), ("শতাংশ", "decimal"),
        ("শতক", "decimal"), ("একর", "acre"), ("হেক্টর", "hectare"),
        ("bigha", "bigha"), ("bighas", "bigha"), ("katha", "katha"),
        ("decimal", "decimal"), ("decimals", "decimal"), ("hectare", "hectare"),
        ("hectares", "hectare"), ("acre", "acre"), ("acres", "acre"), ("ha", "hectare"),
    ],
    key=lambda pair: len(pair[0]),
    reverse=True,
)
_AREA_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(" + "|".join(re.escape(t) for t, _ in _AREA_UNIT_TERMS) + r")",
    re.IGNORECASE,
)
_AREA_UNIT_MAP = dict(_AREA_UNIT_TERMS)

# Budget: digits immediately followed by a money word. Deliberately does not
# fire on a bare number (e.g. an area or a phone number) — the money keyword
# is required, so it never invents a budget from an unrelated figure.
_BUDGET_RE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(?:টাকা|taka|tk\.?|bdt)", re.IGNORECASE)


def extract_known_fields(text: str) -> dict[str, Any]:
    """Pull already-stated intake fields out of one farmer message.

    Returns a dict with any subset of: district, area, area_unit, soil_type,
    water_source, season, budget_bdt. Only includes a key when an explicit
    keyword or number+unit pattern matched — never a default, never a guess.
    Used to inject an authoritative "already known" system note (mirrors the
    farm-memory note this module already injects for get_farm) so the model
    stops re-asking for fields the farmer just typed, without relying on the
    model to notice all six itself in one dense sentence.
    """
    if not text or not text.strip():
        return {}
    western = _bn_to_western_digits(text)
    lower = western.lower()
    found: dict[str, Any] = {}

    for bn_name, en_name in _DISTRICT_BN_TO_EN:
        if bn_name in text:
            found["district"] = en_name
            break
    else:
        for name, canon in _DISTRICT_EN_NAMES:
            if name.lower() in lower:
                found["district"] = canon
                break

    m = _AREA_RE.search(western)
    if m:
        unit_key = _AREA_UNIT_MAP.get(m.group(2).lower())
        if unit_key:
            try:
                found["area"] = float(m.group(1))
                found["area_unit"] = unit_key
            except ValueError:
                pass

    for term, key in _SOIL_TERMS:
        if term in text or term.lower() in lower:
            found["soil_type"] = key
            break

    for term, key in _WATER_TERMS:
        if term in text or term.lower() in lower:
            found["water_source"] = key
            break

    for term, key in _SEASON_TERMS:
        if term in text or term.lower() in lower:
            found["season"] = key
            break

    m = _BUDGET_RE.search(western)
    if m:
        try:
            found["budget_bdt"] = float(m.group(1).replace(",", ""))
        except ValueError:
            pass

    return found


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
            plan = SeasonPlan.model_validate(result["plan"])
            from backend.memory.store import save_plan
            save_plan(plan.farm_id, plan.model_dump())
            return PlanUpdateEvent(plan=plan)
        if tool_name == "check_plan_conflicts" and result.get("alerts"):
            from ..schemas import AlertEvent
            return AlertEvent(alert=result["alerts"][0])
        # The intake widget (PRD §8 Tier0.1). The tool validates and shapes it;
        # this is where it becomes the event the UI has been able to render
        # since H2 but never received.
        if tool_name == "ask_farmer" and "input_request" in result:
            return InputRequestEvent.model_validate(result["input_request"])
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
                    # CLAUDE.md rule 10: numerals reaching the client are ALWAYS
                    # Western, even though prompts.py tells the model this and the
                    # model does not reliably comply (same lesson as ask_farmer —
                    # prompt-only guarantees don't hold under this loop). Enforced
                    # here, deterministically, at the point each streamed chunk
                    # leaves the loop — not a whole-message regex, because the
                    # message isn't whole yet.
                    #
                    # Safe under streaming because Bangla->Western digit mapping is
                    # a PER-CHARACTER, CONTEXT-FREE substitution (str.translate on
                    # single Unicode code points ০-৯, no multi-char sequences, no
                    # reordering, no lookahead): translating "৮২" then ".৬৪" in two
                    # separate chunks yields the same "82" + ".64" as translating
                    # "৮২.৬৪" whole. A number split across a chunk boundary is
                    # therefore translated correctly either way. `delta` is already
                    # a decoded Python str by the time it reaches here (the OpenAI
                    # SDK never hands us a chunk mid-UTF-8-codepoint), so there is
                    # no partial-character risk to guard against either.
                    # Only digit GLYPHS are in the translation table — Bangla words
                    # and punctuation pass through untouched.
                    yield TokenEvent(text=_bn_to_western_digits(delta))
                res = stream.result()

            total_in += res.usage["in_tokens"]
            total_out += res.usage["out_tokens"]
            total_cost += res.usage["cost_usd"]

            messages.append(res.assistant_message)

            if res.finish_reason != "tool_calls" or not res.tool_calls:
                break  # natural end of turn

            for tc in res.tool_calls:
                # Retrieval is a required evidence step, not a best-effort model
                # habit. The model receives the cited passages before it sees
                # the deterministic recommendation/calendar result, and both
                # calls are visible in the judge trace.
                retrieval_result: dict | None = None
                if tc.name in {"crop_scorer", "season_plan"}:
                    crop = tc.args.get("crop")
                    if tc.name == "crop_scorer":
                        query = (
                            f"{tc.args.get('season', 'target')} season crop suitability "
                            f"soil {tc.args.get('soil_type', '')} water {tc.args.get('water_source', '')}"
                        )
                    else:
                        query = "crop calendar fertilizer irrigation weed pest checkpoints harvest"
                    retrieval_id = f"retrieval-{tc.id}"
                    retrieval_params = {"query": query, **({"crop": crop} if crop else {})}
                    yield ToolCallEvent(id=retrieval_id, name="rag_query", params=retrieval_params, ts=_now())
                    retrieval_result = dispatch("rag_query", retrieval_params)
                    yield ToolResultEvent(
                        id=retrieval_id, name="rag_query", result_raw=retrieval_result, ts=_now(),
                    )
                yield ToolCallEvent(id=tc.id, name=tc.name, params=tc.args, ts=_now())
                result = dispatch(tc.name, tc.args)
                if isinstance(result, dict) and isinstance(retrieval_result, dict):
                    # The model receives the exact retrieved passages alongside
                    # the deterministic result it is about to narrate.
                    result["kb_evidence"] = retrieval_result.get("matches", [])
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
    from ..api import sse  # the redacting constructors (import, not reimplement)
    from ..memory.store import get_farm, get_session_messages, save_session_messages

    messages = get_session_messages(session_id)

    # Memory recall (PRD §4, judged behaviour; PLAN §5 opens the demo on it).
    # A stored farm is injected once, at the start of a fresh session, as a
    # system note — not as words in the farmer's mouth. Only on a fresh session
    # because the history already carries it after the first turn, and repeating
    # it every turn burns tokens and drifts the context.
    if farm_id and not messages:
        # The farm id is server-authored session context. Tool calls must carry
        # this exact opaque value; the model must never invent or abbreviate it.
        remembered = get_farm(farm_id)
        if remembered:
            note = (
                "Known farm profile for this farmer, from memory of an earlier "
                "session. Greet them by acknowledging what you already know and "
                "do NOT re-ask these fields; confirm rather than interrogate. Ask "
                f"only for what is missing.\n{json.dumps(remembered, ensure_ascii=False)}\n"
            )
        else:
            note = ""
        note += (
            f"Authoritative farm_id for this session: {farm_id!r}. "
            "When a tool requires farm_id, copy this value exactly."
        )
        messages.append({"role": "system", "content": note})

    # Deterministic intake extraction (see extract_known_fields above). Runs on
    # every turn, not just the first — a farmer can state a missing field in
    # any message. Only injects a note when something was actually detected.
    extracted = extract_known_fields(message)
    if extracted:
        messages.append({
            "role": "system",
            "content": (
                "Deterministic extraction (a regex parse, not the model) found "
                "these fields already stated in the farmer's next message, "
                "mapped to canonical field names/values. Do NOT call ask_farmer "
                "for any field listed here — treat it as known and confirm it "
                "in passing instead. This is a mechanical parse and can miss "
                "things a careful read would catch, so still read the farmer's "
                "own words, and still ask (with ask_farmer) about any of "
                "district / area+area_unit / soil_type / water_source / "
                "budget_bdt / season that is NOT listed here and not already "
                "known from earlier in this conversation.\n"
                f"{json.dumps(extracted, ensure_ascii=False)}"
            ),
        })

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
