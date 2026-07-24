# PRD v2 — AgriSense AI (TeamFixeth_AgriSense)

IUT 12th ICT Fest — Bdapps Agentic AI Hackathon, Final Round. 24h: 24 Jul 09:00 → 25 Jul 09:00. This is the single product spec. PLAN.md = execution, NOTES.md = caveats, CLAUDE.md = agent rules.

## 1. One-line product

A Bangla-first PWA where a smallholder farmer talks to an autonomous agent that produces a costed, weather-grounded season plan for their specific farm — and every number in that plan carries provenance a judge can inspect.

## 2. Target users

Primary: Bangladeshi smallholder farmer. Low literacy assumed, Bangla, cheap Android phone, thinks in bigha/katha, BDT, district names.
Secondary: the judge. Must verify in <4 min: the agent is real (trace), the math is real (change input → outputs change), the data is real (provenance on every number).

## 3. The five judged agentic behaviors — where each shows

| Behavior | Where |
|---|---|
| Tool use | Open-Meteo forecast + climatology, geocoder, Chroma RAG, crop.db SQL, crop scorer, finance engine, bdapps CaaS. Real values, all traced. |
| Multi-step planning | "Plan my season" → geocode → weather → RAG → scorer → calendar → finance, chained visibly. |
| Missing info + recovery | Intake gap detection with targeted Bangla follow-ups. Plus scripted recoveries: geocode ambiguity → confirm; budget too low → reduced-area/cheaper-crop replan; weather API down → retry then labeled cached data; missing KB evidence → admit insufficiency, never invent. Minimum two recoveries appear in the demo. |
| Memory | SQLite farm profile + conversations + plans. Survives restart. Demo opens with a remembered farm. |
| Explainability | Every recommendation names inputs + provenance: "৪৫ কেজি ইউরিয়া — soil=loam (আপনি বলেছেন), stage=vegetative (calendar), rain=0mm/5d (পূর্বাভাস, Open-Meteo 14:02)." |

## 4. Crop recommendation algorithm (deterministic, inspectable)

`backend/tools/crop_scorer.py` (owner A). Pure function, unit-tested. The LLM narrates scorer output in Bangla; the LLM never ranks crops itself.

### Stage 1 — hard exclusions (each logged with farmer-readable reason)

| Filter | Rule | Source |
|---|---|---|
| Season | sowing window ∩ target season = ∅ → exclude | KB crop calendar |
| Soil | farmer soil not in crop's allowed list → exclude | KB |
| Water | crop water class > farm water class (rainfed < tubewell < canal/irrigated) → exclude | KB + intake |
| Budget | min_cost_per_ha × area > budget → exclude, agent offers reduced-area replan (recovery demo moment) | finance engine |

### Stage 2 — suitability score 0–100 for survivors

| Component | Max | Computation | Source |
|---|---|---|---|
| Agronomic fit | 25 | soil primary=25 / secondary=15 / marginal=8 | KB |
| Profit | 25 | net profit/ha (base scenario), min-max normalized within candidate set | finance engine (Holt base yield) |
| Climate fit | 20 | linear penalty for climatology rain/temp outside crop optimal range | Open-Meteo climatology + KB |
| District track record | 20 | percentile of this crop's district yield vs same crop across districts; ±2 for damped-Holt trend direction | crop.db |
| Stability | 10 | 10 × (1 − CV of district yields 2016–2024), floor 0 | crop.db |

Output per candidate: composite + every component (value + provenance) + water need (KB) + risk level (yield-CV terciles → low/med/high) + est. profit (finance engine). Judge sees exactly why #1 beat #2.

### Role of yield data — explicitly NOT "recommend the highest-yield crop"

Raw yield is incomparable across crops and ignores price, cost, constraints, risk. Usage: district history → relative track record (20/100); damped-Holt point estimate → base yield into finance, band = ± residual std dev, labeled "projection from BBS 2016–2024, not a guarantee"; yield CV → risk. Disclosed limitation: district yield is a district-wide average; no fake per-farm adjustment — the scenario band covers uncertainty.

## 5. Provenance (enforced by schema, not prompt)

Every number reaching the UI carries a Provenance object:

```
value, unit, source_type: kb|api|dataset|static_table|computed,
source_id, source_title, locator (page/table/url/query), retrieved_at,
formula (human-readable, if computed), confidence: high|medium|low
```

