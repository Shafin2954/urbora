# AgriSense AI

A Bangla-first PWA where a smallholder farmer talks to an autonomous agent that
produces a costed, weather-grounded season plan for their specific farm — and every
number in that plan carries provenance you can inspect.

Built for the IUT 12th ICT Fest Bdapps Agentic AI Hackathon, 24–25 July 2026.

---

## The one thing to know

**Every number on screen came from a call you can read, or it does not render.**

That rule is enforced structurally rather than by discipline:

- Money arithmetic happens only in `backend/finance/engine.py`, in `Decimal`, from
  cited rows in `data/prices.md`. The LLM never computes.
- Crop ranking happens only in `backend/tools/crop_scorer.py`, deterministically.
  The LLM never ranks.
- Prices with no citation produce a **refusal**, not an estimate.
- The UI's `<Value>` component takes a number and its provenance *together* and
  renders `—` if the provenance is missing. You cannot print an unsourced figure by
  forgetting a prop.

Where data is missing, the app says so — in Bangla, to the farmer, and in the trace,
to you. That honesty is the product, not a limitation of it.

---

## Tier coverage

Per the competition brief's tiered scope. "Done" means it runs end to end through the
live agent and UI, not just that the code exists.

### Tier 0 — Core (required)

| # | Capability | Status | Where |
|---|---|---|---|
| 1 | Conversational intake | **Done** | `ask_farmer` tool + `backend/agent/prompts.py` gap-detection; one missing field at a time via typed widgets (`InputRequest.jsx`) |
| 2 | Live weather grounding | **Done** | `get_forecast` (16-day, Open-Meteo, `source_type=forecast`) and `get_climatology` (historical normals, `source_type=climatology`) — real HTTP calls, never invented |
| 3 | Crop recommendation | **Done** | `crop_scorer` tool, deterministic, ranks the 5 supported crops on season/soil/water/climate/district track record/profit; `degraded` list discloses any missing evidence, relayed to the farmer before any ranking is shown |
| 4 | Season plan | **Done** | `season_plan` tool — dated, source-cited calendar (sowing → fertilizer → irrigation → weeding → harvest) for the confirmed crop and date; the LLM never invents a date |
| 5 | Financial projection | **Done** | `finance_projection` tool — itemised costs, yield (with uncertainty band), revenue, net profit, ROI, break-even yield/price, 3 scenarios; refuses rather than estimates if a price/cost citation is missing |
| 6 | Explained reasoning | **Done** | Every tool result carries `source_id`/`source_title`/`locator`/`confidence`; the agent narrates only what a tool returned, never its own recall |
| 7 | Knowledge base with RAG | **Done** | `rag_query` tool over `backend/kb/retrieval.py` — a small, deterministic, source-cited keyword-ranked retrieval layer over curated AIS e-Krishi / BAMIS / BRRI passages (see disclosure below: this is *not* a vector/embedding index). Called before every crop recommendation and again for the chosen crop's calendar |
| 8 | Visible agent trace | **Done** | Every tool call emits `tool_call`/`tool_result` SSE events; the "কাজের চিত্র" (work diagram) panel (`GraphPanel.jsx`) renders them as a provenance graph — click any node to see raw params/result in `NodeInspector.jsx` |

### Tier 1 — Advanced

| Capability | Status | Where |
|---|---|---|
| Persistent memory | **Done** | `remember_farm` tool + `backend/memory/store.py` (`farms` table); farm profile is keyed by `farm_id` and re-read on every turn and every crop-sidebar load, so a returning session doesn't repeat intake |
| Proactive, weather-triggered advice | **Done** | `check_plan_conflicts` tool compares the saved plan's weather-dependent tasks against the live forecast and persists traceable alerts; surfaced in `AlertPanel.jsx` ("আমার প্ল্যান চেক করুন") |
| Fertilizer and irrigation scheduler | **Done** | `care_schedule` tool — pulls fertilizer/irrigation tasks from the saved `season_plan`, with live forecast context when a task falls inside the 16-day horizon. Doses/timing are cited, never computed |
| Pest and disease risk | **Not implemented** | Out of scope for the 24-hour window; no pest/disease tool or model exists |
| Scenario simulation | **Done** | `simulate_budget` tool — re-runs deterministic ranking + finance under a changed budget ("what if my budget drops 30%?"); the server computes the delta, never the model |

