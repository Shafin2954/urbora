"""Web crop-problem check: the keypad triage table, opened to the website (LOG4 2026-09-30).

    GET  /api/triage/options                 crops, stages, organs, symptoms, extents, weather
    POST /api/triage/check                   the farmer's answers -> KB-bounded candidates

Same deterministic table as USSD menu 2 (`backend/kb/triage.py`): the model is not involved,
and a combination the KB does not cover says so ("তথ্য যথেষ্ট নয়") instead of guessing.
The dose total for the farmer's land is computed by `units.scale_rate` and returned with a
Provenance object (CLAUDE.md rule 3). The web answer is structured, not the SMS text, so the
page shows each part with its source.

Traced like a tool (rule 5): the request and result go to the console trace as
`tool_call` / `tool_result` through the redacting emitter's `redact()`.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.kb import triage as T
from backend.units import scale_rate

from .redact import redact

router = APIRouter()
log = logging.getLogger("urbora.triage")

ORGAN_ICON = {"leaf": "🍃", "stem": "🌿", "sheath": "🌾", "root": "🪴", "panicle": "🌾",
              "tuber": "🥔", "pod": "🫛", "whole": "🌱"}


@router.get("/api/triage/options")
def options() -> dict:
    """Everything the step-by-step form needs, in the table's own order."""
    crops = []
    for key, name in T.CROPS:
        crops.append({
            "key": key, "name_bn": name,
            "days_basis": "after_transplanting" if key in T.RICE else "after_sowing",
            "stages": [{"key": s, "name_bn": bn, "days": [lo, hi]} for s, bn, lo, hi in T.STAGES[key]],
            "organs": [{"key": o, "name_bn": T.ORGAN_BN[o], "icon": ORGAN_ICON[o],
                        "symptoms": [{"key": s, "name_bn": T.SYMPTOM_BN[s]} for s in T.symptoms(key, o)]}
                       for o in T.organs(key)],
        })
    return {"crops": crops,
            "extents": [{"key": k, "name_bn": bn} for k, bn in T.EXTENTS],
            "weather": [{"key": k, "name_bn": bn} for k, bn in T.WEATHER]}


class CheckRequest(BaseModel):
    crop: str
    stage: str
    organ: str
    symptom: str
    extent: str = "little"
    weather: str = "none"
    area_bigha: float | None = Field(default=None, gt=0, le=1000)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _fmt(v: float) -> str:
    return T._fmt(v)


@router.post("/api/triage/check")
def check(req: CheckRequest) -> dict:
    if req.crop not in T.CROP_BN:
        raise HTTPException(400, "unknown crop")
    if req.stage not in {s[0] for s in T.STAGES[req.crop]}:
        raise HTTPException(400, "unknown stage for this crop")
    if req.organ not in T.organs(req.crop) or req.symptom not in T.symptoms(req.crop, req.organ):
        raise HTTPException(400, "unknown organ/symptom for this crop")
    if req.extent not in dict(T.EXTENTS) or req.weather not in dict(T.WEATHER):
        raise HTTPException(400, "unknown extent/weather")

    log.info("tool_call triage_check %s", redact(req.model_dump())[0])
    diag = T.diagnose(req.crop, req.stage, req.organ, req.symptom, req.extent, req.weather)
    corpus = T.corpus()
    shown = diag.candidates[:2]

    candidates = []
    for c in diag.candidates:
        p = corpus.get(c.kb_id, {})
        candidates.append({
            "key": c.key, "name_bn": c.name_bn, "coverage": c.coverage,
            "advice_bn": c.advice_bn if c.coverage != "P" else "",
            "source": {"kb_id": c.kb_id, "title": p.get("source_title"), "confidence": p.get("confidence")},
        })

    dose = None
    if diag.dose_allowed():
        top = diag.candidates[0]
        d = top.dose
        passage = corpus.get(d.kb_id, {})
        dose = {"text_bn": d.text_bn, "source": {"kb_id": d.kb_id, "title": passage.get("source_title")}}
        if d.amount is not None and d.per and req.area_bigha:
            total = scale_rate(d.amount, d.per, req.area_bigha, "bigha")
            dose["total"] = {
                "value": _fmt(total), "unit": d.unit_bn,
                "prov": {"value": _fmt(total), "unit": d.unit_bn, "source_type": "computed",
                         "source_id": d.kb_id, "source_title": passage.get("source_title") or d.kb_id,
                         "locator": f"{d.amount:g} {d.unit_bn} / {d.per}",
                         "formula": f"units.scale_rate({d.amount:g}, '{d.per}', {req.area_bigha:g}, 'bigha')",
                         "retrieved_at": _now(), "confidence": "high"},
            }
            if d.water_l:
                dose["water_l"] = _fmt(scale_rate(d.water_l, d.per, req.area_bigha, "bigha"))

    safety = []
    if shown and any(c.spray for c in shown):
        safety = [T.SAAO_LINE, T.GEAR_LINE]
    elif shown:
        safety = ["সন্দেহ হলে স্থানীয় কৃষি অফিসার (SAAO)-কে দেখান।"]
    if req.extent == "most" and shown:
        safety.insert(0, "প্রায় পুরো জমিতে হলে দেরি না করে SAAO-কে দেখান।")

    _, s_bn, lo, hi = T.stage(req.crop, req.stage)
    result = {
        "summary_bn": f"{T.CROP_BN[req.crop]} ({s_bn}), {T.ORGAN_BN[req.organ]}: {T.SYMPTOM_BN[req.symptom]}",
        "coverage": diag.coverage,
        "candidates": candidates,
        "no_kb_bn": "তথ্য যথেষ্ট নয়: এই লক্ষণের যাচাই করা তথ্য আমাদের কাছে নেই। স্থানীয় উপসহকারী কৃষি কর্মকর্তা (SAAO)-কে দেখান।" if not candidates else None,
        "dose": dose,
        "safety_bn": safety,
        "stage_days": [lo, hi],
        "method": "deterministic KB table (backend/kb/triage.py); the AI model is not used",
    }
    log.info("tool_result triage_check coverage=%s candidates=%s", diag.coverage, [c["key"] for c in candidates])
    return result
