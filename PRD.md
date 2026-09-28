# PRD v4 addendum — GP FutureMakers 2026 (September 2026)

**This addendum governs the FutureMakers round. Sections 1–15 below are the July
hackathon PRD (v3.1), kept as history; where they conflict, this addendum wins.**

**Track:** Digital Inclusion & Education. **Round 1 deliverable:** idea/pitch (concept
note, LOG4 [00:40]); the build backs the pitch with working flows.

**Users, widened.** Primary: a Bangladeshi smallholder on **any phone** — including the
~3 in 4 rural mobile users without a smartphone (GSMA 2024). Also: input dealers and
produce buyers (marketplace partners).

**In scope (reverses §8 "Non-goals"):**
1. Channels: SMS (two-way), missed-call opt-in, USSD menus, a voice line, proactive
   alert SMS — one agent, one farm memory across all of them.
2. Input marketplace (dealer-paid commission) and produce marketplace (buyer-paid fee).
3. Rename (working name AgriSense; one constant).

**Still out of scope:** escrow and payments held on behalf of others, logistics,
quality disputes, a real USSD short code or IVR number (operator provisioning), model
training.

**Rules that carry over unchanged:** the LLM never computes or ranks (now including
dealers); every number has provenance or does not render; missing data is said out
loud; simulated things are labelled. New: CLAUDE.md rules 15 (channels) and 16
(marketplace honesty).

**Success for this round:** a button phone can go from a missed call to a costed plan by
SMS, order an input, and sell a harvest, with every number traceable in `#/monitor`;
all of it runs in the emulator today and on a real SIM once the gateway phone and keys
are in place.

---

# PRD v3.1 — AgriSense AI (TeamFixeth_AgriSense)

IUT 12th ICT Fest — Bdapps Agentic AI Hackathon, Final Round. 24h: 24 Jul 09:00 → 25 Jul 09:00, demo 25 Jul 10:00. **This document replaces all earlier PRD versions.** PLAN.md stays authoritative for execution — the §13 amendments of PRD v3 have been folded into PLAN.md directly; do not re-apply. NOTES.md and CLAUDE.md unchanged and binding.

**Provenance of this document:** merge of PRD v2 + Instance A's PRD v3 (ADR-001), performed by the team. §15 decisions 1–3 are RATIFIED by this merge; decision 4 remains the H3 half-cap check. Restorations from v2 that v3 had dropped: named KB source documents, DAM current-price bulletin, pest checkpoints as Tier 0, Rajshahi as demo district.

---

## 1. One-line product

A Bangla-first PWA where a smallholder farmer talks to an autonomous agent that produces a costed, weather-grounded season plan for their specific farm — and every number in that plan carries provenance a judge can inspect.

## 2. Target users

Primary: Bangladeshi smallholder farmer. Low literacy assumed, Bangla, cheap Android phone, thinks in bigha/katha, BDT, district names.
Secondary: the judge. Must verify in <4 min: the agent is real (trace), the math is real (change input → outputs change), the data is real (provenance on every number).

## 3. The six-crop core

### 3.1 Selection criteria, in priority order

1. **Demo-season viability.** Demo is 25 July. A crop whose sowing window cannot intersect any season a farmer would plausibly plan on that date can never appear on stage (Kharif-1 crops — Aus, Jute, sown Mar–May — fail outright).
2. **Data density in the yearbook.** District-level area/yield series long enough for Holt + CV (≥6 points), Ch10 price rows, presence in the Ch1.8 crop calendar.
3. **Guidance availability.** BARC doses and BRRI/BARI/DAE calendar material exist and are curatable within the cap.
4. **Ranking-demo richness.** ≥3 surviving candidates in the demo season, with genuinely different profiles (water need, cost, risk, profit).

### 3.2 The set

| Crop | Season(s) | Why in |
|---|---|---|
| **Boro rice** | Rabi (Dec–Feb sow, Apr–Jun harvest) | Highest-volume crop in BD; densest data; irrigation-heavy → water-class filter demo. |
| **Wheat** | Rabi (Nov–Dec sow) | BBS major; low-water Rabi contrast to Boro. |
| **Potato** | Rabi (Nov–Dec plant) | BBS major; high-cost/high-revenue → makes budget-exclusion recovery realistic. |
| **Maize** | Rabi (Oct–Dec sow; kharif window exists) | Best-covered minor crop; strong profit narrative; solid BARC dose tables. |
| **Mustard** | Rabi (Oct–Nov sow) | Classic low-cost/low-water rotation crop; the "small budget" answer. |
| **Aman rice (T.Aman)** | Kharif-2 (Jul–Aug transplant) | The season literally open on demo day; covers "এখন কী লাগাব?" honestly. |