### Tier 2 — Ambitious (bonus)

| Capability | Status | Notes |
|---|---|---|
| Marketplace / supplier comparison | **Not implemented** | Out of scope |
| Market price intelligence (sell-now/wait) | **Not implemented** | A real, cited TCB retail bulletin is displayed (see the real-vs-mock table) but deliberately kept unreachable from any revenue or sell/store/wait recommendation — see "Why retail prices cannot become revenue" below |
| Plant disease detection from images | **Not implemented** | Out of scope |
| bdapps Payment Gateway Integration | **Not implemented in this submission.** A simulator-plus-live payments module (`backend/payments/`: `simulator.py`, `client.py`, `service.py`, a server-enforced quote/confirm/checkout gate) was built earlier in the event, but it is **not wired into the agent's tool list or the shipped UI** — there is no checkout tab and no agent tool calls it. We chose to cut it from the demo path rather than ship a partially-integrated flow; the code remains in the tree, unused, as an honest record of that decision. |
| Bengali interaction | **Done** (text only) | All farmer-facing text is Bangla by default and mirrors the user's language; no voice input/output |

If you build only Tier 0 and it runs cleanly, per the brief that's a complete,
competitive submission — Tier 1 above it is where this build differentiates.

---

## What is real and what is not

| Data | Source | Status |
|---|---|---|
| Weather forecast (16-day) and climatology normals | Open-Meteo, live | **Real.** Every claim labelled `forecast` or `climatology`; climatology is never presented as a prediction |
| Geocoding | Open-Meteo geocoder + a hardcoded 64-district fallback | **Real.** Ambiguous names are confirmed with the farmer, never guessed |
| District yield history, 5 crops | `agribase_clean.db` (see disclosure below) | **Real, with a caveat** — read the disclosure |
| Damped-Holt yield projections + uncertainty band | Generated in-event by `backend/kb/holt.py` into `data/crop.db` | **Real, computed.** Every row discloses `n_points` and method |
| Selling prices (farm-gate) | `data/prices.md`, sourced from `agristats.db` (BBS Yearbook of Agricultural Statistics 2025) | **Real, cited.** All 5 crops have a farm-gate price row; a missing citation still refuses rather than estimates |
| Input costs (seed, fertiliser, labour) | `data/prices.md` | **Real for boro/aman/potato** (BBS aggregate cost-of-cultivation, cited). **Mustard/lentil are fertiliser-only** (Urea/TSP/MoP from BARC's FRG-2024 and BARI's Krishi Projukti Hatboi, priced against a 2023-04-11 government notice) — a stated minimum bound, not a complete cost, because no citable seed price was found for those two crops |
| Historic agricultural-input statistics (seed supply, fertilizer market, pesticide use, wages, irrigation) | `agristats.db`, BBS Chapter 7 | **Real, cited.** Exposed read-only via the `agri_inputs` tool; explicitly historic/aggregate reference data, never used to cost a plan |
| Agronomy knowledge base (crop calendars, cultivation guidance) | AIS e-Krishi, AIS কৃষিকথা, BAMIS, BRRI — curated into `backend/kb/retrieval.py` and `backend/kb/crop_facts.py` | **Real, cited, small.** A deterministic keyword-ranked lookup over ~6 hand-curated passages, not a vector database — see the RAG disclosure above |
| Retail market prices | TCB daily bulletin, Dhaka, 24-07-2026 | **Real, cited, dated** — and deliberately *unreachable* from any revenue calculation. See below |
| Crop calendars and soil/water suitability for the five supported crops | AIS e-Krishi, BAMIS and BRRI guidance | **Curated and cited.** The scorer deterministically screens season, soil, water and district climatology; a failed source lookup is disclosed in its degraded list |
| bdapps payments | Simulator + live-path code exists (`backend/payments/`) | **Built but not shipped.** Not reachable from the agent or the UI in this submission — see the Tier 2 table above |

### Why retail prices cannot become revenue

The TCB bulletin we hold is *retail Dhaka*: milled rice at 50–60৳/kg, split lentil dal
at 90–100৳/kg, potato at 25–30৳/kg. A farmer does not sell milled rice — they sell
**paddy**, unmilled, of which roughly 65% survives milling, at a farm-gate price
roughly half the retail one.