KB chunks store source URL, publication date, section/table id at ingest; metadata flows into Provenance at retrieval. Rule: a number without Provenance must not render. B shows provenance on tap/hover.

## 6. Scope tiers (nothing cut — stretch items GATED)

Gate rule: items marked [GATED] may not be started until the `tier0-stable` tag exists (target H15) AND main is green. Until then they are proposals in the log, not code. This is how we keep full ambition without losing the 15 scope points.

### Tier 0 — required (done H12, hardened H15)

1. **Conversational intake (Bangla)** — location, farm size, soil, water, budget, season. Local units accepted, normalized via units.py.
2. **Live weather grounding** — `get_forecast` (Open-Meteo 16-day, real, actionable) + `get_climatology` (Open-Meteo historical normals, real, planning assumption). Every weather claim labeled `source_type: forecast|climatology`. Bangla wording reflects it: forecast → "পূর্বাভাস অনুযায়ী"; climatology → "গত বছরের গড় অনুযায়ী, ভিন্ন হতে পারে". Climatology presented as predicted future rainfall = bug. No invented weather, ever.
3. **Crop recommendation** — §4 scorer, ≥3 ranked candidates.
4. **Season plan** — dated calendar land prep → harvest, tasks flagged `depends_on_weather`, each task with source.
5. **Financial projection** — itemized costs; yield = damped-Holt base; three scenarios (conservative = base−band & price−10%, base, optimistic = base+band & price+10%); revenue, net profit, ROI, break-even yield AND break-even price. Selling prices from BBS Yearbook Ch.10 (harvest-time + wholesale 2023–24) and labor costs from Yearbook Ch.7.5 wages, hand-curated in-event into `data/prices.md`: every row cited with source + table/page + date — no placeholders. Other input prices (seed, fertilizer) cited from BARC/DAE/market sources with URL + date, or the row is deleted. Computed only in `backend/finance/` pure functions with consistency unit tests. LLM never does arithmetic.
6. **Explained reasoning** — §3 table + §5 provenance.
7. **Knowledge base with RAG** — curated markdown from BARC/DAE guides + FAO-56 Kc table, written during the event from public sources; Chroma index generated in-event by `ingest.py`. Plus structured crop.db (see §8 data rules) via SQL tool. RAG queries formulated in English (cross-lingual fix), conversation stays Bangla.
8. **Visible agent trace** — live panel streaming every tool call: name, params, raw results, timestamp. English. Redacted (§9). Any number in the plan traceable to an entry.

### Tier 1 (H15–H18, priority order)

1. Persistent memory across sessions (from SQLite design — demo it).
2. Scenario simulation — "rainfall −30%?" / "budget −40%?" → scorer + finance re-run, changed numbers, deltas shown.
3. Fertilizer & irrigation scheduler — doses by growth stage (BARC + FAO-56 Kc), organic alternatives, cost.
4. Proactive weather-triggered advice — minimal credible version: persisted plan tasks + `check_plan_conflicts` tool scanning the 16-day forecast against upcoming weather-dependent tasks; runs on session open and via "আমার প্ল্যান চেক করুন" button; conflicts saved as alert events, shown as banner; agent proposes revision, farmer confirms, plan updates. Visibly revisits and revises an existing plan. No cron/push needed.
5. [GATED] Pest and disease risk from crop × stage × weather (KB-driven), with prevention/treatment options and cost.

### Tier 2 (bonus, gated except payments)