**Excluded, reasons stated up front (judges may ask):** Aus and Jute — best-in-book data, but sowing windows closed at demo time (criterion 1 dominates 2). Livestock/fisheries — out of problem scope.

### 3.3 Season logic for the demo

- **Demo district: Rajshahi** (High Ganges Floodplain AEZ-11 + Barind Tract — two distinct soil profiles inside one district, which makes the AEZ soil cross-check earn its place).
- The rehearsed demo farmer plans **Rabi** ("আগামী রবি মৌসুমের জন্য") — realistic in July (seed booking, input budgeting), 5 candidates enter → rich ranking.
- If a judge forces "plant now": season filter yields T.Aman (+ nothing else from the set). The agent says so honestly — "এই মুহূর্তে খরিপ-২ মৌসুমে এই তালিকা থেকে মূলত আমনই উপযুক্ত" — ranks what survives, and offers the Rabi plan as the forward look. Honest degradation is scored recovery behavior; padding the list with fabricated candidates is the failure mode.
- [GATED, cheap hedge] a 7th kharif-2 crop (brinjal or kharif maize) may be added post-`tier0-stable` for ≥3 live "now" candidates. Proposal only until the gate opens.

### 3.4 KB depth tiers (keeps the curation cap honest)

- **Tier-A depth** (Boro, Potato, Maize — likely demo picks): full calendar with stage dates, BARC dose schedule by growth stage, variety note, 2–3 pest/disease entries **+ pest CHECKPOINT dates (Tier 0 — they belong in the season calendar)**, water/Kc rows, fully itemized cost template.
- **Tier-B depth** (Wheat, Mustard, Aman): calendar incl. pest checkpoint dates, total dose + split timing, soil/water class, cost template.
- **Cap: 3.5h total** for A's KB + hand-curated yearbook tables. Half-cap check at ~1.75h. **Degradation order if slipping:** drop Mustard → Maize to Tier-B → 4 crops (Boro, Wheat, Potato, Aman). Log the drop; never silently thin the data.

Scorer, finance, and prices.md cover **all six** regardless of KB tier — those cost minutes per crop, not hours.

### 3.5 Named source documents (download in first 30 min of H3 while wifi is good)

BARC Fertilizer Recommendation Guide (FRG-2018 — dose tables by crop × soil fertility class, page-cited) · BRRI "আধুনিক ধানের চাষ" (Boro + Aman calendars, doses, pest checkpoints) · BARI Krishi Projukti Hatboi chapters (potato, maize, mustard, wheat) · SRDI Upazila Nirdeshika (Rajshahi — upazila-level soil) · FAO-56 Kc table · BAMIS (bamis.gov.bd) advisories · one current DAM (dam.gov.bd) daily price bulletin.

## 4. The five judged agentic behaviors — where each shows

| Behavior | Where |
|---|---|
| Tool use | Open-Meteo forecast + climatology, geocoder, Chroma RAG, crop.db SQL, crop scorer, finance engine, bdapps CaaS. Real values, all traced. |
| Multi-step planning | "Plan my season" → geocode → weather → RAG → scorer → calendar → finance, chained visibly. |
| Missing info + recovery | Gap detection with targeted Bangla follow-ups. Scripted recoveries: geocode ambiguity → confirm; budget too low → reduced-area/cheaper-crop replan; weather API down → retry then labeled cached data; missing KB evidence → admit insufficiency. ≥2 recoveries in the demo. |
| Memory | SQLite farm profile + conversations + plans. Survives restart. Demo opens with a remembered farm. |
| Explainability | Every recommendation names inputs + provenance: "৪৫ কেজি ইউরিয়া — soil=loam (আপনি বলেছেন), stage=vegetative (calendar), rain=0mm/5d (পূর্বাভাস, Open-Meteo 14:02)." |

## 5. crop.db — canonical schema

Owner: A. Generated in-event by `parse_agribase.py` + `holt.py`; timestamps in `meta`. DDL committed as `data/crop_schema.sql`, frozen with schemas.py at H1; same change protocol.