Wiring that number into revenue would have doubled every profit figure on screen, in
the direction that flatters us. So `data/prices.md` keeps those rows in a separate
table, `backend/finance/catalog.py` parses them for display only, and there is a test
asserting that a crop with costs and a retail row but no farm-gate row still refuses
to produce a projection.

### Yield data disclosure

District yield estimates are computed from a validated derivative of the supplied
agricultural dataset; the in-database source citation is pending verification; and
recommendations disclose this limitation. Do **not** read these as BBS-verified
figures. The derivative (`agribase_clean.db`) predates the event; everything derived
from it — `data/crop.db`, the Holt projections — is generated in-event with
timestamps and a git sha in a `meta` table.

---

## Conventions

- **1 bigha = 20 katha = 0.1338 ha.** The commonly quoted "1 bigha = 33 decimal" is an
  approximation — a bigha is really 33.06 decimal. We anchor bigha/katha on the
  sq-ft definition (so a bigha is exactly 20 katha) and leave acre/decimal on the
  exact international acre. The residual disagreement is 0.18%, and a test pins it.
- **1 maund = 40 kg**, the market/DAM maund, not the 37.3242 kg historical one. This
  matters: it is a 7% difference landing directly on revenue.
- Internal values are **always hectares and kilograms**. Local units exist only at the
  intake and display edges, via `backend/units.py`.
- **Western numerals everywhere**, with Bangla words around them, so a number on screen
  can be checked against the English trace panel.

## Crop coverage

Five crops: **boro rice, aman rice, potato, mustard, lentil.**

Wheat and maize are deliberately absent. Wheat has no yield series in the source at
all; maize's rows are visibly corrupt (one district's area exceeds the district). A
crop with no yield series cannot be ranked or costed without inventing a harvest, so
the tools return an honest error for them and the agent says so.

---

## Running it

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements.txt
cd frontend && npm ci && cd ..

# TWO env files — copy and fill in BOTH (see each file's header for why):
cp .env.example .env                          # Supabase + API host/port/CORS + VITE_* vars
cp backend/.env.example backend/.env           # OPENAI_API_KEY and the rest of the agent config
```

`backend/agent/config.py` reads `backend/.env` explicitly before it ever falls back to the
repo-root one, so the LLM key must go in `backend/.env`, not the root `.env` — putting it
in the wrong file is a common way to get a confusing "it starts but the agent has no key"
failure.

Fill in `backend/.env` (see `backend/.env.example`):

| Variable | Required for | Notes |
|---|---|---|
| `OPENAI_API_KEY` | the agent to run at all | the agent's LLM backend is OpenAI, not Anthropic — a deliberate mid-event provider swap from the original Claude/Sonnet plan (see `backend/agent/config.py`) |
| `OPENAI_MODEL` | — | defaults to `gpt-4o-mini`; must be tool-capable |

Fill in the repo-root `.env` (see `.env.example`):

| Variable | Required for | Notes |
|---|---|---|
| `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY` | the browser sign-in screen and crop sidebar | project's Supabase instance; browser-exposed anon key, RLS-protected |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` | the backend's `/api/crops` routes, which proxy the caller's own Supabase token | same project, server-side copy; read by `backend/api/config.py`, which loads the root `.env` |
| `SUPABASE_DB_PASSWORD` | the `supabase` CLI only (`db push`/`link`) | not read by application code |
| `VITE_DEMO_GUEST` | optional | `true` skips the Supabase login screen entirely for demo purposes (see below); the same effect is available per-session via `?guest=1` in the URL, or by clicking "অতিথি হিসেবে দেখুন" under the login form |

Then run both halves:

```bash
.venv/Scripts/python -m uvicorn backend.api.main:app --reload --port 8000
cd frontend && npm run dev        # http://localhost:5173, proxies /api to :8000
```

Tests (run before every merge — CLAUDE.md rule 12):

```bash
.venv/Scripts/python -m pytest tests/ backend/tests -q
```

Coverage spans the finance engine, `units.py`, the redactor, crop scoring, retrieval,
season-plan generation and persistence, plan-conflict checking, the care scheduler,
scenario simulation, and agri-input lookups — the places CLAUDE.md rule 12 asks for
tests, not UI coverage theater.

The PWA manifest only exists in the production build, so the phone install test must
run against `npm run build && npm run preview`, never `npm run dev`.

### Demo guest mode

