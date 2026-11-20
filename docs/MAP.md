# Map: what lives where

The file map for people and AI agents. **Keep it current:** when you add, move or repurpose a file or folder, update this page in the same commit (AGENTS.md §1). "?" means not yet known.

Last full rewrite: 2026-11-10 (repo cleanup; replaces the old `repograph.md`).

## Top level

| Path | What it is |
|---|---|
| `README.md` | Start here: what the product is, how to run it, what is real vs demo |
| `AGENTS.md` | Rules for every AI agent (`CLAUDE.md` only imports it) |
| `LOG.md` | Current work log, append-only. Older logs are in `docs/logs/` |
| `backend/` | Python API, agent, tools, phone channels, marketplaces, all tests |
| `frontend/` | Vite + React web app (PWA manifest, no service worker) |
| `data/` | Databases and price tables the backend reads (in git), plus `raw/` for local source PDFs (not in git) |
| `ml/yieldmax/` | Reproducible yield training notebook, team run instructions, metrics and row-level backtest evidence |
| `docs/` | Everything written for people: spec, research, deploy notes, history |
| `scripts/` | `dev.mjs` (run API + web together), `e2e_farmers.mjs` (Playwright run of three farmers) |
| `supabase/` | Supabase CLI config + migrations for web accounts (`crops` table, RLS) |
| `brand/` | Brand kit: name, voice, logo, tokens, asset build scripts |
| `video/` | Pitch-video pipeline (FutureMakers Round 1); not used by the app |
| `package.json` | `npm run dev` / `app` / `build` / `e2e` |
| `.replit`, `start.sh`, `pyproject.toml`, `uv.lock` | Replit hosting. Replit installs from `pyproject.toml`, **not** `backend/requirements.txt`; keep both in step |
| `netlify.toml` | Netlify hosting of the static frontend; it calls the Replit API |
| `.env.example`, `backend/.env.example` | Every setting, documented. Real values go in `.env.local` (see Env below) |
| `.claude/launch.json` | Dev servers for Claude Code: `backend` :8000, `frontend` :5000, `backend-sim` :8020 |

## How it runs

