# Repograph — what lives where

Shared exploration map (CLAUDE.md §1). Append/update after any unit of work so the
other instance doesn't re-explore. "?" = not yet known / not yet built.

## Ownership legend
A = Instance A (agent/tools/kb/memory/schemas/data) · B = Instance B (api/finance/payments/frontend/units)

## backend/ (created H0–H1 by A)
- `backend/requirements.txt` — pinned deps. A's core: anthropic 0.119.0, pydantic 2.13.4, python-dotenv 1.2.2. B appends fastapi/uvicorn/sse. Pin exact on first add.
- `backend/.env.example` — all env keys (A: ANTHROPIC_API_KEY, AGRISENSE_*; B: BDAPPS_* placeholders). Keep current.
- `backend/.venv/` — local virtualenv (gitignored).
- `backend/schemas.py` — **A, THE CONTRACT, frozen H1.** Pydantic v2 models: Provenance, FarmProfile/LocalArea, CropCandidate/ScoreComponent, SeasonPlan/PlanTask, FinanceProjection/FinanceScenarios/FinanceScenario/FinanceItem, Alert, CheckoutResult, all SSE events (Token/ToolCall/ToolResult/PlanUpdate/FinanceUpdate/Alert/Done/InputRequest/Error) + `SSEEvent` union, HTTP request bodies (ChatRequest/RecomputeRequest/CheckoutRequest/CheckoutItem). Every SSE event carries a `type` literal discriminator. Serializes to JSON via `.model_dump_json()`.
- `backend/agent/` — A. `config.py` (AgentConfig.from_env, model=claude-sonnet-5 default, max_iterations=12). `llm_client.py` (LLMClient: swappable ChatBackend, `.stream()`, `.cost_from_usage()`, `cached_system()` prompt-cache helper, `_PRICING` table). Agent loop itself = next block (H1–H3).
- `backend/tools/` — A. empty (weather/geocode/rag_query/cropdb_sql/crop_scorer/check_plan_conflicts land H1–H9).
- `backend/kb/` — A. empty (parse_agribase.py, holt.py, ingest.py, curated markdown land H3–H6).
- `backend/memory/` — A. empty (SQLite WAL: farm profile/conversations/plans/alerts land H9–H12).
- `backend/api/` `backend/finance/` `backend/payments/` `backend/units.py` — **B, not yet created.**

## data/
- `data/raw/` — A. public yearbook extracts (empty, .gitkeep).
- `crop.db` — A, generated in-event by parse_agribase.py (not yet built).
- `data/prices.md` — B (not yet created).

## Pre-existing at repo root (NOT created by this block — predates it)
- `agribase_clean.db` + `build_agribase_clean.sql` + `AGRIBASE_CLEANING.md` — a validation-first derivative of a supplied `crops.db`. Exposes views `latest_district_yields` and `recommendation_yields`. **Note:** PRD §5 says crop.db is generated in-event by parse_agribase.py; how this pre-existing db reconciles with that in-event requirement is an OPEN question for A to resolve at H3–H6 (rules-cleanliness, NOTES #3). Its `source_registry` is `pending_verification` — do not label as BBS-verified.
- `BDAPPS-API-REFERENCE.md`, `BDAPPS-PREFLIGHT-CHECKLIST.md` — bdapps docs (B territory).
- `competition.md` — event brief.

## Docs
- `PRD.md` `PLAN.md` `NOTES.md` `CLAUDE.md` — spec + schedule + caveats + rules.
- `LOG1.md` (A) `LOG2.md` (B) — append-only work logs.