The app normally sits behind Supabase email/password sign-in (`AuthScreen.jsx`), which
is a single point of failure if venue wifi drops mid-demo. A guest path bypasses it:
a "অতিথি হিসেবে দেখুন (ডেমো)" button appears under the login form, and `?guest=1` in the
URL (or `VITE_DEMO_GUEST=true`) skips straight past it. Guest identity is a local stub
(`{id:'guest', email:'guest@demo'}`) — it is never sent to Supabase. Because the crop
sidebar and chat history persistence go through `/api/crops`, which requires a real
Supabase-issued JWT verified by Supabase itself, those two features do not have data to
show in guest mode; the chat/agent path itself (the thing being judged) needs no
Supabase session and works normally.

### Payments

Not part of this submission — see the Tier 2 table above. `backend/payments/` exists
in the tree from earlier in the event but is not called by the agent or reachable from
the UI; no checkout flow ships.

---

## Architecture

```
backend/
  agent/      the loop, prompts, tool specs, LLM client (OpenAI backend)
  tools/      geocode · weather · cropdb · crop_scorer · finance · season_plan ·
              plan_conflicts · care_scheduler · scenario · agri_inputs ·
              ask_farmer · remember_farm
  kb/         holt.py (Holt yield projections) · retrieval.py (rag_query's corpus) ·
              crop_facts.py (curated agronomic facts the scorer reads)
  finance/    engine.py (Decimal, the only place money math happens) + catalog.py
  payments/   bdapps client + simulator twin + confirmation gate (built, not shipped — see above)
  memory/     SQLite WAL: conversation history and farm profiles
  api/        FastAPI routes, SSE transport, redacting trace emitter, Supabase-proxying crop index
  units.py    bigha/katha/maund conversions
frontend/     Vite + React, one responsive page, manifest-only PWA
data/         crop.db (generated in-event) · prices.md (cited price tables)
```

**Agent tools** (registered in `backend/agent/tools_spec.py`, dispatched by name; every
call emits a traced `tool_call`/`tool_result` pair):

| Tool | Does |
|---|---|
| `ask_farmer` | Asks the farmer one missing intake field at a time, with the right input widget |
| `geocode` | Resolves a place/district name to coordinates (Open-Meteo geocoder + 64-district fallback) |
| `get_forecast` | 16-day weather forecast for coordinates |
| `get_climatology` | Historical monthly normals for coordinates |
| `rag_query` | Source-cited agronomy passages from the curated local KB |
| `cropdb_sql` | District yield history, Holt yield projection, and yield track record |
| `agri_inputs` | Historic BBS Chapter 7 seed/fertilizer/pesticide/wage/irrigation reference facts |
| `crop_scorer` | Deterministic ranking of the 5 supported crops for a farm profile |
| `finance_projection` | Costed 3-scenario financial projection for one crop |
| `season_plan` | Dated, source-cited task calendar for a confirmed crop and date |
| `check_plan_conflicts` | Compares a saved plan's weather-dependent tasks against the live forecast |
| `care_schedule` | Fertilizer/irrigation tasks due from a saved plan, with forecast context |
| `simulate_budget` | Re-runs ranking + finance under a changed budget |
| `remember_farm` | Persists the confirmed farm profile for future turns/sessions |

The agent streams Server-Sent Events; every tool call emits `tool_call` and
`tool_result` into a live trace, rendered as a provenance graph (`GraphPanel.jsx`) with
a raw chronological log nested underneath. Redaction happens in the event constructors
*and* again at the serializer: passwords, app ids, keys and tokens become `***`; phone
numbers keep their last three digits so a human can still confirm which SIM was
involved — because a leaked credential in a judge-facing panel is not a recoverable
mistake.

## Competition rules compliance

All application code — the parser, the Holt fitting, the finance engine, the agent —
was written and run during the event. Derived artifacts (`data/crop.db`, the
projections) are generated in-event and carry timestamps plus a git sha. Raw public
yearbook PDFs are not committed (234 MB); they are public documents hosted separately.
Pre-cached third-party models and wheels are used but not authored here.

## Horizon 2

`crop.db`'s long/tidy, provenance-per-row design generalises to an `observations`
table covering all 146 crops, livestock, fisheries, prices, weather and disaster loss
across all 14 yearbook editions (2012–2025) — turning AgriSense from one farmer's
advisor into a citable agricultural intelligence layer for Bangladesh, under the same
rule throughout: every number carries its page.
