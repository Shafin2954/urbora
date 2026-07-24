"""
AgriSense shared schemas — THE CONTRACT (PLAN.md §2).

Owner: Instance A. Imported by Instance B (api / finance / payments / frontend
serialization). FROZEN at H1. After the freeze, any change requires a LOG1.md
entry + human A approval + a heads-up to B before merge (CLAUDE.md §0).

Design rules baked in here:
  * Rule 3 — Provenance is mandatory. Every number that reaches the UI is wrapped
    in (or accompanied by) a Provenance object. A number without provenance must
    not render; that is enforced by these types, not hoped for in a prompt.
  * Rule 4 — Weather claims carry source_type (forecast vs climatology) via the
    Provenance.source_type field (api = live forecast/climatology from Open-Meteo).
  * Rule 10 — internal units are ha/kg; local units live only at the intake/display
    edge (FarmProfile.area_local).

Timestamps are ISO-8601 strings on the wire (SSE + JSON), UTC. Numeric values in
tables use Western numerals; Bangla text lives around them, never inside them.
"""

from __future__ import annotations

from typing import Literal, Union

from pydantic import BaseModel, Field

# ─────────────────────────────────────────────────────────────────────────────
# Provenance — the spine of the whole system (PRD §7, PLAN §2)
# ─────────────────────────────────────────────────────────────────────────────

SourceType = Literal["kb", "api", "dataset", "static_table", "computed"]
Confidence = Literal["high", "medium", "low"]


class Provenance(BaseModel):
    """Where a single number/value came from. Attached to every rendered value.

    source_type meanings:
      kb           — retrieved from the curated knowledge base (Chroma RAG)
      api          — live API response (Open-Meteo forecast OR climatology)
      dataset      — crop.db row  (locator = "{edition} {source_table} p.{page}")
      static_table — hand-curated table (prices.md, FAO-56 Kc, AEZ soil)
      computed     — derived by a pure function (finance engine, holt.py, scorer);
                     `formula` names the method + inputs.
    """

    value: Union[int, float, str]
    unit: str | None = None
    source_type: SourceType
    source_id: str
    source_title: str
    locator: str | None = None          # page/table/url/query — human-inspectable
    retrieved_at: str                   # ISO-8601 UTC
    formula: str | None = None          # required when source_type == "computed"
    confidence: Confidence = "high"


# ─────────────────────────────────────────────────────────────────────────────
# Farm profile (PLAN §2)
# ─────────────────────────────────────────────────────────────────────────────

SoilType = Literal["clay", "loam", "sandy_loam", "clay_loam", "silt", "sandy", "peat"]
WaterSource = Literal["rainfed", "tubewell", "canal", "irrigated"]
Season = Literal["rabi", "kharif1", "kharif2"]
LocalAreaUnit = Literal["bigha", "katha", "decimal", "acre", "hectare"]


class LocalArea(BaseModel):
    """Farmer-facing area at the intake/display edge (units.py converts to ha)."""

    value: float
    unit: LocalAreaUnit


class FarmProfile(BaseModel):
    farm_id: str
    name: str
    district: str
    lat: float
    lon: float
    area_ha: float                      # internal canonical unit (ha)
    area_local: LocalArea               # what the farmer typed
    soil_type: SoilType
    water_source: WaterSource
    budget_bdt: float
    season: Season
    created_at: str                     # ISO-8601 UTC


# ─────────────────────────────────────────────────────────────────────────────
# Crop recommendation (PRD §6, PLAN §2)
# ─────────────────────────────────────────────────────────────────────────────

WaterNeed = Literal["low", "medium", "high"]
RiskLevel = Literal["low", "medium", "high"]


class ScoreComponent(BaseModel):
    """One row of the 0–100 suitability breakdown (agronomic/profit/climate/etc.)."""

    name: str
    points: float
    max: float
    provenance: Provenance


class CropCandidate(BaseModel):
    crop: str                           # canonical english key (matches KB + crop.db)
    composite_score: float
    components: list[ScoreComponent]
    excluded: bool = False
    exclusion_reason: str | None = None  # farmer-readable, when excluded
    water_need: WaterNeed
    risk_level: RiskLevel
    est_profit_bdt: float
    provenance: list[Provenance]        # extra sources feeding this candidate


# ─────────────────────────────────────────────────────────────────────────────
# Season plan (PRD §8 Tier0.4, PLAN §2)
# ─────────────────────────────────────────────────────────────────────────────

TaskCategory = Literal[
    "land_prep", "sowing", "irrigation", "fertilizer",
    "weeding", "pest_checkpoint", "harvest", "other",
]


class PlanTask(BaseModel):
    date: str                           # ISO-8601 date (YYYY-MM-DD)
    task: str
    category: TaskCategory
    details: str
    depends_on_weather: bool = False
    provenance: Provenance


class SeasonPlan(BaseModel):
    farm_id: str
    crop: str
    tasks: list[PlanTask]


