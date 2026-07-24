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

## What is real and what is not

| Data | Source | Status |
|---|---|---|
| Weather forecast (16-day) and climatology normals | Open-Meteo, live | **Real.** Every claim labelled `forecast` or `climatology`; climatology is never presented as a prediction |
| Geocoding | Open-Meteo geocoder + a hardcoded 64-district fallback | **Real.** Ambiguous names are confirmed with the farmer, never guessed |
| District yield history, 5 crops | `agribase_clean.db` (see disclosure below) | **Real, with a caveat** — read the disclosure |
| Damped-Holt yield projections + uncertainty band | Generated in-event by `backend/kb/holt.py` into `data/crop.db` | **Real, computed.** Every row discloses `n_points` and method |
| Selling prices (farm-gate) | `data/prices.md` | **Not yet curated.** Tables are empty; every consumer refuses rather than estimating |
| Input costs (seed, fertiliser, labour) | `data/prices.md` | **Not yet curated.** Same |
| Retail market prices | TCB daily bulletin, Dhaka, 24-07-2026 | **Real, cited, dated** — and deliberately *unreachable* from any revenue calculation. See below |
| Crop calendars, fertiliser doses, soil/water suitability | BARC / BRRI / BARI documents | **Not curated.** The scorer reports these components "unavailable" rather than guessing |
| bdapps payments | Simulator matching the documented API shapes | **Simulated, labelled everywhere.** Live path exists and is config-gated |

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

# .env at the REPO ROOT (both halves read it from there)
cp .env.example .env      # then fill in OPENAI_API_KEY

.venv/Scripts/python -m uvicorn backend.api.main:app --port 8000
cd frontend && npm run dev        # http://localhost:5173, proxies /api to :8000
```

Tests (run before every merge — CLAUDE.md rule 12):

```bash
.venv/Scripts/python -m pytest tests/ backend/tests -q
```

The PWA manifest only exists in the production build, so the phone install test must
run against `npm run build && npm run preview`, never `npm run dev`.

### Payments

Simulator by default. `BDAPPS_MODE=live` plus `BDAPPS_APP_ID` / `BDAPPS_PASSWORD`
switches to the real API; a missing, mistyped or credential-less mode always falls
back to the simulator, because the safe direction is the only acceptable default. The
mode shown in the UI is read off the client object actually in use — simulated output
cannot be hand-labelled live.

Checkout always has a server-enforced confirmation step: `/api/checkout` refuses with
409 unless a matching, unexpired, single-use quote exists. A stray POST cannot take a
farmer's money, and a double-tap cannot charge twice.

---

## Architecture

```
backend/
  agent/      the loop, prompts, tool specs, LLM client (OpenAI backend)
  tools/      geocode · weather · cropdb · crop_scorer · finance · ask_farmer · remember_farm
  finance/    engine.py (Decimal, the only place money math happens) + catalog.py
  payments/   bdapps client + simulator twin + confirmation gate
  memory/     SQLite WAL: conversation history and farm profiles
  api/        FastAPI routes, SSE transport, redacting trace emitter
  units.py    bigha/katha/maund conversions
frontend/     Vite + React, one responsive page, manifest-only PWA
data/         crop.db (generated in-event) · prices.md (cited price tables)
```

The agent streams Server-Sent Events; every tool call emits `tool_call` and
`tool_result` into a live trace panel, **redacted**: passwords, app ids, keys and
tokens become `***`; phone numbers keep their last three digits so a human can still
confirm which SIM was charged. Redaction happens in the event constructors *and* again
at the serializer, because a leaked credential in a judge-facing panel is not a
recoverable mistake.

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
