# What is real and what is not

Moved from the README on 2026-11-10 (unchanged except paths). This is the honesty ledger: every data source, whether it is real, simulated or missing, and the disclosures judges and partners should read.

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
| SMS, USSD and voice in the emulator | `/api/channels/emulator/*` (browser page removed) | **SIMULATED transport, real flows.** The emulator calls the same backend flows a gateway would; `SMS_PROVIDER=simulator` sends nothing |
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
search. It was a deliberate scope choice (see docs/logs/LOG3.md: "Chroma/embeddings for
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
`docs/logs/LOG2.md`, "the previous graph was too dense and English-heavy for the
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
