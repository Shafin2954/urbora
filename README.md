# উর্বরা (Urbora) — স্বপ্ন ফলুক

A Bangla-first farm advisor a smallholder can reach from **any phone**: a voice call, a USSD
code, an SMS, or the web app. One agent builds a costed, weather-grounded season plan for
the farmer's own land, where every number carries the source it came from, and then helps
them act on it: buy inputs from a nearby dealer and sell the harvest to buyers.

- **Web:** <https://urbora-team-uplift.netlify.app> (frontend on Netlify, API on Replit).
- **History:** built in July 2026 for the IUT ICT Fest bdapps Agentic AI Hackathon (tag
  `tier0-stable` in the old repo `TeamFixeth_AgriSense`; working name AgriSense). The Grameenphone FutureMakers 2026 round added
  the phone channels and the marketplaces. Shown next at the AI Builders Congress
  (OpenCloud, Bangladesh), then going to real farmers.
- The product name lives in one place: `backend/branding.py` / `frontend/src/branding.js`.

## The one rule

**Every number on screen came from a call you can read, or it does not render.**

- Money arithmetic happens only in `backend/finance/engine.py` (`Decimal`, cited prices from
  `data/prices.md`). Crop ranking happens only in `backend/tools/crop_scorer.py`. The LLM
  narrates tool results; it never computes and never ranks.
- A price with no citation produces a refusal, not an estimate.
- The UI renders a number only together with its provenance.
- Missing data is said out loud, in Bangla to the farmer and in the trace to you.

The full ledger of what is real, simulated or missing: [docs/product/REAL_VS_DEMO.md](docs/product/REAL_VS_DEMO.md).

## Status (2026-11-10)

| Door | Works today | Notes |
|---|---|---|
| Web app (`#/app`) | **Yes** | Sign in (Supabase) or continue as a guest |
| SMS | **Yes**, verified on real SIMs (Sept 2026) | Through an Android phone running SMS Gateway; simulator otherwise |
| SMS menu (text **মেনু**) | **Yes**, on real SIMs | The USSD menu over plain SMS, no short code needed |
| USSD `*code#` | **In the simulator** | A real short code needs bdapps/operator approval |
| Missed call → SMS | **In the simulator** | ADB bridge built |
| Voice call | **Yes, on a real phone** (first calls 2026-11-10) | Through Windows Phone Link; on the Motorola test phone calls are answered by hand for now |
| Input + produce marketplaces | **Yes, with demo dealers/buyers** | Demo rows are labelled ডেমো everywhere; demo dealers exist only in Rajshahi |
| Leaf-photo diagnosis | Optional | Needs `backend/requirements-vision.txt` (~200 MB); hidden otherwise |
| Payments (bdapps) | **Simulator only** | No real money moves; confirmation is enforced server-side |

What each capability does, tier by tier, and the 17 agent tools: [docs/product/CAPABILITIES.md](docs/product/CAPABILITIES.md).

## Run it locally (Windows; same idea elsewhere)

From the repo root:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements.txt
```

Put your keys in **one file, `.env.local`** at the repo root. At minimum:
`OPENAI_API_KEY` (the agent runs on OpenAI `gpt-4o`; do not switch to `gpt-4o-mini`, which
skips tool calls). Every other setting is documented in `.env.example` and
`backend/.env.example`.

```bash
npm run dev
```

This starts the API on :8000 and the web app on <http://localhost:5000> (it installs the
frontend packages on first run). `npm run app` builds the frontend and serves everything
from :8000 instead. Optional, once: `python -m backend.market.seed_demo` loads the labelled
demo dealers and buyers.

Run every command from the **repo root**: `backend` is the Python package root.

## Tests

```bash
.venv/Scripts/python -m pytest backend/tests -q
```

650 tests, all in `backend/tests/` (finance, units, ranking, redaction, channel menus, SMS
budgeting, marketplace, voice). They are hermetic: your real keys in `.env.local` are
stripped during tests. `npm run build` checks the frontend; `npm run e2e` drives three
farmers through the web app with Playwright.

## Phone channels

Simulator testing, real SMS through an Android phone, bdapps USSD, and real voice calls
through Windows Phone Link + Voicemeeter: [docs/channels/PHONE_SETUP.md](docs/channels/PHONE_SETUP.md).

## Where things are

```
backend/     API, agent, tools, phone channels, marketplaces, all tests
frontend/    Vite + React web app
data/        databases and cited price tables the backend reads
docs/        spec, research, setup guides, deploy notes, history
scripts/     dev runner, end-to-end test
supabase/    web-account database migrations
brand/       brand kit;   video/  pitch-video pipeline
```

The full file map, kept current for people and AI agents: **[docs/MAP.md](docs/MAP.md)**.
Known traps: [docs/NOTES.md](docs/NOTES.md). Product spec: [docs/product/PRD.md](docs/product/PRD.md).

## Conventions

- 1 bigha = 20 katha = 0.1338 ha; 1 maund = 40 kg. Internally always hectares and kilograms;
  local units exist only at the edges, via `backend/units.py`.
- Western numerals for numbers, Bangla words around them.
- Five crops: boro rice, aman rice, potato, mustard, lentil. Wheat and maize are absent on
  purpose (no usable yield series), and the agent says so.

## Working on this repo

- AI agents: read [AGENTS.md](AGENTS.md) first (`CLAUDE.md` imports it).
- Work on `main` in the private repo `Shafin2954/urbora`; push only with the full suite green.
  The hackathon history (`master`, `futuremakers`, tag `tier0-stable`) stays in the old repo
  `Shafin2954/TeamFixeth_AgriSense`.
- Log every unit of work in `LOG4.md`; update `docs/MAP.md` when files move or change purpose.
- Secrets go only in `.env.local` / `.env` / `backend/.env` (all gitignored).
