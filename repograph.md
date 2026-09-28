# Repograph — what lives where

Map of the tree. Update after any unit of work so nothing has to be re-explored.
"?" = not yet known / not yet built.

## FutureMakers round (September 2026) — read this first
Branch `futuremakers`, single operator, log in `LOG4.md`, rules in CLAUDE.md v3.
- `backend/branding.py`, `frontend/src/branding.js` — the product name: **Agrosfeer**.
- `backend/env.py` — loads `.env.local` > `backend/.env` > `.env` (both configs use it).
- Replit (committed by the Repl itself to `master`): `.replit` (dev = `start.sh`; deployment = autoscale,
  build `cd frontend && npm install && npm run build`, run uvicorn on :5000), `start.sh`, `pyproject.toml` +
  `uv.lock` (**the Repl's own dependency list — separate from `backend/requirements.txt`**), `replit.md`,
  stub `main.py`, `package.json`. `backend/api/main.py` serves `frontend/dist` + an SPA fallback when dist exists.
  Vite dev port is **5000** since the merge (was 5173).
- `backend/agent/intake_guard.py` — refuses planning tools on district/soil/water/season the farmer never stated.
- `backend/channels/voice/audio.py` (pure audio helpers + VAD segmenter + ADB call-state parser) and
  `voice/phonelink.py` (real calls via Windows Phone Link + Voicemeeter; optional deps in
  `backend/requirements-voice-bridge.txt`); routes `/api/channels/bridge/voice/*`.
- `backend/tests/conftest.py` — clears provider env vars so tests stay hermetic.
- `backend/channels/` — phone channels. `identity.py` (phone → `ph-<hmac>` farm id;
  sessions per phone per day, voice per call), `adapter.py` (`run_channel_turn`:
  drains `run_turn` into text + numbered `Menu` + plan/finance + redacted events;
  digit replies map back to option labels), `sms_text.py` (GSM-7/UCS-2 segment
  math, `fit`, template `plan_summary_sms`), `sms.py` (providers smsgate / bdapps /
  simulator; `send_sms(farm_id, text)`), `flows.py` (inbound SMS, missed call,
  summary), `ussd.py` (pure `step()` state machine + `ussd_request` runtime; agent
  work runs as background actions → SMS), `alerts_job.py` (rain-conflict SMS once
  per alert), `voice/speech.py` (Sarvam/OpenAI/Azure STT+TTS over httpx),
  `voice/turn.py` (`voice_turn`, `hang_up` → SMS summary), `bridge/adb.py`
  (missed-call watcher over ADB).
- `backend/agent/loop.py` — `run_turn(..., channel=)` + `CHANNEL_NOTES`.
- `CHANNELS_RESEARCH.md` — verified telecom/SMSGate/16123 facts + the KB-bounded crop-problem tree. Read before touching channels.
- `backend/channels/bridge/phone_up.py` — one command: phone as SMS gateway over USB (adb forward 8080 / reverse 8000, webhooks).
- `backend/channels/ussd.py` — screen budget (`fits`, 80 UCS-2 / 182 GSM-7), pager (`paginate`/`paged`/`pick_paged`), 9 = more / 0 = back, resume of dropped walks.
- `backend/kb/triage.py` (deterministic crop-problem table, SMS template) + `backend/channels/triage_menu.py` (USSD menu 2, `run_problem_action`); store table `triage_reports`, `triage_summary()`.
- `run_turn(..., context_note=)` — server note a channel attaches (recent triage for SMS follow-ups).
- `backend/channels/sms_menu.py` — "মেনু" → USSD menu over SMS (checked first in `flows.handle_inbound_sms`).
- `backend/channels/voice/audio.py` `DtmfDetector` + `voice/ivr.py` (keys → spoken USSD menu); routes `/api/channels/{emulator,bridge}/voice/keys`; `phonelink --test-dtmf`.
- `.claude/launch.json` — dev servers: backend :8000 (reload), frontend :5000.
- `backend/market/` — `db.py` (market tables in the same SQLite file), `catalog.py`
  (generic inputs), `ranking.py` (price/distance/stock/trust), `inputs.py`
  (`find_inputs` tool, orders + state machine, dealers, SMS), `produce.py`
  (listings + price guide, offers, accept/contacts), `sms_commands.py` (বিক্রি /
  গ্রহণ / dealer হ্যাঁ…), `ussd_menus.py` (menus 4 and 5), `seed_demo.py`.
- `backend/finance/market.py` — order totals, commission (dealer pays), packs,
  produce deal fee (buyer pays). Decimal.
- `backend/api/channels.py` (`/api/channels/*`: SMSGate/bdapps webhooks, emulator
  SMS/USSD/voice/missed-call/inbox — only in simulator mode —, monitor sessions,
  bridge, alert scan) and `backend/api/market.py` (`/api/market/*`).
- `backend/memory/store.py` — new tables `contacts` (the only raw phone numbers),
  `channel_turns`, `sms_log`, `ussd_sessions`, `alert_sms`.
- Frontend hash routes (`frontend/src/Root.jsx`): `#/phone` (`pages/PhonePage.jsx`,
  `VoiceCall.jsx`), `#/monitor` (`components/ChannelMonitor.jsx` → `GraphPanel`),
  `#/market` (`pages/MarketPage.jsx`), `#/dealer`, `#/buyer`
  (`pages/PartnerPages.jsx`). API clients `src/api/channels.js`, `src/api/market.js`.
- Tests: `backend/tests/test_channels_{core,sms,ussd,voice}.py`,
  `backend/tests/test_market.py`, `tests/test_market_finance.py`. Suite 632 green (2026-09-28).
- Gone: `data/agristats.db` (0-byte decoy), `NodeInspector.jsx`, `TracePanel.jsx`.

## Ownership
**Single operator since H10.5** (LOG3 [10:30]) — the whole tree. The A/B labels below
are historical: they say who originally wrote a thing, not who may touch it. Current
work is logged in `LOG3.md`; `LOG1.md`/`LOG2.md` are closed history.

## Unit conventions (ratified — use these everywhere)
**1 maund = 40 kg.** **1 bigha = 20 katha = 0.1338 ha.** Internal values are always
ha and kg; local units exist only at the intake/display edges, via `backend/units.py`.
Must also be stated in the README (NOTES #9). Detail and reasoning: `backend/units.py`.

## backend/ (created H0–H1 by A)
- `backend/requirements.txt` — pinned deps. A's core: anthropic 0.119.0, pydantic 2.13.4, python-dotenv 1.2.2. B's are pulled in via `-r api/requirements-api.txt`. Pin exact on first add.
- `backend/.env.example` — A's env keys. **See the env-loading trap below** for which `.env` is actually read.
- `backend/.venv/` — local virtualenv (gitignored). B used a repo-root `.venv/` instead; both are gitignored, either works.
- `backend/schemas.py` — **A, THE CONTRACT, frozen H1.** Pydantic v2 models: Provenance, FarmProfile/LocalArea, CropCandidate/ScoreComponent, SeasonPlan/PlanTask, FinanceProjection/FinanceScenarios/FinanceScenario/FinanceItem, Alert, CheckoutResult, all SSE events (Token/ToolCall/ToolResult/PlanUpdate/FinanceUpdate/Alert/Done/InputRequest/Error) + `SSEEvent` union, HTTP request bodies (ChatRequest/RecomputeRequest/CheckoutRequest/CheckoutItem). Every SSE event carries a `type` literal discriminator. Serializes to JSON via `.model_dump_json()`.
- `backend/agent/` — A. **LLM PROVIDER = OpenAI** (human A's call, deviates from PRD §11's Claude/Sonnet — LOG1 02:50). `config.py` (AgentConfig.from_env, OPENAI_MODEL default gpt-4o-mini, temperature, max_iterations=12, OPENAI_API_KEY/BASE_URL). `llm_client.py` (`OpenAIClient` implements provider-neutral `ChatBackend`; `TurnStream` context-mgr streams text deltas + accumulates streamed tool-call args → normalized `TurnResult`; `to_openai_tools()` translates our Anthropic-style tool defs → OpenAI function tools; `cost_from_usage()` + `_PRICING` (VERIFY prices); `tool_result_message()`; `LLMClient` alias). OpenAI prompt caching is automatic (no cache_control). `prompts.py` (SYSTEM_PROMPT — Bangla-first, weather-labeling, no-arithmetic/no-ranking, gap-detection intake). `tools_spec.py` (TOOL_DEFS Claude tool schemas + `dispatch()`; registers geocode/get_forecast/get_climatology/cropdb_sql/crop_scorer). `loop.py` — **two layers.** `run_turn_sync(messages, client, system)` is the pure engine (yields frozen SSE event models; provider-neutral; max_iterations guard; per-turn cost accum + console cost line). `async run_turn(session_id, farm_id, message)` is what `api/chat.py` calls: loads history from `memory/store.py`, bridges the blocking engine onto a worker thread, saves history back, and yields **wire dicts** built through `sse.tool_call`/`sse.tool_result`. **Import layout: `backend` is the package root — import as `backend.agent.loop`, run pytest/smokes from repo root.** Message history is native OpenAI format ({role,content} / assistant tool_calls / {role:tool,tool_call_id}).
- `backend/tools/` — A. `districts.py` (hardcoded 64-district table + ALIASES + `lookup_district()` — geocode offline fallback, NOTES #6). `geocode.py` (`geocode(name)` → Open-Meteo geocoding, candidate list, `needs_confirmation`; falls back to districts.py on failure; never fabricates). `weather.py` (`get_forecast` 16-day source_type=forecast; `get_climatology` archive normals source_type=climatology; retry→disk-cache fallback labeled cached=True→honest `degraded` if no cache). Live-verified against Open-Meteo. `cropdb.py` (see below). `crop_scorer.py` — **PRD §6 deterministic ranker, deliberately scoped down (human decision, LOG1 2026-07-24).** Public pure `score_crops(...)` + impure `crop_scorer_tool(...)` (registered tool). Scores District track record (20pt) + Stability (10pt) for real, today, straight from crop.db/agribase_clean.db via cropdb.py. Agronomic fit/Profit/Climate fit report `points=0.0, confidence="low", value="unavailable"` — no fabricated KB/finance data — because neither a curated BARC/BRRI KB nor B's `backend/finance/` exist yet. Season/Soil/Water/Budget exclusions are no-ops until their data exists (only the "no yield data" exclusion, i.e. wheat/maize/unknowns, is live). Two typed-but-unpopulated seams — `crop_facts: dict[str,CropFacts]|None` (KB) and `finance: dict[str,CropFinance]|None` (B's engine) — already implement + test the FUTURE full-scoring path (synthetic values only in tests); supplying real data through these params later needs no rewrite. Tool result always carries a `degraded` list; `prompts.py` requires the agent to relay it honestly in Bangla before presenting any ranking. Live-verified through the full agent loop (OpenAI tool-called it, disclosed degraded mode near-verbatim, ranked all 5 crops matching the manual sanity check). Approved plan: `C:\Users\Shafin\.claude\plans\imperative-frolicking-hummingbird.md`.
- **Remaining A tools not yet built:** rag_query (needs Chroma + curated KB), aez_soil_check, check_plan_conflicts.
- **KNOWN SIDE-FINDING (not yet fixed):** in one live run the model rendered weather figures in Bangla numerals (২৫.৫) instead of Western numerals — violates CLAUDE.md rule 10 / NOTES #17. `prompts.py` needs a stronger explicit instruction; crop_scorer's own output numbers were correctly Western. Flagged for a follow-up prompt tweak, out of scope for the crop_scorer task.
- `backend/tools/cropdb.py` — A. `cropdb_sql(action, crop, district)` tool: parameterized actions district_yields / holt_projection / yield_track_record over agribase_clean.db (safe views) + data/crop.db. NOT a raw-SQL surface. `CANON_TO_KEY` maps canonical crop names → db keys (also used by crop_scorer.py, plus `resolve_crop()`). Returns provenance-ready dicts (dataset=medium conf / computed=low-med).
- `backend/tests/` — A. `test_geocode_districts.py`, `test_weather.py`, `test_imports.py`, `test_cropdb.py`, `test_crop_scorer.py`, `test_llm_backend.py` — all offline (network monkeypatched or structurally absent). Run: `backend/.venv/Scripts/python -m pytest backend/tests -q` from repo root. 59 tests, all green.
- `backend/.cache/weather/` — A, gitignored. Disk cache of last-good weather responses (fallback source).
- `backend/kb/` — A. `holt.py` (in-event generator: reads `agribase_clean.db` recommendation_yields view → damped-Holt base+band+trend, writes `data/crop.db` holt_projections + meta with git sha/timestamp; NEVER modifies agribase_clean.db). Remaining: `ingest.py` (Chroma), curated KB markdown (needs source docs — the crop_scorer.py `crop_facts` seam is what activates once this exists).
- `backend/memory/` — `store.py`: SQLite WAL at `backend/memory/memory.db` (gitignored). `sessions` table holds each session's conversation history — **this is where chat state lives**, and it is why a session survives a restart. `farms` table exists but **nothing reads or writes it yet**, so a returning farmer is not actually recalled (Phase 5). `get_session_messages`/`save_session_messages`/`get_farm`/`save_farm`.

## backend/api/ — B (FastAPI, SSE, sessions)
- `main.py` — the app. `GET /api/health`; `GET`+`POST /api/hello/stream` (transport self-test); mounts `chat.py`'s router.
- `chat.py` — `POST /api/chat`, B's route wrapping **A's agent loop**, imported lazily from `backend.agent.loop:run_turn` (so a missing or broken agent module degrades to an honest `error` event instead of taking the API down). Also `/api/dev/harness*` — dev-only UI harnesses emitting contract-shaped events with deliberately synthetic English content (never farmer advice).
- `sse.py` — SSE wire format + streaming plumbing (event constructors, heartbeat, client-disconnect teardown). `tool_call`/`tool_result` **redact by construction**; `format_sse` redacts again for anything that skipped them.
- `checkout.py` — `POST /api/checkout`, `/quote`, `GET /mode`. See the payments section.
- **Gone (LOG3 [10:30]):** `sessions.py` and `agent_bridge.py`. The agent loop grew its own SQLite session store and thread bridge, which do the same jobs and survive a restart. Do not rebuild them here.
- `redact.py` — trace redaction (NOTES #19). password/appId/key/token/secret → `***`; phone/subscriberId → last 3 digits; secrets in URL query strings scrubbed. Returns the masked field paths, so a redaction is visible rather than silent.
- `config.py` — env-driven settings (host, port, CORS origins, heartbeat). No secret defaults.
- `requirements-api.txt` — B's exactly-pinned deps (fastapi, uvicorn[standard], python-dotenv, pytest + transitives).

**Four API facts worth knowing before touching it:**
- **Wire format:** every SSE event is one `data:` line holding one JSON object, discriminator `type` *inside* the JSON (matches PLAN §2). The SSE `event:` field is deliberately unused.
- **Transport is POST + fetch streaming, not EventSource** — EventSource cannot POST, and the contract is `POST /api/chat` with a JSON body.
- **The call shape:** `async run_turn(session_id, farm_id, message)` yielding wire dicts. The loop owns the conversation history (`backend/memory/store.py`) and its own worker thread; the route is a thin transport wrapper. **`farm_id` is passed but not yet used** — nothing reads the `farms` table, so a returning farmer is not actually recalled. Open, Phase 5.
- **Redaction is enforced in `format_sse`, not only in the constructors.** Events already masked carry a `redacted` list and pass through untouched, because re-masking a phone (`***678` → `***`) is lossy.

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

## frontend/ — single operator since H10.5 (Vite + React, manifest-only PWA)
- `vite.config.js` — React plugin, PWA manifest, and the **`/api` proxy to :8000** (the reason there is no CORS in dev).
- `src/App.jsx` — one responsive page: chat/finance/plan/evidence/checkout tabs on the left, the provenance graph permanently docked on the right from 900px. Dev harness bar is stripped from the production build. **Fixed on `graph-ui` [15:35+]:** the tab bar used to `display:none` above 900px, making Finance/Plan/Evidence unreachable on a laptop — only Chat+Trace ever rendered there. Tabs now stay visible at every width.
- `src/state/useChat.js` — **the only place SSE event semantics live.** Handles every PLAN §2 event; unknown types surface in the trace rather than vanishing. `trace` accumulates for the whole session and is never cleared between turns.
- `src/components/ChatPanel.jsx` — transcript + composer, Bangla-first. Composer stays live while a widget shows.
- `src/components/InputRequest.jsx` — all five `input_kind`s: chips, searchable dropdown (64 districts), number, number+unit, text. Answers are sent as ordinary Bangla text ("2 বিঘা") so the agent needs no second parsing path.
- `src/components/GraphPanel.jsx` — **[new, graph-ui]** the provenance graph that replaced the Trace tab as the primary judge view. Farm hexagon at the center; every node a fact (place/weather/KB source/crop/plan/finance/question); every edge labeled with the tool call that produced it. Deterministic radial layout (no physics), pan/zoom only, click a node to open `NodeInspector.jsx` with the raw params/result. Nests the old `TracePanel.jsx` underneath, collapsed, as "Raw log (n events)" — nothing was deleted, just demoted.
- `src/components/NodeInspector.jsx` — **[new, graph-ui]** overlay (not a sidebar, so it never squeezes another pane — see LOG3 [12:50]'s finance-table lesson) showing one node's backing tool call: name, params, raw result, both timestamps, duration, redacted fields.
- `src/lib/traceGraph.js` — **[new, graph-ui]** pure `buildGraph(trace) -> {nodes, edges, callsById}`. Pairs `tool_call`/`tool_result` by shared `id`, follows the `retrieval-{parentId}` convention `loop.py` uses for forced RAG calls to draw `source -> crop` / `source -> plan` edges, and keys every node on a stable fact (not a call id) so the same location/crop/source across three turns draws once, last-write-wins. No arithmetic — every sub-label quotes a server value or counts an array.
- `src/lib/graphLayout.js` — **[new, graph-ui]** pure `layout()` — BFS depth from farm, fixed angular slices per category, two rings. No force simulation on purpose (deterministic, doesn't jitter mid-stream).
- `src/components/TracePanel.jsx` — the raw chronological log, now nested inside GraphPanel rather than being its own tab. Still judge-facing/English, still shows already-redacted params/results and names the masked fields. Entries now default **collapsed**.
- `src/components/EvidencePanel.jsx` — the Tier-0 capability checklist grid was removed here (the graph's legend + node coloring covers "which capability ran" now); the three evidence cards (forecast/ranked crops/KB sources) stay.
- `src/api/sse.js` — SSE-over-fetch client, spec-correct framing (comments, multi-line `data:`, UTF-8 across chunk boundaries).
- `src/index.css` / `App.css` — earthy design tokens, sunlight contrast, ≥44px touch targets. `App.css` had two custom properties referenced but never declared (`--line`, `--muted` on `.plan-task`/`.task-category`) — mapped to `--border`/`--ink-faint` while touching this file for the graph-ui work.
- **No service worker, on purpose** (PRD §9, NOTES #8): `injectRegister: null` + `devOptions.enabled: false` + `selfDestroying: true`, plus a dev-time eviction in `main.jsx`. If the UI behaves impossibly, check the console for the eviction warning first.
- **The PWA manifest link only exists in the production build.** The phone install test must run `npm run build && npm run preview`, never `npm run dev`.

## tests/ — root-level, shared by file (CLAUDE.md rule 12)
`test_units.py`, `test_redact.py`, `test_finance.py`, `test_payments.py`, `test_chat_seam.py` (B).
A's live in `backend/tests/` instead. Run both from the repo root:
`.venv/Scripts/python -m pytest tests/ backend/tests -q` — **227 + 28 green** as of LOG2 [04:45].
The shared root `.venv` now has A's pins too (`openai==2.48.0`), so one venv runs everything.

## data/
- `data/raw/` — A. public yearbook extracts (empty, .gitkeep).
- `data/crop.db` — A, generated in-event by `backend/kb/holt.py` from `agribase_clean.db`. Tables: holt_projections (crop_key, district, base_yield_kg_ha, band_kg_ha, n_points, trend, method, fitted_at) + meta (generated_at, git sha, source, disclaimer). 310 rows. Committed (meta-timestamped). Regenerate: `python -m backend.kb.holt`.
- **CROP SET (from agribase_clean.db):** enabled = aman_rice, boro_rice, potato, mustard, lentil. **Wheat disabled (no source key), maize absent.** Diverges from PRD §3.2 six-crop (no wheat/maize; lentil is an extra). Rabi ranking candidates from data = boro/potato/mustard/lentil; kharif-2 = aman. OPEN for human A: confirm crop set or supply wheat/maize yield data.
- `data/prices.md` — filled from agristats.db + BARC/BARI PDFs as of LOG3 [15:05]. Both farm-gate price and input-cost tables have cited rows now; this line was stale (previously said "not yet created").

## Still to build
Nothing from the original Tier 0 punch list — `data/prices.md`, Plan/Finance tabs, `/api/finance/recompute`, and checkout UI are all done (see LOG3.md). Current work is the Trace-tab -> provenance-graph refactor on branch `graph-ui`.

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
# Task tracking

- `TASKLIST.md` records the remaining scoped work, including Tier 0 completion,
  demo hardening, and explicitly deferred work.
- `LOG3.md` includes the local-area tool-contract fix and the required API reload
  note for anyone running a long-lived development server.
- `backend/requirements.txt` pins the PDF extraction and Bijoy-decoding helpers
  used for Tier 0 knowledge-base curation.
- `backend/kb/crop_facts.py` holds the source-backed agronomy facts used by the
  deterministic scorer; it is not model knowledge.
- `backend/tools/season_plan.py` produces source-cited task calendars; plan
  persistence lives in `backend/memory/store.py`, and `backend/api/plans.py`
  exposes the saved plan.
- `backend/tests/test_season_plan.py` and `backend/tests/test_plan_persistence.py`
  cover deterministic dates, provenance, persistence, and the plan API contract.
- `backend/tests/test_loop_integration.py` pins the server-authoritative farm id
  injected into a fresh session; `tests/test_intake_and_memory.py` covers its
  coexistence with remembered-farm context. Current combined verification: 359
  tests passed, plus the frontend production build.
- `TIER0_ACCEPTANCE.md` is the current release gate: it records each of the
  eight required capabilities and the remaining fresh-live-trace verification.
- `backend/kb/retrieval.py` is the local source-cited retrieval layer used by
  `rag_query`; its orchestration is covered in `test_loop_integration.py`.
- `backend/tools/plan_conflicts.py` compares persisted weather-dependent plan
  tasks against the live forecast; `backend/api/alerts.py` exposes the check
  and persisted results, covered by `backend/tests/test_plan_conflicts.py`.
- `backend/tools/care_scheduler.py` exposes source-cited fertilizer/irrigation
  work from a saved plan; `backend/tools/scenario.py` re-runs ranking/finance
  for a budget scenario. Their UI entry point is `AlertPanel.jsx` in Plan.
- Tier 1 live acceptance used the clean API listener on port 8001 because port
  8000 held orphaned stale listeners; `frontend/vite.config.js` proxies dev
  `/api` traffic to 8001 until that local process issue is resolved.
- `backend/tools/agri_inputs.py` is the fixed-query, read-only agent gateway to
  the Chapter 7 `agristats.db` views (`v_seed`, `v_fertilizer`, `v_pesticides`,
  `v_wages`, `v_irrigation_by_region`, `v_irrigation_by_method`). It returns
  cited historic facts only; `finance_projection` remains the sole cost/profit
  calculator because Chapter 7 does not supply current retail prices.
- `backend/tests/test_agri_inputs.py` pins the new source boundary, result
  provenance, crop mapping, and no-arbitrary-SQL behavior.
- `supabase/migrations/20260725023000_crops.sql` creates the RLS-protected
  crop ownership/index table. `backend/api/crops.py` proxies the caller's
  Supabase token to that table and merges the existing SQLite farm/session data.
- `frontend/src/state/useAuth.js`, `useCrops.js`, and `lib/supabaseClient.js`
  own browser authentication and crop selection; `AuthScreen.jsx` and
  `Sidebar.jsx` render the corresponding UI.
- `supabase/config.toml` is the local Supabase CLI configuration. Run
  `npx supabase start` / `npx supabase db reset --local` from the repo root;
  it was initialized and migration-verified locally.
- This Supabase directory is linked to cloud project `TeamFixeth_AgriSense`
  (`quppbvckhinyslcebhfg`); migration `20260725023000_crops.sql` is deployed.
- `frontend/vite.config.js` sets `envDir: '..'` so Vite reads the shared ignored
  root `.env` instead of requiring a duplicate `frontend/.env`.
- The active app shell no longer renders the evidence/proof tab or development
  harness. `GraphPanel.jsx` is now the Bangla, freezeable animated provenance
  view; it intentionally omits the old raw English trace UI.
- The crop sidebar is a persistent Bangla “আমার ফসল” consultation list. A new
  item begins as “নতুন আলাপ”; `useChat.js` saves the agent's planned crop name
  through `useCrops.js` when `plan_update` arrives.
- `Sidebar.jsx` now separates resumable chats (“আমার আলাপ”) from saved crop
  detail records (“আমার ফসল”). `graphLayout.js` also exports the chronological
  linear layout used by `GraphPanel.jsx` for newest-node-centred animation.
- `20260725032500_crop_titles.sql` adds the persistent crop-record `title`.
  The agent emits a hidden first-reply Bangla title marker; `useChat.js` strips
  and saves it, while `Sidebar.jsx` uses it only for the chat list.
- Guest demo mode in `App.jsx` is completely client-side: `?guest=1` hides the
  sidebar and creates an ephemeral `{ session_id, farm_id: null }`, bypassing
  the RLS-protected crop API while retaining the public chat flow.
- `frontend/vite.config.js` proxies `/api` to the intended FastAPI port 8000.
  If `/api/crops` returns 404 there, restart the current API application rather
  than relying on an old listener.


## New in the final session (2026-07-25 07:00–08:35)

Backend — agent tools (A's territory, edited under the suspended A/B split, LOG2 [07:05]):
- `backend/tools/pest_risk.py` — Tier 1 pest/disease risk. 11 rules across the 5 crops
  keyed to `data/kb/corpus.json` passages. Inputs: crop + sowing date (recovered from the
  saved plan's `sowing` task) + district. Scores forecast days inside each organism's
  days-after-sowing window. `treatment_cost_bdt` is ALWAYS null — no citable pesticide
  price exists in any source here. Tests: `backend/tests/test_pest_risk.py` (10).
- `backend/tools/market_price.py` — Tier 2 market price intelligence over
  `agristats.db :: v_prices` (wholesale, Taka/Quintal -> Tk/kg). 12-month seasonal curve
  plus sell-now / consider-storing. Flagged `not_a_forecast` and `is_farm_gate: false`;
  MUST NOT reach the revenue path (that is `data/prices.md` via `finance/catalog.py`).
  Tests: `backend/tests/test_market_price.py` (9).
- `backend/tools/weather.py` — `get_forecast` now also returns `humidity_pct` per day
  (`relative_humidity_2m_mean`), None when unavailable. Retries without the variable if
  Open-Meteo rejects it, so the forecast itself can never be degraded by this addition.
- `backend/tools/crop_scorer.py` — the tool result gained a top-level `risk_basis` block
  stating what `risk_level` covers (yield variability) and what it does not (pest,
  extreme weather) with the reason for each. `_risk_level` itself is unchanged.
- `backend/agent/tools_spec.py` — 16 tools now (added `pest_risk`, `market_price`).
- `backend/agent/prompts.py` — new sections: "Risk level", pest_risk and market_price
  narration rules under Tier 1 follow-up actions.
- `backend/agent/loop.py` — `run_turn` takes `language` ("bn"/"en"); injects an English
  system note every turn when set to en. Tool params / RAG queries / trace stay English.
- `backend/schemas.py` — **`ChatRequest.language`** added (Literal["bn","en"], default
  "bn"). Additive and defaulted; the only frozen-contract change this session.
- `backend/api/chat.py` — forwards `payload.language` to `run_turn`.

Frontend:
- `frontend/src/i18n.js` — `translator(language)` -> `t(key)`. UI chrome only (~70 keys,
  bn + en); Bangla is the fallback. Farmer-facing ADVICE is never translated here — the
  agent writes it in the chosen language.
- `frontend/src/state/useSettings.js` — language / fontSize / voiceURI / voiceRate in
  localStorage (the app's only localStorage use). Applies root font-size and lang attr.
  Exports `FONT_PX` (small 13.5 / medium 15 / large 18; medium = the existing default).
- `frontend/src/state/useVoice.js` — `useDictation` (SpeechRecognition) and `useSpeech`
  (speechSynthesis). Both feature-detected; unsupported browsers get NO control, not a
  disabled one. Brave disables SpeechRecognition by default — demo in Chrome or Edge.
- `frontend/src/components/SettingsModal.jsx` — language / text size / voice + speed.
- `frontend/src/components/Sidebar.jsx` — rebuilt: new-chat, recent chats, my crops,
  bottom account row (avatar, email, settings gear, sign out).
- `frontend/src/lib/graphLayout.js` — `linearLayout` REPLACED by `verticalLayout`
  (one node per row top-to-bottom; long edges bow left; edges carry `d` + bow midpoint).
  `layout()` (radial) and `fitTransform()` remain unused.
- `frontend/src/components/GraphPanel.jsx` — cursor-anchored exponential zoom eased by a
  CSS transition on `.graph-viewport`; `userMovedRef` is now read so auto-follow stops
  after the first user gesture; captions right-anchored; recentre button.
- `frontend/src/components/ChatPanel.jsx` — pill composer with mic + send inside the
  field; read-aloud button on finished assistant replies; takes `t` and `settings`.
- `frontend/src/App.jsx` — renders `CheckoutPanel` behind a কেনাকাটা tab; the basket is
  derived from `chat.finance.scenarios.base.items` filtered to purchasable units
  (`BUYABLE_UNITS`), so boro/aman/potato (single `ha` aggregate cost line) get no tab.

Still absent (verified, not stubbed): plant disease image detection — no upload route,
no model, no vision call anywhere in the tree.

Also landed after the repograph note above: backend/tools/leaf_diagnosis.py
(PlantVillage MobileNetV2, CPU, lazy import) and backend/api/diagnose.py
(POST /api/diagnose/image, GET /api/diagnose/status), registered in
backend/api/main.py. Optional deps in backend/requirements-vision.txt -- the
backend starts fine without torch and the UI hides the camera button.
Tests: backend/tests/test_leaf_diagnosis.py.

Post-submission fixes (2026-07-25 09:20-09:40):
- backend/api/transcribe.py -- POST /api/transcribe, GET /api/transcribe/status.
  MediaRecorder blob -> OpenAI gpt-4o-transcribe. NOT whisper-1: whisper-1 returns
  Devanagari for Bangla and rejects language=bn. Extension is derived from the part
  content type (_EXTENSION_FOR / _base_type), because a mismatched suffix is
  rejected upstream as a corrupt file. Tests: backend/tests/test_transcribe.py.
- frontend/src/state/useVoice.js -- useDictation is now MediaRecorder-based with
  three states (idle / listening / transcribing) and Bangla+English error text.
  useSpeech (read-aloud) is unchanged and still browser-native.
- backend/tools/crop_scorer.py -- _profit_basis() -> top-level profit_basis key.
  Marks mustard/lentil non-comparable (fertiliser-only costs) and carries the
  exact Bangla ceiling wording the agent must print beside the number.
- backend/agent/prompts.py -- crop-ranking narration rules rewritten: profit
  labelling, season, climatology-not-forecast wording, water need is a crop fact,
  excluded crops must be named.
