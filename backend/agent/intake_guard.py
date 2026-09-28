"""Refuse to plan on farm facts the farmer never gave (CLAUDE.md rule 2).

Found live on 2026-09-28 (LOG4): an SMS that arrived garbled ("???? ...")
still produced a crop_scorer call with district=Dinajpur, soil=loam,
water=irrigated, season=rabi — every one of them invented by the model, and a
confident ranking came back to the farmer. The prompt already says "ask, don't
guess"; this makes it structural, like the digit filter and forced retrieval.

Before a planning tool runs, each intake field it received must be traceable
to something the farmer actually said or confirmed:
- the farmer's own messages (user turns, incl. USSD/SMS/voice transcripts and
  widget answers, which arrive as ordinary Bangla text), via the same
  deterministic extractor loop.py already runs, plus a district-name scan;
- the remembered farm profile the loop injects as a system note.

A field that fails is returned to the model as a tool error naming it, so the
agent asks (ask_farmer) instead of narrating a plan built on a guess. The
check is conservative on purpose: numbers (area, budget) are not checked here
because the extractor already feeds them and a false refusal on a number the
farmer typed differently would be worse than the risk it removes.
"""

from __future__ import annotations

import json
from typing import Any

PLANNING_TOOLS = {"crop_scorer", "finance_projection", "season_plan", "simulate_budget"}
CHECKED = ("district", "soil_type", "water_source", "season")
_PROFILE_PREFIX = "Known farm profile"


def _profile_from_messages(messages: list[dict[str, Any]]) -> dict:
    for m in messages:
        content = m.get("content")
        if m.get("role") == "system" and isinstance(content, str) and content.startswith(_PROFILE_PREFIX):
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("{"):
                    try:
                        return json.loads(line)
                    except ValueError:
                        pass
    return {}


def _user_texts(messages: list[dict[str, Any]]) -> list[str]:
    return [m["content"] for m in messages if m.get("role") == "user" and isinstance(m.get("content"), str)]


def known_facts(messages: list[dict[str, Any]]) -> tuple[dict[str, set[str]], str]:
    """-> ({field: {canonical values}}, all user text joined) from the history."""
    from .loop import extract_known_fields

    facts: dict[str, set[str]] = {f: set() for f in CHECKED}
    texts = _user_texts(messages)
    for text in texts:
        for field, value in extract_known_fields(text).items():
            if field in facts and value:
                facts[field].add(str(value))
    for field, value in _profile_from_messages(messages).items():
        if field in facts and value:
            facts[field].add(str(value))
    return facts, "\n".join(texts)


def _district_stated(value: str, facts: dict[str, set[str]], corpus: str) -> bool:
    from backend.tools.ask import DISTRICT_BN
    from backend.tools.districts import lookup_district

    hit = lookup_district(value)
    if not hit:
        return False  # the tool will refuse an unknown district itself
    canon = hit[0]
    if any((lookup_district(v) or ("",))[0] == canon for v in facts["district"]):
        return True
    names = {canon.lower(), DISTRICT_BN.get(canon, "")} - {""}
    low = corpus.lower()
    return any(n.lower() in low for n in names)


def unstated_fields(tool: str, params: dict[str, Any], messages: list[dict[str, Any]]) -> list[str]:
    """Intake fields in `params` that nothing the farmer said supports."""
    if tool not in PLANNING_TOOLS:
        return []
    facts, corpus = known_facts(messages)
    missing = []
    for field in CHECKED:
        value = params.get(field)
        if value in (None, ""):
            continue
        if field == "district":
            if not _district_stated(str(value), facts, corpus):
                missing.append(field)
        elif str(value) not in facts[field]:
            missing.append(field)
    return missing


def refusal(fields: list[str]) -> dict:
    return {
        "error": "unstated intake fields",
        "fields": fields,
        "detail": (
            "The farmer has not stated these in this conversation or their saved profile: "
            f"{', '.join(fields)}. Do not guess them and do not present any plan. Call "
            "ask_farmer for the first one (or confirm what you understood), then retry."
        ),
    }
