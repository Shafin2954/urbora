# AgriSense AI (working name)

A Bangla-first farm advisor that a smallholder farmer can reach from **any phone**:
a voice call, a USSD code, an SMS, or the web app. One autonomous agent produces a
costed, weather-grounded season plan for their specific farm — every number in it
carries provenance you can inspect — and then helps them act on it: buy the right
inputs from a nearby dealer, and sell the harvest directly to buyers.

The web demo is live at [https://team-fixeth-agri-sense--Shafin54.replit.app](https://team-fixeth-agri-sense--Shafin54.replit.app).

- **July 2026:** built for the IUT 12th ICT Fest Bdapps Agentic AI Hackathon
  (the web advisor; tag `tier0-stable`).
- **September 2026:** entered in **Grameenphone FutureMakers 2026**, track
  *Digital Inclusion & Education*. This round added the button-phone channels and the
  two marketplaces — see [New in the FutureMakers round](#new-in-the-futuremakers-round)
  and `LOG4.md`. The product name is being changed; it is one constant
  (`backend/branding.py`, `frontend/src/branding.js`, or `BRAND_NAME` in `.env`).

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
  renders `—` if the provenance is missing. You cannot print an unsourced figure
  by forgetting a prop.

Where data is missing, the app says so — in Bangla, to the farmer, and in the
trace, to you. That honesty is the product, not a limitation of it.

---

## New in the FutureMakers round

Only about 1 in 4 rural mobile users in Bangladesh owns a smartphone (GSMA, 2024),
so the advisor now has four doors onto the same agent, the same farm memory and the
same tools:

| Door | Phone | Status | Where |
|---|---|---|---|
| Web app | smartphone | **Working** (the July build) | `frontend/`, `POST /api/chat` |
| SMS | any | **Working in the simulator; real SMS via an Android phone is built but not yet run on a device** | `backend/channels/sms.py`, `flows.py`; `POST /api/channels/sms/smsgate` |
| Missed call → SMS | any | **Working in the simulator; ADB bridge built, not yet run on a device** | `backend/channels/bridge/adb.py` |
| USSD `*code#` | any | **Working in the simulator** (a real short code needs operator provisioning); bdapps request/response shape implemented | `backend/channels/ussd.py`; `POST /api/channels/ussd/bdapps` |
| Voice call | any | **Push-to-talk in the browser emulator.** Speech providers wired; **quality not yet verified** (needs `SARVAM_API_KEY` or Azure keys and an ear test). Real phone calls need a USB 4G modem — driver planned, waiting for hardware | `backend/channels/voice/` |
| Proactive alerts by SMS | any | **Working** (opt-in loop) | `backend/channels/alerts_job.py` |

And two marketplaces that turn advice into action:

| Marketplace | Status | Where |
|---|---|---|
| **Input marketplace** — the agent's `find_inputs` tool ranks nearby dealers (price 40, distance 30, stock 15, trust 15; no paid placement); order on the web, USSD menu 4 or SMS; the dealer confirms by SMS; commission paid by the dealer | **Working, with demo dealers** (labelled ডেমো everywhere) | `backend/market/inputs.py`, `ranking.py`; `#/market`, `#/dealer` |
| **Produce marketplace** — the farmer lists the harvest (`বিক্রি আলু 500 কেজি 22 টাকা`), sees a cited price guide, buyers offer, the farmer accepts with one SMS reply; the platform fee is paid by the buyer | **Working, with demo buyers** | `backend/market/produce.py`; `#/market`, `#/buyer` |

Try it: `#/phone` is a button-phone emulator (dial `*3700#`, SMS, missed call, call),
`#/monitor` replays every phone conversation into the provenance graph, `#/market` is
the farmer's marketplace. Everything simulated is labelled **সিমুলেটর** or **ডেমো**.

### What never changed

Every channel runs the same agent under the same rules: numbers come only from tool
results (the LLM never does arithmetic or ranks — crops *or* dealers), every price
carries provenance, and a missing source is said out loud. SMS and USSD numbers are
inserted by templates from tool payloads (`backend/channels/sms_text.py`), never
written by the model. Phone numbers are stored in one table (`contacts`); everything
else keys on a salted hash, and traces show the last 3 digits only.

### Tool choices (researched September 2026)

| Need | Choice | Why |
|---|---|---|
| Bangla speech-to-text | **Sarvam** (`saaras`), OpenAI `gpt-4o-transcribe` as fallback | A Sep-2026 Bangla benchmark over 1,001 clips ([riverbornai](https://github.com/riverbornai/bangla-speech-to-text-benchmark/releases/tag/v1.0.0)) measured Sarvam at 6.9% CER vs 28.7% for `gpt-4o-transcribe`. Not yet re-verified on our own district-name sentence |
| Bangla text-to-speech | Sarvam Bulbul, Azure `bn-BD` (Dhaka accent) or OpenAI — a config switch | To be chosen by a listening test |
| SMS gateway (pilot) | [SMSGate](https://github.com/capcom6/android-sms-gateway) on an Android phone (Apache-2.0, local-server REST + signed webhooks) | Free, real SMS |
| Real phone calls (pilot) | Quectel EC2x USB 4G modem (planned) | An Android phone cannot hand call audio to an app without root |
| USSD emulator, marketplace | Own code | Existing USSD simulators speak other operators' formats; a separate commerce stack (e.g. Medusa) would duplicate our Decimal finance engine |

## Agent System Architecture

![Architecture](<agrisense_agent_architecture (1).svg>)

---

## Tier coverage

Per the competition brief's tiered scope. "Done" means it runs end to end
through the live agent and UI, not just that the code exists.

### Tier 0 — Core (required)

| # | Capability | Status | Where |
|---|---|---|---|
| 1 | Conversational intake | **Done** | `ask_farmer` tool + `backend/agent/prompts.py` gap-detection; one missing field at a time via typed widgets (`InputRequest.jsx`) |
| 2 | Live weather grounding | **Done** | `get_forecast` (16-day, Open-Meteo, `source_type=forecast`) and `get_climatology` (historical normals, `source_type=climatology`) — real HTTP calls, never invented |
| 3 | Crop recommendation | **Done** | `crop_scorer` tool, deterministic, ranks the 5 supported crops on season/soil/water/climate/district track record/profit; `degraded` list discloses any missing evidence, relayed to the farmer before any ranking is shown |
| 4 | Season plan | **Done** | `season_plan` tool — dated, source-cited calendar (sowing → fertilizer → irrigation → weeding → harvest) for the confirmed crop and date; the LLM never invents a date |
| 5 | Financial projection | **Done** | `finance_projection` tool — itemised costs, yield (with uncertainty band), revenue, net profit, ROI, break-even, 3 scenarios; refuses rather than estimates if a price/cost citation is missing |
| 6 | Explained reasoning | **Done** | Every tool result carries `source_id`/`source_title`/`locator`/`confidence`; the agent narrates only what a tool returned, never its own recall |
| 7 | Knowledge base with RAG | **Done** | Two separate, real mechanisms, not one — see "Two knowledge sources" below. `rag_query` retrieves from 52 cited passages; `crop_scorer` reads a separate hand-curated facts table directly. Called before every crop recommendation and again for the chosen crop's calendar |
| 8 | Visible agent trace | **Done** | Every tool call emits `tool_call`/`tool_result` SSE events; the "কাজের চিত্র" (work diagram) panel (`GraphPanel.jsx`) renders them live as a Bangla-labeled provenance graph — see "What the trace panel actually shows" below for exactly what it does and doesn't expose |

### Tier 1 — Advanced

| Capability | Status | Where |
|---|---|---|
| Persistent memory | **Done** | `remember_farm` tool + `backend/memory/store.py` (`farms` table); farm profile is keyed by `farm_id` and re-read on every turn and every crop-sidebar load, so a returning session doesn't repeat intake |
| Proactive, weather-triggered advice | **Done** | `check_plan_conflicts` tool compares the saved plan's weather-dependent tasks against the live forecast and persists traceable alerts; surfaced in `AlertPanel.jsx` ("আমার প্ল্যান চেক করুন") |
| Fertilizer and irrigation scheduler | **Done** | `care_schedule` tool — pulls fertilizer/irrigation tasks from the saved `season_plan`, with live forecast context when a task falls inside the 16-day horizon. Doses/timing are cited, never computed |
| Pest and disease risk | **Done** | `pest_risk` tool (`backend/tools/pest_risk.py`) — deterministic crop x growth-stage x weather rules for 11 named pests/diseases across the 5 crops. Stage windows are days-after-sowing from the confirmed planting date; triggers are evaluated against the live 16-day forecast including daily mean humidity. Prevention/treatment text and doses come verbatim from the 14 cited pest/disease KB passages. **Treatment cost is reported as unavailable, not estimated** — no citable Tk price for any pesticide or fungicide exists in our sources (see the real-vs-mock table). A risk whose window opens beyond the forecast horizon returns `status: upcoming` with no level rather than an invented prediction |
| Scenario simulation | **Done** | `simulate_budget` tool — re-runs deterministic ranking + finance under a changed budget ("what if my budget drops 30%?"); the server computes the delta, never the model |

### Tier 2 — Ambitious (bonus)

| Capability | Status | Notes |
|---|---|---|
| Marketplace / supplier comparison | **Done (FutureMakers round), with demo dealers** | `find_inputs` ranks dealers by price, distance, stock and trust, deterministically; see "New in the FutureMakers round" |
| Market price intelligence (sell-now/wait) | **Done** | `market_price` tool (`backend/tools/market_price.py`) over `agristats.db :: fact_prices` — 83,097 BBS Yearbook monthly wholesale rows, 2007-08 to 2025. Returns the 12-month historical price curve in Tk/kg plus a deterministic sell-now / consider-storing reading. Three constraints are structural, not disclaimers: it is labelled `basis: historical_pattern` and `not_a_forecast` (the same discipline `weather.py` applies to climatology); it is labelled `is_farm_gate: false`, because these are wholesale prices and revenue may only come from the cited farm-gate table in `data/prices.md`; and `storage_cost_bdt` is null because no source in this project prices storage or spoilage, so a "store" reading is an upside **before** costs. See "Why retail prices cannot become revenue" below |
| Plant disease detection from images | **Done, with a stated limitation** | `POST /api/diagnose/image` runs `linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification` (MobileNetV2 fine-tuned on PlantVillage, 38 classes) locally on CPU — no image leaves the machine. Camera button in the composer. **Two limitations ship inside every response, not as a footnote:** (1) of our five crops, PlantVillage's label set covers **potato only** — rice, mustard and lentil are absent from it entirely, and a closed-set classifier will still return a confident label for them, so every result reports `is_supported_crop` and an out-of-scope warning in Bangla when the predicted crop is not one we advise on; (2) PlantVillage is **laboratory imagery** (single detached leaves, uniform background), so accuracy on a real field photo is materially lower than the headline benchmark — the result says so and tells the farmer to treat it as a second opinion. Dependencies are **optional** (`backend/requirements-vision.txt`, ~200 MB of CPU torch): without them the backend still starts, `GET /api/diagnose/status` reports `available: false`, and the UI hides the camera button rather than offering an upload that will fail |
| bdapps Payment Gateway Integration | **Done, simulator mode.** The payments module (`backend/payments/`: `client.py`, `msisdn.py`, `service.py`, `simulator.py`) is now wired end to end: a `কেনাকাটা` tab appears when a basket exists, and runs quote -> confirmation -> charge -> Bangla SMS receipt through `POST /api/checkout/quote` and `POST /api/checkout`. The confirmation gate is enforced **server-side** — a charge without a registered, unexpired quote is refused with 409, so it is a guarantee rather than a UI convention. The mode badge reads whatever `GET /api/checkout/mode` reports off the client object actually in use, and says `unknown` if the server did not answer, because guessing "simulator" in the wrong direction is exactly the failure CLAUDE.md rule 13 exists to prevent. **No real money moves.** The basket is derived from the agent's own cited input-cost lines, and only from purchasable ones — BBS's boro/aman/potato cost rows are a single aggregate figure in `ha`, so those crops get no checkout rather than a fabricated product list. |
| Bengali interaction and voice | **Done** | Bangla by default throughout. A settings panel (`SettingsModal.jsx`) switches the UI **and the agent's replies** between Bangla and English (the choice is sent on `/api/chat` and injected as a system note), and sets text size (small/medium/large) for sunlight and low vision. **Dictation** records with `MediaRecorder` and transcribes server-side via `POST /api/transcribe` using OpenAI `gpt-4o-transcribe`. **Read-aloud** stays browser-native (`speechSynthesis`) with a chooseable voice and speed. See the voice note below for why dictation is not browser-native |

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
| Input costs (seed, fertiliser, labour) | `data/prices.md` | **Real for boro/aman/potato** (BBS aggregate cost-of-cultivation, complete, cited). **Mustard/lentil are fertiliser-only** (Urea/TSP/MoP from BARC's FRG-2024 and BARI's Krishi Projukti Hatboi, priced against a 2023-04-11 government notice) — a stated **minimum bound**, not a complete cost, because no citable seed price was found for those two crops. `crop_scorer` excludes both from the Profit component entirely rather than scoring them against an incomplete floor |
| Historic agricultural-input statistics (seed supply, fertilizer market, pesticide use, wages, irrigation) | `agristats.db`, BBS Chapter 7 | **Real, cited.** Exposed read-only via the `agri_inputs` tool; explicitly historic/aggregate reference data, never used to cost a plan |
| Agronomy knowledge base — retrieval corpus | AIS e-Krishi, AIS কৃষিকথা, BAMIS, BRRI — curated into `data/kb/corpus.json`, served by `backend/kb/retrieval.py` | **Real, cited.** 52 hand-written passages (boro_rice 12, aman_rice 10, potato 11, mustard 8, lentil 11), retrieved by the `rag_query` tool with a stdlib IDF-weighted keyword score — not a vector database, see the RAG disclosure below |
| Agronomy knowledge base — scorer facts | AIS e-Krishi, AIS কৃষিকথা, BAMIS, BRRI — curated into `backend/kb/crop_facts.py` | **Real, cited, separate mechanism.** A small hand-written dict (season/soil/water/climate bands per crop) that `crop_scorer.py` reads directly — no retrieval step, no ranking; see "Two knowledge sources" below |
| Retail market prices | TCB daily bulletin, Dhaka, 24-07-2026 | **Real, cited, dated** — and deliberately *unreachable* from any revenue calculation. See below |
| Crop calendars and soil/water suitability for the five supported crops | AIS e-Krishi, BAMIS and BRRI guidance | **Curated and cited.** The scorer deterministically screens season, soil, water and district climatology; a failed source lookup is disclosed in its degraded list |
| bdapps payments | Simulator (`backend/payments/simulator.py`), matching the documented bdapps CaaS request/response shapes | **Real code, simulated transactions.** Labelled `mode: simulator` in code, API and UI. No real charge occurs |
| Checkout basket contents | Derived from `finance_projection`'s cited input-cost lines | **Real, cited.** Not a product catalog — there is no supplier catalog in this project |
| Historic monthly wholesale prices (sell/store timing) | `agristats.db :: fact_prices`, BBS Yearbook, 83,097 rows, 2007-08 to 2025 | **Real, cited.** Used only for the seasonal *pattern*; flagged `not_a_forecast` and `is_farm_gate: false` so it can never become revenue |
| Pest and disease risk rules | Stage windows from the same cited sources as `season_plan`; treatment text from the 14 cited pest/disease KB passages; triggers from live Open-Meteo forecast + humidity | **Real, cited.** The risk *level* is computed, not retrieved — the formula is returned with every risk |
| **Pesticide / fungicide prices** | — | **MISSING from public sources, and reported as missing.** `pest_risk` still returns `treatment_cost_bdt: null`. The only spray price the agent may quote is a dealer's dated marketplace listing (`find_inputs`, provenance `source_type: listing`). The seeded demo listings' spray prices are **invented demo values**, labelled `[DEMO]` and "ডেমো দোকান" |
| **Seed prices** | — | **MOCK / ABSENT.** No centralised Bangladeshi seed price source was found. Seed cost is therefore **not included** in any projection: `agristats.db`'s `fact_seed` carries national supply/demand tonnage only (no price column), and the mustard/lentil cost rows are explicitly fertiliser-only. Every affected figure is labelled a minimum bound rather than silently completed with a guessed seed price |
| Leaf-photo disease classification | `linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification` (PlantVillage, 38 classes), CPU, local | **Real model, narrow scope.** Covers potato among our five crops; rice/mustard/lentil are not in its label set and are reported as out-of-scope rather than diagnosed. Lab-trained, so field-photo accuracy is lower — stated in every response |
| Bangla speech-to-text | OpenAI `gpt-4o-transcribe`, live | **Real.** The farmer's recording is sent to OpenAI — the same provider already receiving every typed message, so no new boundary is crossed, but it is stated here rather than buried |
| Crop profit figures | `data/prices.md` via `backend/finance/` | **Real for boro/aman/potato** (complete BBS cost). **Mustard and lentil are an UPPER BOUND, not a profit** — their cost rows are fertiliser-only, so revenue minus a subset of costs. `crop_scorer` returns `profit_basis` marking them non-comparable and the agent is required to print "সর্বোচ্চ সম্ভাব্য লাভ — সব খরচ ধরা হয়নি" on the same line as the number |
| **Marketplace dealers and buyers** | `python -m backend.market.seed_demo` | **DEMO.** 5 dealers and 3 buyers, every row `is_demo`, named ডেমো, labelled in the UI, SMS and agent narration. Their phone numbers are made up and a live SMS gateway never texts them. Demo fertiliser listings use the cited government-notified price (Urea/TSP ৳27/kg, MoP ৳20/kg; 2023-04-11 notice in `data/prices.md`); spray prices are invented. Real dealers and buyers self-register at `#/dealer` / `#/buyer` and show as "যাচাই হয়নি" until verified |
| Produce price guide | `data/prices.md` farm-gate row + `market_price` (BBS wholesale pattern) | **Real, cited.** Labelled a historical pattern, not a forecast, and wholesale, not farm-gate |
| Commission and platform-fee rates | `MARKET_COMMISSION_PCT` (5), `PRODUCE_FEE_PCT` (2) | **Pilot parameters, not data.** The dealer pays the commission; the buyer pays the fee |
| SMS, USSD and voice in the emulator | `#/phone` | **SIMULATED transport, real flows.** The emulator calls the same backend flows a gateway would; `SMS_PROVIDER=simulator` sends nothing |
| Bangla speech on the voice line | Sarvam / OpenAI / Azure | **Real APIs, quality not yet verified** for this line |

### Voice disclosure — why dictation is not browser-native

The microphone first used the browser's own Web Speech API: no backend, no key,
on-device. It does not work where it matters. **Brave keeps the
`webkitSpeechRecognition` constructor but blocks the relay it depends on**, so
feature detection says yes, the button appears, `start()` succeeds, and the very
next event is a `network` error — the mic lights up for a second and dies with
nothing to show. Firefox has never shipped the API at all. Bangla dictation was a
browser-and-vendor lottery.

So recognition moved server-side. The browser records with `MediaRecorder`
(universally supported) and posts the clip to `POST /api/transcribe`.

**The model choice is not incidental.** Verified against synthesized Bangla speech
on 2026-07-25:

| model | "আমার দিনাজপুরে এক বিঘা জমি আছে, এই রবি মৌসুমে কোন ফসল চাষ করব?" |
|---|---|
| `whisper-1` | `अमर दिनजपूरे एक बिगा जमी अछे` — **Devanagari.** It transcribed Bangla into Hindi script, and rejects `language="bn"` outright |
| `gpt-4o-mini-transcribe` | `আমার দিনেচপুরে … রবি মাক্সুমে` — right script, mangles the district name and "মৌসুম" |
| **`gpt-4o-transcribe`** | `আমার দিনাজপুরে এক বিঘা জমি আছে। এই রবি মৌসুমে কোন ফসল চাষ করবো?` — **exact** |

The district name is the most load-bearing word a farmer says: it picks the
coordinates, the yield history and the weather. `gpt-4o-transcribe` is the model
in use for that reason.

Trade-off, stated plainly: dictation now needs the network and the backend, where
the old path ran on-device. Read-aloud is unaffected and remains fully local.

### RAG disclosure — what "retrieval" means here

`rag_query` (`backend/kb/retrieval.py`) is deliberately **not** a vector
database and has **no embeddings**. It is a stdlib-only, deterministic
keyword ranker over `data/kb/corpus.json`'s 52 passages:

1. Each passage is tokenized into a bag of words (its text + crop name + title
   + topic tag, so a bare crop-name query still matches).
2. Inverse document frequency is computed once over the whole corpus — words
   that appear in almost every passage (the crop name itself, "kg", "ha")
   get down-weighted; distinguishing words ("irrigation", "blight",
   "tricyclazole") get up-weighted.
3. A query scores against a passage as a TF-IDF dot product, normalized by
   `sqrt(passage length)` so a long passage can't out-rank a short precise one
   purely by repeating common words.

This is a real, working retrieval layer — the agent is genuinely grounded in
what it returns, and every result carries `source_id`/`source_title`/`locator`
— but call it what it is: keyword overlap with IDF weighting, not semantic
search. It was a deliberate scope choice (see LOG3.md: "Chroma/embeddings for
the KB — no time, new dependency, and it would risk the demo for a corpus this
small; kept the deterministic ranker instead").

### Two knowledge sources — not one

The old draft of this README described "the RAG system" as a single thing.
It's actually two separate, real mechanisms that feed different parts of the
agent, and conflating them undersells both:

1. **`rag_query` over `data/kb/corpus.json`** (52 passages) — retrieved live,
   ranked per-query, used to ground the agent's *narration* (fertilizer doses,
   irrigation timing, pest/disease notes, sowing windows).
2. **`backend/kb/crop_facts.py`** — a small, hand-curated, statically-imported
   dict (season/soil/water/climate bands for each of the 5 crops), read
   *directly* by `crop_scorer.py` at scoring time. No retrieval, no ranking —
   it's structured data the deterministic scorer consumes like any other
   input. Sourced from the same named documents (AIS e-Krishi, AIS কৃষিকথা,
   BAMIS, BRRI), just not chunked into a searchable corpus.

Both are real and cited. Neither is a vector index.

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

### What the trace panel actually shows

The old draft of this README claimed clicking a graph node opens a raw
params/result inspector, and that a chronological raw log sits nested
underneath the graph. **That was true of an earlier build and is not what
ships.** `App.jsx` renders exactly one trace surface, `GraphPanel.jsx`; two
components that used to provide node-level and raw-JSON drilldown
(`NodeInspector.jsx`, `TracePanel.jsx`) were deleted in LOG4 (they had been
unreachable from the UI since
`LOG2.md`, "the previous graph was too dense and English-heavy for the
requested product surface").

What the shipped graph panel actually does: every tool call still fires
`tool_call`/`tool_result` SSE events (nothing about the trace's completeness
changed), and `GraphPanel.jsx` renders them live as a farm-centered graph with
Bangla tool labels, pan/zoom (drag + wheel), a freeze/resume toggle so a judge
can stop it mid-stream and read it, entrance animation on new nodes/edges
only, and a live "চলছে: <tool>" status line while a call is in flight. What it
does **not** do: expose a per-node raw-JSON drilldown, or nest a raw
chronological log. If you need the raw params/result for a specific call, it
is still fully present in the underlying trace array the frontend receives
over SSE — it is just not surfaced as a separate inspector in this build.

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

## Setup

```bash
python -m venv backend/.venv
backend/.venv/Scripts/python -m pip install -r backend/requirements.txt
cd frontend && npm ci && cd ..
```

`backend/requirements.txt` pulls in `backend/api/requirements-api.txt` via
`-r`, so this one install covers both the agent/tools/kb code and the FastAPI
layer.

### Two env files — copy and fill in BOTH

```bash
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
| `OPENAI_MODEL` | — | defaults to `gpt-4o` (`backend/agent/config.py` `DEFAULT_MODEL`) if unset. **Do not switch to `gpt-4o-mini`**: live-verified on 2026-07-25 to skip tool calls entirely under this agent's 14-tool loop + long system prompt — it answers from model recall instead, with zero `tool_call` SSE events, no weather, no crop_scorer, no rag_query, empty trace panel |
| `AGRISENSE_TEMPERATURE` | — | defaults to `0.0` — pinned deliberately (see `backend/agent/config.py`'s `DEFAULT_TEMPERATURE`). At 0.2 it was live-verified flaky: gpt-4o sometimes called `ask_farmer` correctly, sometimes answered the same missing-field question as plain chat text instead (`ask_farmer` fired only ~7/9 times). Leave this unset or `0.0` |

Fill in the repo-root `.env` (see `.env.example`):

| Variable | Required for | Notes |
|---|---|---|
| `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY` | the browser sign-in screen and crop sidebar | project's Supabase instance; browser-exposed anon key, RLS-protected |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` | the backend's `/api/crops` routes, which proxy the caller's own Supabase token | same project, server-side copy; read by `backend/api/config.py`, which loads the root `.env` |
| `SUPABASE_DB_PASSWORD` | the `supabase` CLI only (`db push`/`link`) | not read by application code |
| `VITE_DEMO_GUEST` | optional | `true` skips the Supabase login screen entirely for demo purposes (see below); the same effect is available per-session via `?guest=1` in the URL, or by clicking "অতিথি হিসেবে দেখুন" under the login form |

### Run it

```bash
backend/.venv/Scripts/python -m uvicorn backend.api.main:app --reload --port 8000
```

**Run this from the repo root, not from inside `backend/`.** `backend.api.main:app`
is a dotted module path relative to the repo root; running the same command from
inside `backend/` fails with `ModuleNotFoundError` because Python can no longer
resolve the `backend` package.

```bash
cd frontend && npm run dev        # http://localhost:5173, proxies /api to :8000
```

The Vite dev server proxies `/api` to `http://127.0.0.1:8000` (see
`frontend/vite.config.js`) so the browser only ever talks to one origin —
confirm the backend is actually listening on port 8000 (the `API_PORT`
default in `backend/api/config.py`) or the proxy has nothing to forward to.

### Tests

```bash
backend/.venv/Scripts/python.exe -m pytest tests backend/tests -q
```

**562 passed** — verified on 2026-09-27 against this checkout (LOG4).
Coverage spans the finance engine, `units.py`, the trace redactor, crop
scoring, retrieval, season-plan generation and persistence, plan-conflict
checking, the care scheduler, scenario simulation, and agri-input lookups —
the places CLAUDE.md rule 12 asks for tests, not UI coverage theater.

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

### Phone channels and marketplaces

```bash
python -m backend.market.seed_demo      # demo dealers + buyers (once; --reset removes them)
```

Then open `http://localhost:5173/#/phone` (button-phone emulator), `#/monitor`
(live phone conversations) and `#/market`. With the default `SMS_PROVIDER=simulator`
nothing leaves the machine and the emulator's inbox shows every SMS.

**Real SMS through an Android phone** (pilot):

1. Install **SMS Gateway for Android** (SMSGate) on the phone, enable *Local Server*,
   note the address, username and password it shows.
2. In `.env`: `SMS_PROVIDER=smsgate`, `SMSGATE_URL=http://<phone-ip>:8080`,
   `SMSGATE_USER`, `SMSGATE_PASSWORD`, and a long random `CHANNEL_ID_SALT`.
3. Register a webhook on the phone for `sms:received` (and `sms:delivered`) pointing at
   `http://<backend>/api/channels/sms/smsgate`; set the app's signing key as
   `SMSGATE_SIGNING_KEY` so unsigned calls are refused.
4. Missed calls: plug the phone in with USB debugging on, set `BRIDGE_TOKEN` on both
   sides, and run `python -m backend.channels.bridge.adb --backend http://<backend>`.

A personal SIM is for a pilot only; production runs on the operator's IVR, USSD short
code and bulk-SMS channels. `ALERT_SMS_ENABLED=true` turns on the proactive rain-alert
texts.

### Payments

Ships in **simulator mode** — see the Tier 2 table above. The `কেনাকাটা` tab appears when
the finance projection has purchasable input lines, and runs quote → confirmation → charge
→ Bangla SMS receipt through `POST /api/checkout/quote` and `POST /api/checkout`. The
confirmation gate is enforced server-side (409 without a matching, unexpired quote).
No real money moves; the mode badge reads `GET /api/checkout/mode`.

---

## Architecture

```
backend/
  agent/      the loop, prompts, tool specs, LLM client (OpenAI backend)
  tools/      geocode · weather · cropdb · crop_scorer · finance · season_plan ·
              plan_conflicts · care_scheduler · scenario · agri_inputs ·
              ask_farmer · remember_farm
  kb/         holt.py (Holt yield projections) · retrieval.py (rag_query's 52-passage
              corpus) · crop_facts.py (curated agronomic facts the scorer reads directly)
  finance/    engine.py (Decimal, the only place money math happens) + catalog.py
  payments/   bdapps client + simulator twin + server-enforced confirmation gate (simulator mode)
  channels/   phone identity, adapter over run_turn, SMS providers + text rules, USSD menus,
              voice line, ADB missed-call bridge, proactive alert SMS
  market/     input + produce marketplaces: catalog, ranking, orders, listings/offers,
              SMS commands, USSD sub-menus, demo seed
  memory/     SQLite WAL: conversation history and farm profiles
  api/        FastAPI routes, SSE transport, redacting trace emitter, Supabase-proxying crop index
  units.py    bigha/katha/maund conversions
frontend/     Vite + React, one responsive page, manifest-only PWA
data/         crop.db (generated in-event) · prices.md (cited price tables) ·
              kb/corpus.json (52 cited retrieval passages)
```

**Agent tools** (registered in `backend/agent/tools_spec.py`, dispatched by name; every
call emits a traced `tool_call`/`tool_result` pair — 17 tools total; the table
lists the original core, plus `pest_risk`, `market_price` and `find_inputs`):

| Tool | Does |
|---|---|
| `ask_farmer` | Asks the farmer one missing intake field at a time, with the right input widget |
| `geocode` | Resolves a place/district name to coordinates (Open-Meteo geocoder + 64-district fallback) |
| `get_forecast` | 16-day weather forecast for coordinates |
| `get_climatology` | Historical monthly normals for coordinates |
| `rag_query` | Source-cited agronomy passages from the 52-passage curated corpus |
| `cropdb_sql` | District yield history, Holt yield projection, and yield track record |
| `agri_inputs` | Historic BBS Chapter 7 seed/fertilizer/pesticide/wage/irrigation reference facts |
| `crop_scorer` | Deterministic ranking of the 5 supported crops for a farm profile |
| `finance_projection` | Costed 3-scenario financial projection for one crop |
| `season_plan` | Dated, source-cited task calendar for a confirmed crop and date |
| `check_plan_conflicts` | Compares a saved plan's weather-dependent tasks against the live forecast |
| `care_schedule` | Fertilizer/irrigation tasks due from a saved plan, with forecast context |
| `simulate_budget` | Re-runs ranking + finance under a changed budget |
| `remember_farm` | Persists the confirmed farm profile for future turns/sessions |
| `pest_risk` | Deterministic crop × growth-stage × forecast pest/disease risk, cited treatments |
| `market_price` | Historical wholesale price pattern + sell-now / consider-storing reading |
| `find_inputs` | Ranked nearby dealer offers for one input, with dated listing provenance |

The agent streams Server-Sent Events; every tool call emits `tool_call` and
`tool_result` into a live trace, rendered as a Bangla-labeled provenance graph
(`GraphPanel.jsx` — see "What the trace panel actually shows" above for exactly
what it exposes). Redaction happens in the event constructors *and* again at
the serializer: passwords, app ids, keys and tokens become `***`; phone
numbers keep their last three digits so a human can still confirm which SIM
was involved — because a leaked credential in a judge-facing panel is not a
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