```sql
-- one row per crop×district×year observation; long/tidy
CREATE TABLE district_series (
  crop        TEXT NOT NULL,      -- canonical english name, matches KB + scorer keys
  district    TEXT NOT NULL,      -- canonical district name (64-list in units/geo module)
  year        INTEGER NOT NULL,   -- harvest year of the split year (2016–2024)
  season      TEXT,               -- aus|aman|boro|rabi|kharif1|kharif2|annual, where given
  area_ha     REAL,
  production_mt REAL,
  yield_t_ha  REAL,               -- as published; recompute-check in validation
  edition     TEXT NOT NULL,      -- yearbook edition, e.g. '2024'
  source_table TEXT NOT NULL,     -- e.g. '3.1 Boro'
  source_page INTEGER,            -- NULL only if genuinely unpaginated in extract
  extracted_at TEXT NOT NULL
);

CREATE TABLE holt_projections (
  crop TEXT NOT NULL, district TEXT NOT NULL,
  base_yield_t_ha REAL NOT NULL,      -- damped-Holt point estimate
  band_t_ha REAL NOT NULL,            -- residual std dev
  n_points INTEGER NOT NULL,          -- series length used
  trend TEXT NOT NULL,                -- up|flat|down (for scorer ±2)
  fitted_at TEXT NOT NULL
);

CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);  -- generated_at, parser_git_sha, source_urls
```

Rules:
1. **Every `district_series` row carries `edition + source_table + source_page`.** `cropdb_sql` results map these into Provenance (`source_type: dataset`, `locator: "{edition} {source_table} p.{source_page}"`).
2. `holt_projections` rows are `source_type: computed`; Provenance `formula` names method + series ("damped Holt over BBS {district} {crop} 2016–2024, n={n}").
3. Parser ingests whatever crops the extract cleanly yields (extra rows are free and honest), but the **scorer's candidate universe is exactly the six curated crops** — a crop without calendar, doses, cost template, and price row cannot be ranked without fabricating one. Stated in README; a feature, not a limitation.
4. Validation (in-parser, printed + meta): row counts per crop×edition, null rates, yield≈production/area cross-check, YoY jump flags >40%. Flag, never repair.

## 6. Crop recommendation algorithm (deterministic, inspectable; over the six-crop universe)

`backend/tools/crop_scorer.py` (owner A). Pure function, unit-tested. LLM narrates scorer output in Bangla; LLM never ranks crops itself.

### Stage 1 — hard exclusions (each logged with farmer-readable reason)

| Filter | Rule | Source |
|---|---|---|
| Season | sowing window ∩ target season = ∅ → exclude | KB crop calendar |
| Soil | farmer soil not in crop's allowed list → exclude | KB |
| Water | crop water class > farm water class (rainfed < canal < tubewell/irrigated) → exclude | KB + intake |
| Budget | min_cost_per_ha × area > budget → exclude, agent offers reduced-area replan (recovery moment) | finance engine |

### Stage 2 — suitability score 0–100 for survivors

| Component | Max | Computation | Source |
|---|---|---|---|
| Agronomic fit | 25 | soil primary=25 / secondary=15 / marginal=8 | KB |
| Profit | 25 | net profit/ha (base scenario), min-max normalized within candidate set | finance engine (Holt base yield) |
| Climate fit | 20 | linear penalty for climatology rain/temp outside crop optimal range | Open-Meteo climatology + KB |
| District track record | 20 | percentile of crop's district yield vs same crop across districts; ±2 for Holt trend direction | crop.db |
| Stability | 10 | 10 × (1 − CV of district yields 2016–2024), floor 0 | crop.db |

Output per candidate: composite + every component (value + provenance) + water need (KB) + risk level (yield-CV terciles) + est. profit (finance engine). Yield data role: relative track record + Holt base into finance with band ("projection from BBS 2016–2024, not a guarantee") + CV risk — never "recommend the highest-yield crop."

## 7. Provenance (enforced by schema, not prompt)

Every number reaching the UI carries a Provenance object:

```
value, unit, source_type: kb|api|dataset|static_table|computed,
source_id, source_title, locator (page/table/url/query), retrieved_at,
formula (human-readable, if computed), confidence: high|medium|low
```

KB chunks store source URL, publication date, section/table id at ingest; metadata flows into Provenance at retrieval. Rule: a number without Provenance must not render. B shows provenance on tap/hover. Yearbook/DAM prices carry honest confidence ("prices move" → medium).

## 8. Scope tiers

Gate rule: [GATED] items may not start before the `tier0-stable` tag (target H15) AND green main.

### Tier 0 — required (done H12, hardened H15)