# ─────────────────────────────────────────────────────────────────────────────
# Financial projection (PRD §8 Tier0.5, PLAN §2) — computed by Instance B's
# finance engine; A never does the arithmetic (rule 1). Shapes owned here.
# ─────────────────────────────────────────────────────────────────────────────


class FinanceItem(BaseModel):
    name: str
    qty: float
    unit: str
    unit_cost: float
    total: float
    provenance: Provenance


class FinanceScenario(BaseModel):
    items: list[FinanceItem]
    total_cost: float
    expected_yield_kg: float
    price_per_kg: float
    revenue: float
    net_profit: float
    roi_pct: float


class FinanceScenarios(BaseModel):
    conservative: FinanceScenario
    base: FinanceScenario
    optimistic: FinanceScenario


class FinanceProjection(BaseModel):
    scenarios: FinanceScenarios
    breakeven_yield_kg: float
    breakeven_price_bdt: float
    assumptions: list[Provenance]


# ─────────────────────────────────────────────────────────────────────────────
# Proactive alerts (Tier 1) + bdapps checkout (Tier 2)
# ─────────────────────────────────────────────────────────────────────────────

AlertStatus = Literal["open", "acknowledged", "resolved", "dismissed"]


class Alert(BaseModel):
    alert_id: str
    farm_id: str
    task_date: str                      # the plan task the conflict touches
    task: str
    conflict: str                       # what the weather/data conflict is
    suggestion: str                     # proposed revision
    created_at: str
    status: AlertStatus = "open"


CheckoutMode = Literal["live", "simulator"]


class CheckoutResult(BaseModel):
    status: str                         # e.g. "success" | "insufficient_balance" (E1326)
    trx_id: str | None = None
    mode: CheckoutMode                  # never present simulator as live (rule 13)
    receipt_sms_sent: bool = False
    raw: dict                           # raw (redacted) bdapps response for the trace


# ─────────────────────────────────────────────────────────────────────────────
# SSE events (PLAN §2). Emitted by B's redacting emitter; produced by A's agent
# loop. `type` is the discriminator. tool_call / tool_result carry RAW params &
# results — the emitter (B) redacts secrets before they leave the process (rule 5).
# ─────────────────────────────────────────────────────────────────────────────


class TokenEvent(BaseModel):
    type: Literal["token"] = "token"
    text: str


class ToolCallEvent(BaseModel):
    type: Literal["tool_call"] = "tool_call"
    id: str
    name: str
    params: dict                        # RAW — redacted by the emitter
    ts: str


class ToolResultEvent(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    id: str
    name: str
    result_raw: object                  # RAW — redacted by the emitter
    ts: str


class PlanUpdateEvent(BaseModel):
    type: Literal["plan_update"] = "plan_update"
    plan: SeasonPlan


class FinanceUpdateEvent(BaseModel):
    type: Literal["finance_update"] = "finance_update"
    finance: FinanceProjection


class AlertEvent(BaseModel):
    type: Literal["alert"] = "alert"
    alert: Alert


class Usage(BaseModel):
    in_tokens: int
    out_tokens: int
    cost_usd: float


class DoneEvent(BaseModel):
    type: Literal["done"] = "done"
    usage: Usage


InputKind = Literal["chips", "dropdown", "number", "number_unit", "text"]


class InputOption(BaseModel):
    value: str
    label_bn: str


class InputRequestEvent(BaseModel):
    """An intake accelerator widget the UI renders inline (PRD §8 Tier0.1)."""

    type: Literal["input_request"] = "input_request"
    field: str
    prompt_bn: str
    input_kind: InputKind
    options: list[InputOption] | None = None    # for chips/dropdown
    unit_options: list[str] | None = None       # for number_unit


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    message: str


SSEEvent = Union[
    TokenEvent,
    ToolCallEvent,
    ToolResultEvent,
    PlanUpdateEvent,
    FinanceUpdateEvent,
    AlertEvent,
    DoneEvent,
    InputRequestEvent,
    ErrorEvent,
]


# ─────────────────────────────────────────────────────────────────────────────
# HTTP request bodies (PLAN §2). Response bodies ARE the core models above.
#   POST /api/chat                 → SSE stream (ChatRequest)
#   GET  /api/farms                → list[FarmProfile]
#   GET  /api/plan/{farm_id}       → SeasonPlan | 404
#   POST /api/finance/recompute    → FinanceProjection (RecomputeRequest)
#   POST /api/checkout             → CheckoutResult (CheckoutRequest)
#   POST /api/plan/{farm_id}/check → list[Alert]
# ─────────────────────────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    session_id: str
    farm_id: str | None = None
    message: str


class RecomputeRequest(BaseModel):
    farm_id: str
    overrides: dict[str, object]        # {field: value} — e.g. {"area_ha": 0.4}


class CheckoutItem(BaseModel):
    name: str
    qty: float
    unit: str
    unit_price_bdt: float


class CheckoutRequest(BaseModel):
    farm_id: str
    mobile: str
    amount: float
    items: list[CheckoutItem]