- **Dev:** `npm run dev` → API on :8000 (auto-reload) + Vite on :5000. Vite proxies `/api` to :8000, so there is no CORS in dev (NOTES #13).
- **One process:** `npm run app` → builds `frontend/dist`, and `backend/api/main.py` serves it with an SPA fallback on :8000.
- **Replit:** dev runs `start.sh`; deployment builds the frontend and runs uvicorn on :5000 (`.replit`).
- **Netlify:** static frontend only, `VITE_API_BASE` → Replit API; Replit's `CORS_ORIGINS` must list the Netlify origin.
- **Python env:** `.venv/` at the repo root (both `launch.json` and `scripts/dev.mjs` use it).
- **Env loading** (`backend/env.py`): `.env.local` > `backend/.env` > `.env`, and real environment variables win over all three. Vite reads the root env files too (`envDir: '..'`).

## backend/

The package root is `backend`; import as `backend.agent.loop` and run everything from the repo root.

**Contract and shared**
- `schemas.py`: THE CONTRACT. Pydantic models for provenance, farm, crops, plan, finance, every SSE event, request bodies. Changes are additive only and logged.
- `branding.py`: the product name (উর্বরা / Urbora). Never hardcode it elsewhere.
- `units.py`: the only place local units (bigha, katha, maund…) exist. Internal is ha and kg.
- `env.py`: env-file loading order (above).

**agent/** (the LLM loop; the model narrates, it never computes or ranks)
- `loop.py`: `run_turn(session_id, farm_id, message, channel=, language=, context_note=)`. Max 12 iterations, cost in the `done` event.
- `llm_client.py`: OpenAI backend behind a provider-neutral interface. `config.py`: model and limits from env (`OPENAI_MODEL`, default gpt-4o).
- `prompts.py`: system prompt. `tools_spec.py`: the 17 tool schemas + `dispatch()`.
- `intake_guard.py`: refuses to plan on farm facts the farmer never gave.

**tools/** (what the agent can call; each returns provenance)
- Place and weather: `geocode.py` (with the offline fallback `districts.py`), `weather.py` (`get_forecast` labelled forecast, `get_climatology` labelled climatology).
- Yields and ranking: `cropdb.py` (read-only yields from `data/agribase_clean.db` + `data/crop.db`), `crop_scorer.py` (deterministic ranking, PRD §6).
- Money: `finance.py` (`finance_projection`, which calls `backend/finance/engine.py`), `scenario.py` (`simulate_budget`).
- Plan and care: `season_plan.py`, `care_scheduler.py`, `plan_conflicts.py` (plan vs live forecast), `pest_risk.py`.
- Data lookups: `agri_inputs.py` (`data/agristats.db` input facts), `market_price.py` (wholesale price curve; never feeds revenue).
- Conversation: `ask.py` (`ask_farmer`, puts an intake widget on screen), `farm_memory.py` (`remember_farm`).
- `leaf_diagnosis.py`: leaf-photo model. Optional; needs `backend/requirements-vision.txt` (~200 MB torch). Without it, `/api/diagnose/status` says unavailable and the UI hides the camera.

**finance/**: `engine.py` (the only money arithmetic, `Decimal`), `catalog.py` (reads `data/prices.md`), `market.py` (order totals, commission, produce-deal fee).

**kb/**: `retrieval.py` (`rag_query` over `data/kb/corpus.json`), `crop_facts.py` (cited agronomy facts for the scorer), `holt.py` (regenerates `data/crop.db`: `python -m backend.kb.holt`), `triage.py` (deterministic crop-problem table).

**api/** (FastAPI; `main.py` mounts every router)
- `chat.py`: `POST /api/chat` (SSE). `sse.py`: wire format; `tool_call`/`tool_result` redact by construction. `redact.py`: the redactor.
- `finance.py`, `plans.py`, `alerts.py`, `checkout.py` (simulator-first payments, server-enforced confirmation), `crops.py` (Supabase accounts + guest sessions), `triage.py`, `diagnose.py`, `transcribe.py` (composer mic → gpt-4o-transcribe), `market.py` (`/api/market/*`), `channels.py` (`/api/channels/*`).

**channels/** (SMS, USSD, voice; same agent, same farm memory)
- `adapter.py`: `run_channel_turn` turns an agent turn into text + a numbered menu. `identity.py`: phone → hashed farm id.
- `sms.py` (providers `smsgate` / `bdapps` / `simulator`), `sms_text.py` (segment budgeting, templates), `sms_menu.py` (USSD menu over SMS), `flows.py` (inbound SMS, missed call, call summary).
- `ussd.py` (pure state machine; never waits on the LLM, answers go by SMS), `triage_menu.py` (menu 2: crop problem), `alerts_job.py` (rain-conflict SMS).
- `bridge/adb.py` (missed-call watcher over USB), `bridge/phone_up.py` (phone as SMS gateway via the SMS Gateway app).
- `voice/speech.py` (Sarvam / OpenAI / Azure STT+TTS), `voice/turn.py` (one spoken turn; `spoken_text` is what a caller hears; hang-up → SMS summary), `voice/ivr.py` (keypad menu spoken), `voice/audio.py` (VAD, DTMF, ADB call-state parser), `voice/phonelink.py` (real calls through Windows Phone Link + Voicemeeter; setup in `docs/channels/PHONE_SETUP.md`).

**market/**: `inputs.py` (find offers, orders, dealers), `produce.py` (listings, buyer offers), `ranking.py` (deterministic dealer ranking), `catalog.py`, `db.py`, `sms_commands.py`, `ussd_menus.py`, `seed_demo.py` (labelled demo dealers/buyers, all in Rajshahi: `python -m backend.market.seed_demo`).

**payments/**: bdapps `simulator.py` (exact documented shapes), `client.py` (live), `service.py` (mode toggle, defaults to simulator), `msisdn.py`.

**memory/**: `store.py`, SQLite WAL at `backend/memory/memory.db` (gitignored runtime state: sessions, farms, plans, SMS log, USSD sessions, market tables). `seed_demo.py`: the rehearsed demo farm.

**tests/**: the whole suite (`.venv/Scripts/python -m pytest backend/tests -q`). `conftest.py` strips provider env vars so a developer's real keys never leak into tests, and provides the `priced_md` fixture (fake, labelled prices).

**Requirements:** `requirements.txt` (core, pinned), `requirements-voice-bridge.txt` (only the laptop running real calls), `requirements-vision.txt` (only for leaf photos).

## frontend/

- Routes (`src/Root.jsx`, hash-based): home (default, `pages/HomePage.jsx`), `#/app` (the advisor, `App.jsx` + `shell.css`), `#/check` (home scrolled to the crop check), `#/market`, `#/dealer`, `#/buyer` (`pages/MarketPage.jsx`, `pages/PartnerPages.jsx`), `#/monitor` (live channel monitor, `components/ChannelMonitor.jsx`).
- `src/state/useChat.js`: the only place SSE event semantics live. Other state: `useAuth`, `useCrops`, `useGuestSessions` (guests, localStorage), `useSettings`, `useVoice`, `useCheckout`.
- `src/api/`: one client per backend area (`sse.js` is spec-correct SSE over fetch).
- Components: `ChatPanel`, `InputRequest` (the intake widgets), `PlanPanel`, `FinancePanel`, `CheckoutPanel`, `AlertPanel`, `GraphPanel` (provenance graph; layout in `lib/graphLayout.js`, data in `lib/traceGraph.js`), `Provenance` (a number renders only with its source), `CropCheck`, `Sidebar`, `SettingsModal`, `AuthScreen`, `SiteNav`, `BrandMark` (logo from `lib/seal.js`).
- `src/lib/engraving.js`: brand grain pattern; also imported by `brand/scripts`.
- `src/branding.js`, `src/i18n.js` (UI chrome bn/en; advice is never translated here), `index.css` (design tokens).
- `public/img/`: generated photos for the home page; their prompts are in `brand/IMAGE_PROMPTS.md`.
- `vite.config.js`: port 5000, `/api` proxy to :8000 (`API_PROXY_TARGET` overrides), PWA manifest only (NOTES #8).

## data/

- `crop.db`: generated yield projections (damped Holt) + meta with git sha. Regenerate: `python -m backend.kb.holt`.
- `agribase_clean.db`: validated yields derived from a supplied `crops.db` (how: `docs/data/AGRIBASE_CLEANING.md`). Read only through safe views.
- `agristats.db`: BBS yearbook extraction (prices, inputs). Read-only.
- `prices.md`: the cited farm-gate prices and input costs the finance engine uses.
- `kb/corpus.json`: the curated agronomy passages behind `rag_query`.
- `sources/`: original source files kept for reference (`Dhaka retail price.xlsx`).
- `raw/`: local PDFs (gitignored, `*.pdf`).

## docs/

| Path | What it is |
|---|---|
| `docs/MAP.md` | This page |
| `docs/NOTES.md` | Known traps, numbered. Code cites them ("NOTES #13"); keep the numbers stable |
| `docs/product/PRD.md` | Product spec |
| `docs/product/CAPABILITIES.md` | What the advisor does, tier by tier; the 17 agent tools |
| `docs/product/REAL_VS_DEMO.md` | Honesty ledger: every data source, real / simulated / missing, plus disclosures |
| `docs/product/competition.md` | Hackathon brief; code comments cite its tiers |
| `docs/product/FIELD_INSIGHTS.md` | Real farmer interview (Dinajpur) |
| `docs/product/architecture.svg` | Agent architecture diagram |
| `docs/channels/PHONE_SETUP.md` | Real SMS, USSD and voice calls on a phone; simulator testing |
| `docs/channels/CHANNELS_RESEARCH.md` | Verified telecom facts; read before touching channels |
| `docs/channels/BDAPPS-API-REFERENCE.md`, `BDAPPS-PREFLIGHT-CHECKLIST.md` | bdapps API shapes and go-live checklist |
| `docs/deploy/WEBSITE_HANDOFF.md`, `docs/deploy/replit.md` | Netlify + Replit deployment |
| `docs/data/AGRIBASE_CLEANING.md`, `build_agribase_clean.sql` | How `data/agribase_clean.db` was built |
| `docs/logs/LOG1.md`–`LOG3.md` | Closed hackathon logs |
| `docs/archive/hackathon/` | July schedule (`PLAN.md`; code comments cite "PLAN §2" for the contract), task list, Tier 0 acceptance, an SSE audit dump |
| `docs/archive/round1/` | FutureMakers Round 1 brief, form drafts, review, profile plan, `form_check.py` (reads its own folder) |
| `docs/archive/repograph-2026-09.md` | The previous file map, superseded by this page |

## brand/ and video/

- `brand/BRAND-CORE.md` is the brand source of truth. `brand/scripts/*.mjs` rebuild logos, patterns and web assets.
- `video/`: `VIDEO_HANDOFF.md`, `VIDEO_STORYBOARDS.md`, `PLAN_v5.md` (current plan), `build/` (render pipeline; `timeline.py` holds all timings). Audio and renders are not in git.

## Gitignored runtime state (exists locally, never committed)

`.env*` (except examples), `.venv/`, `backend/memory/memory.db`, `backend/.cache/` (weather cache), `frontend/dist/`, `node_modules/`, `data/raw/*.pdf`, `supabase/.temp/`.