1. **bdapps CaaS checkout** (10 pts, treated as near-required, NOT gated): portal blocked pre-event (needs receiving URLs), so simulator is the primary path, built H3–H6 with exact request/response shapes from BDAPPS-API-REFERENCE.md including error paths (E1326 insufficient balance). Flow: confirmation step ("৳X কাটা হবে — নিশ্চিত?") → balance query → direct debit → Bengali SMS receipt (encoding 16). All-outbound; no public callback URL. `mode: live|simulator` labeled in UI + README. If portal unblocks before H15: whitelist venue IP, test real ৳2 debit on Robi SIM at H15–18; on-stage failure → one rehearsed click back to simulator.
2. AEZ soil cross-check (NOT gated — cheap, offline): farmer-stated soil compared against BBS Yearbook Ch.1 AEZ district soil profile; disagreement → agent asks farmer to confirm (recovery moment #3). Replaces the earlier SoilGrids idea — local official data beats a live foreign API here. [GATED] SoilGrids stays available only as an extra if truly idle.
3. Bengali-first interaction — core already; claim the accessibility bonus in README.
4. [GATED] Market price intelligence / sell-store-wait.
5. [GATED] PlantVillage leaf-photo disease detection (pretrained HF model only, no training).
6. [GATED] Voice input (Bangla STT).

### Non-goals regardless

Marketplace/escrow, USSD/SMS inbound flows, satellite imagery, model training, auth beyond farm profiles, visual polish beyond one clean responsive page.

## 7. Product shape

- **PWA**: manifest-based installable, mobile-first. Service worker [GATED] and prod-build-only if attempted (NOTES #7).
- **One responsive page**: chat primary; Plan / Finance / Trace as tabs (desktop: trace side panel). Noto Sans Bengali. Western numerals inside tables and computed values; Bangla text around them. Trace panel English (for judges).
- Bangla-first: agent mirrors user language, defaults Bangla.

## 8. Data rules (competition-safe) + honesty ledger

All application code — including the agribase parser, damped-Holt fitting, Chroma ingest — is written and run DURING the event. Derived artifacts (crop.db, Chroma index) are generated in-event with timestamps stored in a meta table. The raw National Yearbook extracts are public data, hosted publicly with the link in README. Pre-cached third-party artifacts that are fine: embedding model, pip wheels, npm packages.

| Data | Source | Real/Mock |
|---|---|---|
| Weather forecast + climatology | Open-Meteo API, live | Real |
| District yield/area 2016–2024 + Holt projections | BBS National Yearbook (public raw data); parsed + fitted in-event | Real |
| Fertilizer doses, crop calendars | BARC / DAE public guides, curated in-event | Real (curated) |
| Crop water coefficients | FAO-56 Kc table | Real |
| Input + selling prices | BBS Yearbook 2024 Ch.10 (harvest-time + wholesale 2023–24), hand-curated in-event into data/prices.md, each row table+page cited | Real (official, dated) |
| Labor wages | BBS Yearbook Ch.7.5 monthly agricultural wages 2023–24, curated in-event | Real |
| District soil profile | BBS Yearbook Ch.1 AEZ tables (district → zone → texture/pH/fertility), curated in-event | Real |
| Official crop calendar | BBS Yearbook Ch.1.8, curated in-event | Real |
| District crop damage (risk refinement, optional) | BBS Yearbook Ch.4 | Real if included |
| bdapps | Simulator matching documented shapes; live on Robi SIM if portal unblocks | Disclosed either way |

## 9. Trace redaction (security)

The SSE trace emitter redacts before sending: `password`, `applicationId` values, anything matching /key|token|secret/i → `***`; phone/subscriberId → last 3 digits only. Applies to params and raw results. Unit-tested with a fake bdapps payload. Judges see judge-relevant values, never credentials.

## 10. Stack (final)

| Layer | Choice | Why |
|---|---|---|
| Agent loop | Custom loop, Claude API (Sonnet), native tool use | Own the loop → trivial trace emission |
| LLM config | Single client, model switchable by env var only (no abstraction layer) | Scope discipline; [GATED] fallback provider |
| Backend | Python FastAPI + SSE | Tools are Python functions |
| RAG | Chroma embedded/local, index built in-event | Zero infra, survives wifi death |
| Embeddings | sentence-transformers, model pre-cached | Offline-safe; English queries |
| Structured data | crop.db (SQLite) generated in-event, SQL tool | Real district yields + Holt projections |
| Memory | SQLite, WAL mode | Tier 1 persistence nearly free |
| Frontend | Vite + React, manifest PWA | SSE trace panel, mobile-first |
| Weather | Open-Meteo forecast + climate endpoints | Free, keyless, real |
| Payments | bdapps CaaS via httpx; simulator twin | Outbound-only; portal-independent |

## 11. Success criteria → 100 pts

Agentic 20: five behaviors + two recoveries in one run. Accuracy 20: finance tests pass, live input change recomputes, yields match crop.db. Scope 15: Tier 0 end-to-end, stable, rehearsed. KB 12: trace shows retrieval feeding advice, sources in README. bdapps 10: full checkout flow, labeled mode. Explainability 10: provenance on every number. Technical 8: pinned deps, tests on finance/units/scorer/redactor. Innovation 5: scenario sim + proactive alerts + Bangla PWA + any gated wins.
