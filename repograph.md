# Repograph — what lives where

Shared exploration map (CLAUDE.md §1). Append/update after any unit of work so the
other instance doesn't re-explore. "?" = not yet known / not yet built.

## Ownership legend
A = Instance A (agent/tools/kb/memory/schemas/data) · B = Instance B (api/finance/payments/frontend/units)

## Unit conventions (ratified — use these everywhere)
**1 maund = 40 kg.** **1 bigha = 20 katha = 0.1338 ha.** Internal values are always
ha and kg; local units exist only at the intake/display edges, via `backend/units.py`.
Must also be stated in the README (NOTES #9). Detail and reasoning: `backend/units.py`.

## backend/ (created H0–H1 by A)
- `backend/requirements.txt` — pinned deps. A's core: anthropic 0.119.0, pydantic 2.13.4, python-dotenv 1.2.2. B's are pulled in via `-r api/requirements-api.txt`. Pin exact on first add.
- `backend/.env.example` — A's env keys. **See the env-loading trap below** for which `.env` is actually read.
- `backend/.venv/` — local virtualenv (gitignored). B used a repo-root `.venv/` instead; both are gitignored, either works.
- `backend/schemas.py` — **A, THE CONTRACT, frozen H1.** Pydantic v2 models: Provenance, FarmProfile/LocalArea, CropCandidate/ScoreComponent, SeasonPlan/PlanTask, FinanceProjection/FinanceScenarios/FinanceScenario/FinanceItem, Alert, CheckoutResult, all SSE events (Token/ToolCall/ToolResult/PlanUpdate/FinanceUpdate/Alert/Done/InputRequest/Error) + `SSEEvent` union, HTTP request bodies (ChatRequest/RecomputeRequest/CheckoutRequest/CheckoutItem). Every SSE event carries a `type` literal discriminator. Serializes to JSON via `.model_dump_json()`.
- `backend/agent/` — A. **LLM PROVIDER = OpenAI** (human A's call, deviates from PRD §11's Claude/Sonnet — LOG1 02:50). `config.py` (AgentConfig.from_env, OPENAI_MODEL default gpt-4o-mini, temperature, max_iterations=12, OPENAI_API_KEY/BASE_URL). `llm_client.py` (`OpenAIClient` implements provider-neutral `ChatBackend`; `TurnStream` context-mgr streams text deltas + accumulates streamed tool-call args → normalized `TurnResult`; `to_openai_tools()` translates our Anthropic-style tool defs → OpenAI function tools; `cost_from_usage()` + `_PRICING` (VERIFY prices); `tool_result_message()`; `LLMClient` alias). OpenAI prompt caching is automatic (no cache_control). `prompts.py` (SYSTEM_PROMPT — Bangla-first, weather-labeling, no-arithmetic/no-ranking, gap-detection intake). `tools_spec.py` (TOOL_DEFS Claude tool schemas + `dispatch()`; registers geocode/get_forecast/get_climatology; extend here for future tools). `loop.py` (`run_turn(messages, client)` generator → yields frozen SSE event models: token/tool_call/tool_result/error/done; provider-neutral — depends only on ChatBackend; max_iterations guard; per-turn cost accum + console cost line). **Import layout: `backend` is the package root — import as `backend.agent.loop`, run pytest/smokes from repo root.** Message history is native OpenAI format ({role,content} / assistant tool_calls / {role:tool,tool_call_id}).
- `backend/tools/` — A. `districts.py` (hardcoded 64-district table + ALIASES + `lookup_district()` — geocode offline fallback, NOTES #6). `geocode.py` (`geocode(name)` → Open-Meteo geocoding, candidate list, `needs_confirmation`; falls back to districts.py on failure; never fabricates). `weather.py` (`get_forecast` 16-day source_type=forecast; `get_climatology` archive normals source_type=climatology; retry→disk-cache fallback labeled cached=True→honest `degraded` if no cache). Live-verified against Open-Meteo. Remaining tools (rag_query/cropdb_sql/crop_scorer/aez_soil_check/check_plan_conflicts) land H3–H12.
- `backend/tests/` — A. `test_geocode_districts.py`, `test_weather.py`, `test_imports.py` — offline (network monkeypatched). Run: `backend/.venv/Scripts/python -m pytest backend/tests -q` from repo root. 16 tests, all green.
- `backend/.cache/weather/` — A, gitignored. Disk cache of last-good weather responses (fallback source).
- `backend/kb/` — A. `holt.py` (in-event generator: reads `agribase_clean.db` recommendation_yields view → damped-Holt base+band+trend, writes `data/crop.db` holt_projections + meta with git sha/timestamp; NEVER modifies agribase_clean.db). Remaining: `ingest.py` (Chroma), curated KB markdown (needs source docs — H3–H6 human-curated).
- `backend/tools/cropdb.py` — A. `cropdb_sql(action, crop, district)` tool: parameterized actions district_yields / holt_projection / yield_track_record over agribase_clean.db (safe views) + data/crop.db. NOT a raw-SQL surface. `CANON_TO_KEY` maps canonical crop names → db keys. Returns provenance-ready dicts (dataset=medium conf / computed=low-med).
- `backend/memory/` — A. empty (SQLite WAL: farm profile/conversations/plans/alerts land H9–H12).

## backend/api/ — B (FastAPI, SSE, sessions)
- `main.py` — the app. `GET /api/health`; `GET`+`POST /api/hello/stream` (transport self-test); mounts `chat.py`'s router.
- `chat.py` — `POST /api/chat`, B's route wrapping **A's agent loop**, imported lazily from `backend.agent.loop:run_turn`. Until that module exists the endpoint emits an honest `error` event instead of pretending. Also `/api/dev/harness*` — dev-only UI harnesses emitting contract-shaped events with deliberately synthetic English content (never farmer advice).
- `sse.py` — SSE wire format + streaming plumbing (event constructors, heartbeat, client-disconnect teardown). `tool_call`/`tool_result` **redact by construction**.
- `redact.py` — trace redaction (NOTES #19). password/appId/key/token/secret → `***`; phone/subscriberId → last 3 digits; secrets in URL query strings scrubbed. Returns the masked field paths, so a redaction is visible rather than silent.
- `config.py` — env-driven settings (host, port, CORS origins, heartbeat). No secret defaults.
- `requirements-api.txt` — B's exactly-pinned deps (fastapi, uvicorn[standard], python-dotenv, pytest + transitives).

**Two API facts worth knowing before touching it:**
- **Wire format:** every SSE event is one `data:` line holding one JSON object, discriminator `type` *inside* the JSON (matches PLAN §2). The SSE `event:` field is deliberately unused.
- **Transport is POST + fetch streaming, not EventSource** — EventSource cannot POST, and the contract is `POST /api/chat` with a JSON body.

## backend/finance/ — B (the only place money arithmetic happens)
- `engine.py` — `project(...)` returns a full `FinanceProjection` (3 scenarios, break-even yield + price, assumptions); `CostLine` is the per-hectare input row; `min_cost_per_ha()` is what the scorer's budget exclusion must use so the two can't disagree.
- **Yields cross this boundary in kg/ha** (crop.db units, LOG1 [02:20]) — pass crop.db values straight through, no conversion. A value in 0 < y < 50 kg/ha is **refused** as a probable t/ha mistake.
- **All arithmetic is `Decimal`; floats only at the schema boundary.** Rule: round, then combine — the displayed qty is the one priced, the displayed line totals are the ones summed, so every row multiplies out and the column adds up exactly on screen. Consequence: doubling the area scales the bill to ~1e-5 relative, not exactly (quantities are rounded to 4dp first). Deliberate; see the engine docstring.
- Scenarios (PRD §8 Tier0.5): conservative = (base − band) × price×0.9, base, optimistic = (base + band) × price×1.1. Break-even is answered against the **base** scenario.

## backend/payments/ — B (bdapps, simulator-first)
- `simulator.py` — the twin: documented bdapps shapes exactly, numeric fields as strings (gotcha #7), `E1326`/`E1601` → insufficient balance per the reference's §8 code table (its §6.3 inline note disagrees; §8 wins, LOG2 [03:55]).
- `client.py` — the live path. Detects bdapps' HTML-not-JSON error responses and names the likely cause (IP not whitelisted).
- `msisdn.py` — accepts every way a farmer types a number; **raises** on an invalid one rather than "fixing" it, because a silently corrected number charges a stranger.
- `service.py` — mode toggle (**defaults to simulator**; live construction raises without credentials), the confirmation gate, and the Bengali receipt. `CheckoutResult.raw` goes through the redactor.
- `backend/api/checkout.py` — `POST /api/checkout`, `/api/checkout/quote`, `GET /api/checkout/mode`. **The confirmation gate is server-enforced:** `/quote` registers a single-use pending confirmation keyed on farm_id+mobile+amount; `/checkout` returns **409** without a matching unexpired quote. No schema change was needed.

## backend/units.py — B
Area (bigha/katha/decimal/acre/ha/sq_m/sq_ft) and mass (maund/seer/kg/quintal/ton/g), Bangla aliases, Bangla display labels. Internal is **always ha and kg**; local units exist only at the intake/display edges.
- **1 bigha = 0.1337803776 ha** (20 katha × 720 sq ft ≈ the ratified 0.1338). The docs' "= 33 decimal" is an approximation — a bigha is really 33.06 decimal. Acre/decimal stay on the exact international acre.
- **1 maund = 40 kg** (market/DAM maund, ratified by human B), not the 37.3242 kg historical one.

## frontend/ — B (Vite + React, manifest-only PWA)
- `vite.config.js` — React plugin, PWA manifest, and the **`/api` proxy to :8000** (the reason there is no CORS in dev).
- `src/App.jsx` — one responsive page: chat + trace. Tabs on a phone, side-by-side from 900px. Dev harness bar is stripped from the production build.
- `src/state/useChat.js` — **the only place SSE event semantics live.** Handles every PLAN §2 event; unknown types surface in the trace rather than vanishing.
- `src/components/ChatPanel.jsx` — transcript + composer, Bangla-first. Composer stays live while a widget shows.
- `src/components/InputRequest.jsx` — all five `input_kind`s: chips, searchable dropdown (64 districts), number, number+unit, text. Answers are sent as ordinary Bangla text ("2 বিঘা") so the agent needs no second parsing path.
- `src/components/TracePanel.jsx` — judge-facing trace, English. Shows already-redacted params/results and names the masked fields.
- `src/api/sse.js` — SSE-over-fetch client, spec-correct framing (comments, multi-line `data:`, UTF-8 across chunk boundaries).
- `src/index.css` / `App.css` — earthy design tokens, sunlight contrast, ≥44px touch targets.
- **No service worker, on purpose** (PRD §9, NOTES #8): `injectRegister: null` + `devOptions.enabled: false` + `selfDestroying: true`, plus a dev-time eviction in `main.jsx`. If the UI behaves impossibly, check the console for the eviction warning first.
- **The PWA manifest link only exists in the production build.** The phone install test must run `npm run build && npm run preview`, never `npm run dev`.
- Plan/Finance tabs are deliberately **absent** until H9–H12 — an empty tab reads as a broken feature.

## tests/ — root-level, shared by file (CLAUDE.md rule 12)
`test_units.py`, `test_redact.py`, `test_finance.py`, `test_payments.py` (B). **A's `test_crop_scorer.py` belongs here too.**
Run from the repo root: `.venv/Scripts/python -m pytest tests/ -q` — 214 green as of LOG2 [04:20].

## data/
- `data/raw/` — A. public yearbook extracts (empty, .gitkeep).
- `data/crop.db` — A, generated in-event by `backend/kb/holt.py` from `agribase_clean.db`. Tables: holt_projections (crop_key, district, base_yield_kg_ha, band_kg_ha, n_points, trend, method, fitted_at) + meta (generated_at, git sha, source, disclaimer). 310 rows. Committed (meta-timestamped). Regenerate: `python -m backend.kb.holt`.
- **CROP SET (from agribase_clean.db):** enabled = aman_rice, boro_rice, potato, mustard, lentil. **Wheat disabled (no source key), maize absent.** Diverges from PRD §3.2 six-crop (no wheat/maize; lentil is an extra). Rabi ranking candidates from data = boro/potato/mustard/lentil; kharif-2 = aman. OPEN for human A: confirm crop set or supply wheat/maize yield data.
- `data/prices.md` — B (not yet created).

## Still to build (B)
`data/prices.md` (the cost/price numbers the finance engine is waiting for),
Plan/Finance tabs + `/api/finance/recompute` (H9–H12), checkout UI.

**What A needs to drop in for the loop to light up:** `backend/agent/loop.py` exposing
`async def run_turn(session_id, farm_id, message) -> AsyncIterator[dict]`, yielding PLAN §2
event dicts. Build tool events with `sse.tool_call(...)` / `sse.tool_result(...)` —
**never hand-build those dicts**, or redaction is bypassed. `/api/chat` picks the module
up automatically the moment it exists.

## ⚠ Env loading — one trap, flagged by B
`backend/agent/config.py` calls bare `load_dotenv()`, which searches **CWD upward**.
We run uvicorn from the repo root, so it finds `<root>/.env` and would **not** find
`backend/.env`. So: **put the real `.env` at the repo root.** `backend/api/config.py`
loads the root `.env` explicitly, so one root file serves both instances.
Also, A's `backend/.env.example` guesses `BDAPPS_APP_KEY` / `BDAPPS_APP_PASSWORD`; the
real names per BDAPPS-API-REFERENCE.md are `BDAPPS_APP_ID` / `BDAPPS_PASSWORD` (the root
`.env.example` has the correct ones).

## Pre-existing at repo root (NOT created by this block — predates it)
- `agribase_clean.db` + `build_agribase_clean.sql` + `AGRIBASE_CLEANING.md` — a validation-first derivative of a supplied `crops.db`. Exposes views `latest_district_yields` and `recommendation_yields`. **Note:** PRD §5 says crop.db is generated in-event by parse_agribase.py; how this pre-existing db reconciles with that in-event requirement is an OPEN question for A to resolve at H3–H6 (rules-cleanliness, NOTES #3). Its `source_registry` is `pending_verification` — do not label as BBS-verified.
- `BDAPPS-API-REFERENCE.md`, `BDAPPS-PREFLIGHT-CHECKLIST.md` — bdapps docs (B territory).
- `competition.md` — event brief.

## Docs
- `PRD.md` `PLAN.md` `NOTES.md` `CLAUDE.md` — spec + schedule + caveats + rules.
- `LOG1.md` (A) `LOG2.md` (B) — append-only work logs.