1. **Conversational intake (Bangla, hybrid)** — required: location, farm size, soil, water, budget, season (+ land type উঁচু/মাঝারি/নিচু when season makes drainage relevant, agent-decided). Optional non-blocking after first ranking: last crop, risk preference, transport distance. Agent runs gap detection and decides what to ask (the judged behavior); each question ships with an `input_request` widget — district: searchable 64-dropdown; area: number + unit selector (bigha/katha/decimal); soil/water/season/land type: chips; budget: number. Free text always works in parallel; agent extracts stated fields and skips their widgets. Widgets are accelerators, not a form wizard. Before generating a plan, agent restates the full farm profile for verification. Chat stays conversational: restatement + compact Bangla summary + confidence note + at most one question; full structure lives in the tabs.
2. **Live weather grounding** — `get_forecast` (Open-Meteo 16-day) + `get_climatology` (normals); every claim labeled `source_type`; Bangla wording split ("পূর্বাভাস অনুযায়ী" vs "গত বছরের গড় অনুযায়ী, ভিন্ন হতে পারে"). No invented weather, ever.
3. **Crop recommendation** — §6 scorer over the six-crop universe; ≥3 ranked candidates in the rehearsed Rabi path; honest short-list + forward offer if a judge forces kharif-2 (§3.3).
4. **Season plan** — dated calendar land prep → harvest incl. weed and pest CHECKPOINT dates (from BRRI/BARI manuals), tasks flagged `depends_on_weather`, each task with source.
5. **Financial projection** — itemized costs; yield = damped-Holt base; three scenarios (base±band, price±10%); revenue, net profit, ROI, break-even yield AND price. `data/prices.md` covers all six crops: selling prices from Yearbook Ch10 (harvest-time + wholesale 2023–24, trend) + one current DAM daily bulletin (today's price, dated); wages from Ch7.5; seed/fertilizer prices from BARC/DAE/market with URL + date — every row cited or deleted. Computed only in `backend/finance/` pure functions with consistency tests. LLM never does arithmetic.
6. **Explained reasoning** — §4 behaviors + §7 provenance.
7. **Knowledge base with RAG** — curated markdown written in-event from the §3.5 named documents, with URL/page provenance; coverage per §3.4 tiers; Chroma index built in-event by `ingest.py`. Plus crop.db via SQL tool. RAG queries in English (cross-lingual fix), conversation Bangla. No live crawling in core — two live APIs + curated KB keeps the demo deterministic; general web-fetch [GATED].
8. **Visible agent trace** — live panel, every tool call: name, params, raw results, timestamp. English. Redacted (§10). Any number traceable to an entry.

### Tier 1 (H15–H18, priority order)

1. Persistent memory across sessions (demo it).
2. Scenario simulation — "rainfall −30%?" / "budget −40%?" → scorer + finance re-run, deltas shown.
3. Fertilizer & irrigation scheduler (BARC + Kc), organic alternatives, cost. Tier-A crops first.
4. Proactive weather-triggered advice — `check_plan_conflicts` on session open + "আমার প্ল্যান চেক করুন" button; alert banner; farmer-confirmed revision.
5. [GATED] Pest and disease RISK PREDICTION (crop × stage × weather, KB-driven). Tier-A crops only. (Checkpoint dates are Tier 0; prediction is what's gated.)

### Tier 2 (bonus)

1. **bdapps CaaS checkout** (10 pts, near-required, NOT gated): simulator primary, built H3–H6, exact shapes incl. E1326; confirmation step ("৳X কাটা হবে — নিশ্চিত?"); Bengali SMS receipt (encoding 16); `mode: live|simulator` labeled everywhere; live path only if portal unblocks, tested H15–18 on the Robi SIM, rehearsed one-click fallback toggle.
2. AEZ soil cross-check (NOT gated): farmer-stated soil vs Yearbook Ch1 AEZ district profile; disagreement → confirm (recovery #3). Rajshahi's AEZ-11/Barind split makes this a real demo moment.
3. Bengali-first interaction — core already; claim in README.
4. [GATED] Market price intelligence / sell-store-wait.
5. [GATED] PlantVillage leaf-photo disease detection (pretrained only).
6. [GATED] Voice input (Bangla STT).
7. [GATED] 7th kharif-2 crop (brinjal) per §3.3.
8. [GATED] SoilGrids as an extra only if truly idle (AEZ check supersedes it).

### Non-goals regardless

Marketplace/escrow, USSD/SMS inbound, satellite imagery, model training, auth beyond farm profiles, visual polish beyond one clean responsive page. Explicitly: no generalized multi-domain schema, no 14-edition extraction pipeline, no livestock/fisheries data — Horizon 2 (§12) is README-only.

## 9. Product shape

PWA (manifest-only, no service worker in core); one responsive page: chat primary, Plan/Finance/Trace tabs (desktop: trace side panel); Noto Sans Bengali; Western numerals in tables/computed values; trace panel English; agent mirrors user language, defaults Bangla. Frontend follows the anti-slop + farmer-first rules in CLAUDE.md.

## 10. Data rules (competition-safe) + honesty ledger

All application code — parser, Holt fitting, Chroma ingest — written and run DURING the event; derived artifacts (crop.db, index) generated in-event with meta timestamps; raw public yearbook extracts hosted publicly, link in README; pre-cached third-party models/wheels/packages fine.

| Data | Source | Real/Mock |
|---|---|---|
| Weather forecast + climatology | Open-Meteo API, live | Real |
| District yield/area 2016–2024 + Holt projections, six crops (parser keeps extra cleanly-parsed crops) | BBS Yearbook (public raw extracts); parsed + fitted in-event; every row edition/table/page-cited | Real |
| Fertilizer doses, crop calendars — six crops, two depth tiers | §3.5 named BARC/BRRI/BARI/DAE documents, curated in-event | Real (curated) |
| Crop water coefficients | FAO-56 Kc table | Real |
| Input + selling prices — six crops | Yearbook Ch10 2023–24 (trend) + current DAM daily bulletin (today, dated) + BARC/DAE input prices, hand-curated, row-cited | Real (official, dated) |
| Labor wages | Yearbook Ch7.5, curated in-event | Real |
| District soil profile | Yearbook Ch1 AEZ tables (full table — soil check works nationwide) | Real |
| Official crop calendar | Yearbook Ch1.8, curated in-event | Real |
| District crop damage (optional risk refinement) | Yearbook Ch4 | Real if included |
| bdapps | Simulator matching documented shapes; live if portal unblocks | Disclosed either way |

Trace redaction: password/appId/key/token/secret → `***`; phone/subscriberId → last 3 digits; unit-tested against a fake bdapps payload.

## 11. Stack

Custom agent loop on Claude API (Sonnet, native tool use, env-var model switch only) · Python FastAPI + SSE · Chroma embedded, in-event index · sentence-transformers pre-cached, English queries · crop.db SQLite + SQL tool · SQLite WAL memory · Vite + React manifest PWA · Open-Meteo · bdapps via httpx + simulator twin.

## 12. Horizon 2 — the national platform (README + demo close ONLY; zero build minutes)

One README section + the demo's final 30 seconds: crop.db's long/tidy, provenance-per-row design generalizes to an `observations` table covering all 146 crops, livestock, fisheries, prices, weather, and disaster loss across all 14 yearbook editions (2012–2025) — turning AgriSense from one farmer's advisor into Bangladesh's citable agricultural intelligence layer, same rule throughout: every number carries its page. Banks Innovation points and frames Q&A at zero build cost. Anything from this section appearing in code before the demo is a scope bug.

## 13. PLAN.md amendments — APPLIED

The eight amendments from PRD v3 §13 have been folded into PLAN.md directly (ownership map, H1 double-freeze, H3–H6 A/B rewrites, scorer test cases, H12 gate additions, demo script changes, README items). PLAN.md is the single execution source; do not re-derive from here.

## 14. Success criteria → 100 pts

Agentic 20: five behaviors + two recoveries in one run. Accuracy 20: finance tests pass, live input change recomputes, yields match crop.db. Scope 15: Tier 0 end-to-end, stable, rehearsed. KB 12: trace shows retrieval feeding advice, named sources in README. bdapps 10: full checkout flow, labeled mode. Explainability 10: provenance on every number. Technical 8: pinned deps, tests on finance/units/scorer/redactor. Innovation 5: scenario sim + proactive alerts + Bangla PWA + Horizon-2 framing + any gated wins.

## 15. Decision record

1. Six-crop set (§3.2) incl. Aus/Jute → Maize/Mustard swap — **RATIFIED at merge.**
2. crop.db DDL (§5) — **RATIFIED**; A commits `data/crop_schema.sql` at H1.
3. Demo target season = Rabi, district = Rajshahi (§3.3) — **RATIFIED**; B bakes into seeded farm + rehearsal script.
4. Maize/Mustard series length in the raw extract — **OPEN**, decided at the H3–H6 half-cap check per §3.4 degradation order, never silently. If a series is short, `holt_projections.n_points` discloses it.