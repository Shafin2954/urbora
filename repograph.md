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
- `backend/agent/` — A. `config.py` (AgentConfig.from_env, model=claude-sonnet-5 default, max_iterations=12). `llm_client.py` (LLMClient: swappable ChatBackend, `.stream()`, `.cost_from_usage()`, `cached_system()` prompt-cache helper, `_PRICING` table). `prompts.py` (SYSTEM_PROMPT — Bangla-first, weather-labeling, no-arithmetic/no-ranking, gap-detection intake). `tools_spec.py` (TOOL_DEFS Claude tool schemas + `dispatch()`; registers geocode/get_forecast/get_climatology; extend here for future tools). `loop.py` (`run_turn(messages, client)` generator → yields frozen SSE event models: token/tool_call/tool_result/error/done; max_iterations guard; per-turn cost accum + console cost line). **Import layout: `backend` is the package root — import as `backend.agent.loop`, run pytest/smokes from repo root.**
- `backend/tools/` — A. `districts.py` (hardcoded 64-district table + ALIASES + `lookup_district()` — geocode offline fallback, NOTES #6). `geocode.py` (`geocode(name)` → Open-Meteo geocoding, candidate list, `needs_confirmation`; falls back to districts.py on failure; never fabricates). `weather.py` (`get_forecast` 16-day source_type=forecast; `get_climatology` archive normals source_type=climatology; retry→disk-cache fallback labeled cached=True→honest `degraded` if no cache). Live-verified against Open-Meteo. Remaining tools (rag_query/cropdb_sql/crop_scorer/aez_soil_check/check_plan_conflicts) land H3–H12.
- `backend/tests/` — A. `test_geocode_districts.py`, `test_weather.py`, `test_imports.py` — offline (network monkeypatched). Run: `backend/.venv/Scripts/python -m pytest backend/tests -q` from repo root. 16 tests, all green.
- `backend/.cache/weather/` — A, gitignored. Disk cache of last-good weather responses (fallback source).
- `backend/kb/` — A. `holt.py` (in-event generator: reads `agribase_clean.db` recommendation_yields view → damped-Holt base+band+trend, writes `data/crop.db` holt_projections + meta with git sha/timestamp; NEVER modifies agribase_clean.db). Remaining: `ingest.py` (Chroma), curated KB markdown (needs source docs — H3–H6 human-curated).
- `backend/tools/cropdb.py` — A. `cropdb_sql(action, crop, district)` tool: parameterized actions district_yields / holt_projection / yield_track_record over agribase_clean.db (safe views) + data/crop.db. NOT a raw-SQL surface. `CANON_TO_KEY` maps canonical crop names → db keys. Returns provenance-ready dicts (dataset=medium conf / computed=low-med).
- `backend/memory/` — A. empty (SQLite WAL: farm profile/conversations/plans/alerts land H9–H12).
- `backend/api/` `backend/finance/` `backend/payments/` `backend/units.py` — **B, not yet created.**

## data/
- `data/raw/` — A. public yearbook extracts (empty, .gitkeep).
- `data/crop.db` — A, generated in-event by `backend/kb/holt.py` from `agribase_clean.db`. Tables: holt_projections (crop_key, district, base_yield_kg_ha, band_kg_ha, n_points, trend, method, fitted_at) + meta (generated_at, git sha, source, disclaimer). 310 rows. Committed (meta-timestamped). Regenerate: `python -m backend.kb.holt`.
- **CROP SET (from agribase_clean.db):** enabled = aman_rice, boro_rice, potato, mustard, lentil. **Wheat disabled (no source key), maize absent.** Diverges from PRD §3.2 six-crop (no wheat/maize; lentil is an extra). Rabi ranking candidates from data = boro/potato/mustard/lentil; kharif-2 = aman. OPEN for human A: confirm crop set or supply wheat/maize yield data.
- `data/prices.md` — B (not yet created).

## Pre-existing at repo root (NOT created by this block — predates it)
- `agribase_clean.db` + `build_agribase_clean.sql` + `AGRIBASE_CLEANING.md` — a validation-first derivative of a supplied `crops.db`. Exposes views `latest_district_yields` and `recommendation_yields`. **Note:** PRD §5 says crop.db is generated in-event by parse_agribase.py; how this pre-existing db reconciles with that in-event requirement is an OPEN question for A to resolve at H3–H6 (rules-cleanliness, NOTES #3). Its `source_registry` is `pending_verification` — do not label as BBS-verified.
- `BDAPPS-API-REFERENCE.md`, `BDAPPS-PREFLIGHT-CHECKLIST.md` — bdapps docs (B territory).
- `competition.md` — event brief.

## Docs
- `PRD.md` `PLAN.md` `NOTES.md` `CLAUDE.md` — spec + schedule + caveats + rules.
- `LOG1.md` (A) `LOG2.md` (B) — append-only work logs.
