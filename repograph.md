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
- `backend/agent/` — A. `config.py` (AgentConfig.from_env, model=claude-sonnet-5 default, max_iterations=12). `llm_client.py` (LLMClient: swappable ChatBackend, `.stream()`, `.cost_from_usage()`, `cached_system()` prompt-cache helper, `_PRICING` table). Agent loop itself = next block (H1–H3).
- `backend/tools/` — A. empty (weather/geocode/rag_query/cropdb_sql/crop_scorer/check_plan_conflicts land H1–H9).
- `backend/kb/` — A. empty (parse_agribase.py, holt.py, ingest.py, curated markdown land H3–H6).
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
`test_units.py`, `test_redact.py` (B). **A's `test_crop_scorer.py` belongs here too.**
Run from the repo root: `.venv/Scripts/python -m pytest tests/ -q`.

## data/
- `data/raw/` — A. public yearbook extracts (empty, .gitkeep).
- `crop.db` — A, generated in-event by parse_agribase.py (not yet built).
- `data/prices.md` — B (not yet created).

## Still to build (B)
`backend/finance/`, `backend/payments/`, `data/prices.md`.

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
