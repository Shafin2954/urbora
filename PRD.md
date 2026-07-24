# PRD v3 — AgriSense AI (TeamFixeth_AgriSense)

IUT 12th ICT Fest — Bdapps Agentic AI Hackathon, Final Round. 24h: 24 Jul 09:00 → 25 Jul 09:00, demo 25 Jul 10:00. **This document replaces PRD.md (v2).** PLAN.md stays authoritative for execution except the amendments in §13 here — fold those in, don't fork. NOTES.md and CLAUDE.md unchanged and still binding.

**Provenance of this document:** merge of PRD v2 (Shafin vai) and ADR-001 (Claude instance A). PRD.md is B-side territory — A proposes this v3; Shafin vai merges or amends. Every contradiction between the two sources is resolved in §0 with reasoning, per the "keep what you prefer, say why" instruction.

---



## 1. One-line product

A Bangla-first PWA where a smallholder farmer talks to an autonomous agent that produces a costed, weather-grounded season plan for their specific farm — and every number in that plan carries provenance a judge can inspect.

## 2. Target users

Primary: Bangladeshi smallholder farmer. Low literacy assumed, Bangla, cheap Android phone, thinks in bigha/katha, BDT, district names.
Secondary: the judge. Must verify in <4 min: the agent is real (trace), the math is real (change input → outputs change), the data is real (provenance on every number).

## 3. The six-crop core (NEW — supersedes "3 demo crops")

### 3.1 Selection criteria, in priority order

1. **Demo-season viability.** The demo is 25 July. A crop whose sowing window cannot intersect any season a farmer would plausibly plan on that date will never pass the scorer's hard season filter → it can never appear on stage. Kharif-1 crops (Aus, Jute: sown Mar–May) fail this outright.
2. **Data density in the yearbook.** District-level area/yield/production series long enough for Holt + CV (≥6 points across editions), Ch10 harvest-time/wholesale price rows, presence in the Ch1.8 crop calendar.
3. **Guidance availability.** BARC fertilizer doses and DAE calendar/practice material exist and are curatable within the cap.
4. **Ranking-demo richness.** The set should give ≥3 surviving candidates in the demo target season, with genuinely different profiles (water need, cost, risk, profit) so the component breakdown tells a story.

### 3.2 The set

| Crop | Season(s) | Why in |
|---|---|---|
| **Boro rice** | Rabi (Dec–Feb sow, Apr–Jun harvest) | Highest-volume crop in BD; densest data of anything in the book; irrigation-heavy → water-class filter demo. |
| **Wheat** | Rabi (Nov–Dec sow) | BBS major; low-water Rabi contrast to Boro. |
| **Potato** | Rabi (Nov–Dec plant) | BBS major; high-cost/high-revenue profile → makes the budget-exclusion recovery moment realistic. |
| **Maize** | Rabi (Oct–Dec sow; kharif window exists) | Among the best-covered minor crops; strong profit narrative; BARC dose tables solid. |
| **Mustard** | Rabi (Oct–Nov sow) | Classic low-cost/low-water rotation crop; the "small budget" answer; good coverage. |
| **Aman rice (T.Aman)** | Kharif-2 (Jul–Aug transplant) | The season that is literally open on demo day; covers "এখন কী লাগাব?" honestly. |

**Excluded, with reasons stated up front (judges may ask):** Aus and Jute — best-in-book data, but sowing windows closed at demo time (criterion 1 dominates criterion 2). Livestock/fisheries/etc. — out of problem scope entirely.

### 3.3 Season logic for the demo

- The rehearsed demo farmer plans **Rabi** ("আগামী রবি মৌসুমের জন্য") — realistic in July (seed booking, input budgeting) and gives 5 candidates → rich ranking.
- If a judge forces "plant now": season filter yields T.Aman (+ nothing else from the set). The agent says so honestly — "এই মুহূর্তে খরিপ-২ মৌসুমে এই তালিকা থেকে মূলত আমনই উপযুক্ত" — ranks what survives, and *offers the Rabi plan as the forward look*. Honest degradation is itself scored recovery behavior; padding the kharif-2 list with fabricated candidates is the failure mode.
- [GATED, cheap hedge] a 7th crop with a kharif-2 window (brinjal or kharif maize variant) may be added post-`tier0-stable` if the team wants ≥3 live candidates for "now" queries. Proposal only until the gate opens.

### 3.4 KB depth tiers (keeps the curation cap honest)

- **Tier-A depth** (3 crops: Boro, Potato, Maize — the likely demo picks): full calendar with stage dates, BARC dose schedule by growth stage, variety note, 2–3 pest/disease entries, water/Kc rows, cost template fully itemized.
- **Tier-B depth** (Wheat, Mustard, Aman): calendar, total dose + split timing, soil/water class, cost template.
- **Cap: 3.5h total** for A's KB + hand-curated yearbook tables (was 3h/3 crops). **Degradation order if slipping at the half-cap check:** drop Mustard → drop Maize to Tier-B → drop to 4 crops (Boro, Wheat, Potato, Aman). Log the drop; never silently thin the data.

Scorer, finance, and prices.md cover **all six** regardless of KB tier — those cost minutes per crop, not hours.

## 4. The five judged agentic behaviors — where each shows (unchanged from v2)

| Behavior | Where |
|---|---|
| Tool use | Open-Meteo forecast + climatology, geocoder, Chroma RAG, crop.db SQL, crop scorer, finance engine, bdapps CaaS. Real values, all traced. |
| Multi-step planning | "Plan my season" → geocode → weather → RAG → scorer → calendar → finance, chained visibly. |
| Missing info + recovery | Intake gap detection with targeted Bangla follow-ups. Scripted recoveries: geocode ambiguity → confirm; budget too low → reduced-area/cheaper-crop replan; weather API down → retry then labeled cached data; missing KB evidence → admit insufficiency. ≥2 recoveries in the demo. |
| Memory | SQLite farm profile + conversations + plans. Survives restart. Demo opens with a remembered farm. |
| Explainability | Every recommendation names inputs + provenance: "৪৫ কেজি ইউরিয়া — soil=loam (আপনি বলেছেন), stage=vegetative (calendar), rain=0mm/5d (পূর্বাভাস, Open-Meteo 14:02)." |

## 5. crop.db — canonical schema (NEW; closes the v2 gap)

Owner: A. Generated in-event by `parse_agribase.py` + `holt.py`; timestamps in `meta`. Schema below is frozen with schemas.py at H1; changes follow the same protocol (log + A approval + ping B).

```sql
-- one row per crop×district×year observation; long/tidy
CREATE TABLE district_series (
  crop        TEXT NOT NULL,      -- canonical english name, matches KB + scorer keys
  district    TEXT NOT NULL,      -- canonical district name (64-list in units/geo module)
  year        INTEGER NOT NULL,   -- harvest year of the split year (2016–2024)
  season      TEXT,               -- aus|aman|boro|rabi|kharif1|kharif2|annual, where the table gives it
  area_ha     REAL,
  production_mt REAL,
  yield_t_ha  REAL,               -- as published; recompute-check against area×prod in validation
  edition     TEXT NOT NULL,      -- yearbook edition the row came from, e.g. '2024'
  source_table TEXT NOT NULL,     -- e.g. '3.1 Boro'
  source_page INTEGER,            -- page in that edition; NULL only if genuinely unpaginated in extract
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
1. **Every `district_series` row carries `edition + source_table + source_page`.** This is the surviving core of the original provenance mandate. `cropdb_sql` tool results map these into the Provenance object (`source_type: dataset`, `locator: "{edition} {source_table} p.{source_page}"`).
2. `holt_projections` rows are `source_type: computed`; their Provenance `formula` field names the method and the underlying series ("damped Holt over BBS {district} {crop} 2016–2024, n={n}").
3. Parser ingests **whatever crops the source extract cleanly yields** (no artificial filter — extra rows are free and honest), but the **scorer's candidate universe is exactly the six curated crops**, because a crop without a calendar, dose schedule, cost template, and price row cannot be ranked without fabricating one of them. State this in README; it is a feature, not a limitation.
4. Validation (slimmed, in-parser, printed to console + meta): row counts per crop×edition, null rates, yield≈production/area cross-check within tolerance, YoY jump flags >40%. Flag, never repair (unchanged rule).

## 6. Crop recommendation algorithm (deterministic, inspectable — unchanged from v2, now over 6 crops)

`backend/tools/crop_scorer.py` (owner A). Pure function, unit-tested. The LLM narrates scorer output in Bangla; the LLM never ranks crops itself.

### Stage 1 — hard exclusions (each logged with farmer-readable reason)

| Filter | Rule | Source |
|---|---|---|
| Season | sowing window ∩ target season = ∅ → exclude | KB crop calendar |
| Soil | farmer soil not in crop's allowed list → exclude | KB |
| Water | crop water class > farm water class (rainfed < tubewell < canal/irrigated) → exclude | KB + intake |
| Budget | min_cost_per_ha × area > budget → exclude, agent offers reduced-area replan (recovery moment) | finance engine |

### Stage 2 — suitability score 0–100 for survivors

| Component | Max | Computation | Source |
|---|---|---|---|
| Agronomic fit | 25 | soil primary=25 / secondary=15 / marginal=8 | KB |
| Profit | 25 | net profit/ha (base scenario), min-max normalized within candidate set | finance engine (Holt base yield) |
| Climate fit | 20 | linear penalty for climatology rain/temp outside crop optimal range | Open-Meteo climatology + KB |
| District track record | 20 | percentile of this crop's district yield vs same crop across districts; ±2 for damped-Holt trend direction | crop.db |
| Stability | 10 | 10 × (1 − CV of district yields 2016–2024), floor 0 | crop.db |

Output per candidate: composite + every component (value + provenance) + water need (KB) + risk level (yield-CV terciles) + est. profit (finance engine). Judge sees exactly why #1 beat #2. Yield data role unchanged: relative track record + Holt base into finance with band ("projection from BBS 2016–2024, not a guarantee") + CV risk — never "recommend the highest-yield crop."

## 7. Provenance (enforced by schema, not prompt — unchanged)

Every number reaching the UI carries a Provenance object:

```
value, unit, source_type: kb|api|dataset|static_table|computed,
source_id, source_title, locator (page/table/url/query), retrieved_at,
formula (human-readable, if computed), confidence: high|medium|low
```

KB chunks store source URL, publication date, section/table id at ingest; metadata flows into Provenance at retrieval. Rule: a number without Provenance must not render. B shows provenance on tap/hover.

## 8. Scope tiers (v2 structure kept; six-crop amendments marked ✏)

Gate rule unchanged: [GATED] items may not start before the `tier0-stable` tag (target H15) AND green main.

### Tier 0 — required (done H12, hardened H15)

1. **Conversational intake (Bangla, hybrid)** — as v2: required fields location, farm size, soil, water, budget, season (+ land type when relevant); gap detection agent-decided; `input_request` widgets as accelerators; free text in parallel; profile restated before planning; structured output lives in tabs.
2. **Live weather grounding** — `get_forecast` (Open-Meteo 16-day) + `get_climatology` (normals), every claim labeled `source_type`, Bangla wording split ("পূর্বাভাস অনুযায়ী" vs "গত বছরের গড় অনুযায়ী, ভিন্ন হতে পারে"). No invented weather, ever.
3. **Crop recommendation** — §6 scorer over the ✏six-crop universe; ≥3 ranked candidates in the rehearsed (Rabi) path; honest short-list + forward offer if a judge forces kharif-2 (§3.3).
4. **Season plan** — dated calendar land prep → harvest, tasks flagged `depends_on_weather`, each task with source.
5. **Financial projection** — itemized costs; yield = damped-Holt base; three scenarios (base±band, price±10%); revenue, net profit, ROI, break-even yield AND price. ✏`data/prices.md` covers all six crops: selling prices from Yearbook Ch10 (harvest-time + wholesale 2023–24), wages from Ch7.5, seed/fertilizer prices from BARC/DAE/market with URL + date — every row cited or deleted. Computed only in `backend/finance/` pure functions with consistency tests. LLM never does arithmetic.
6. **Explained reasoning** — §4 behaviors + §7 provenance.
7. **Knowledge base with RAG** — curated markdown from BARC/DAE + FAO-56 Kc + BAMIS advisories, written in-event with URL provenance; Chroma index built in-event; ✏coverage per §3.4 tiers. RAG queries in English, conversation Bangla. No live crawling in core.
8. **Visible agent trace** — live panel, every tool call: name, params, raw results, timestamp. English. Redacted (§10). Any number traceable to an entry.

### Tier 1 (H15–H18, priority order — unchanged)

1. Persistent memory across sessions (demo it).
2. Scenario simulation — "rainfall −30%?" / "budget −40%?" → scorer + finance re-run, deltas shown.
3. Fertilizer & irrigation scheduler (BARC + Kc), organic alternatives, cost. ✏Tier-A crops first.
4. Proactive weather-triggered advice — `check_plan_conflicts` on session open + "আমার প্ল্যান চেক করুন" button; alert banner; farmer-confirmed revision.
5. [GATED] Pest and disease risk (crop × stage × weather, KB-driven). ✏Tier-A crops only.

### Tier 2 (bonus — unchanged)

1. **bdapps CaaS checkout** (10 pts, near-required, NOT gated): simulator primary, built H3–H6, exact shapes incl. E1326; confirmation step; Bengali SMS receipt; `mode: live|simulator` labeled everywhere; live path only if portal unblocks, tested H15–18, rehearsed fallback toggle.
2. AEZ soil cross-check (NOT gated): farmer-stated soil vs Yearbook Ch1 AEZ district profile; disagreement → confirm (recovery #3).
3. Bengali-first interaction — core already; claim in README.
4. [GATED] Market price intelligence / sell-store-wait.
5. [GATED] PlantVillage leaf-photo disease detection (pretrained only).
6. [GATED] Voice input (Bangla STT).
7. ✏[GATED] 7th kharif-2 crop (brinjal) per §3.3.

### Non-goals regardless

Marketplace/escrow, USSD/SMS inbound, satellite imagery, model training, auth beyond farm profiles, visual polish beyond one clean responsive page. ✏Plus, explicitly: no generalized multi-domain schema, no 14-edition extraction pipeline, no livestock/fisheries data — Horizon 2 (§12).

## 9. Product shape (unchanged)

PWA (manifest-only, no service worker in core); one responsive page: chat primary, Plan/Finance/Trace tabs (desktop: trace side panel); Noto Sans Bengali; Western numerals in tables/computed values; trace panel English; agent mirrors user language, defaults Bangla.

## 10. Data rules (competition-safe) + honesty ledger (✏ amended rows only)

All application code — parser, Holt fitting, Chroma ingest — written and run DURING the event; derived artifacts (crop.db, index) generated in-event with meta timestamps; raw public yearbook extracts hosted publicly, link in README; pre-cached third-party models/wheels/packages fine.

| Data | Source | Real/Mock |
|---|---|---|
| Weather forecast + climatology | Open-Meteo API, live | Real |
| ✏District yield/area 2016–2024 + Holt projections, six crops (parser keeps any extra crops the extract yields) | BBS Yearbook (public raw extracts); parsed + fitted in-event; every row edition/table/page-cited | Real |
| ✏Fertilizer doses, crop calendars — six crops, two depth tiers | BARC / DAE public guides, curated in-event | Real (curated) |
| Crop water coefficients | FAO-56 Kc table | Real |
| ✏Input + selling prices — six crops | Yearbook Ch10 2023–24 + BARC/DAE, hand-curated, row-cited | Real (official, dated) |
| Labor wages | Yearbook Ch7.5, curated in-event | Real |
| District soil profile | Yearbook Ch1 AEZ tables, curated in-event | Real |
| Official crop calendar | Yearbook Ch1.8, curated in-event | Real |
| District crop damage (optional risk refinement) | Yearbook Ch4 | Real if included |
| bdapps | Simulator matching documented shapes; live if portal unblocks | Disclosed either way |

Trace redaction unchanged from v2 §9: password/appId/key/token/secret → `***`; phone/subscriberId → last 3 digits; unit-tested against a fake bdapps payload.

## 11. Stack (unchanged from v2)

Custom agent loop on Claude API (Sonnet, native tool use, env-var model switch only) · Python FastAPI + SSE · Chroma embedded, in-event index · sentence-transformers pre-cached, English queries · crop.db SQLite + SQL tool · SQLite WAL memory · Vite + React manifest PWA · Open-Meteo · bdapps via httpx + simulator twin.

## 12. Horizon 2 — the national platform (README + demo close ONLY; zero build minutes before 25 Jul 10:00)

One README section + the demo's final 30 seconds: crop.db's long/tidy, provenance-per-row design generalizes to `observations(entity_type, entity_id, region_id, year, season, metric, value, unit, edition, source_page, …)` covering all 146 crops, livestock, fisheries, prices, weather, and disaster loss across all 14 yearbook editions (2012–2025) — turning AgriSense from one farmer's advisor into Bangladesh's citable agricultural intelligence layer, with the same rule throughout: every number carries its page. Per-era extraction profiles, validation reports, and the narrative corpus live here too. This banks Innovation points and frames Q&A at zero build cost. Anything in this section appearing in code before the demo is a scope bug.

## 13. PLAN.md amendments (apply these; the rest of PLAN v2 stands)

1. **§1 ownership map** — add `data/crop_schema.sql ← A` (the §5 DDL, committed at H1 with schemas.py).
2. **H1 freeze** — schemas.py **and §5 crop.db DDL** frozen together. Same change protocol.
3. **H3–H6, A:** "KB curation, 3 demo crops deep (cap 3h)" → "KB curation, **6 crops per PRD §3.4 tiers (cap 3.5h incl. yearbook hand-curated tables); half-cap check at ~1.75h; degradation order: drop Mustard → Maize to Tier-B → 4 crops (Boro, Wheat, Potato, Aman), logged.**" parse_agribase.py targets the six crops' district series 2016–2024; extra cleanly-parsed crops kept, never chased.
4. **H3–H6, B:** prices.md covers **all six crops** (Ch10 + Ch7.5 + cited input prices). Budget ~20 min/crop for the cost template rows; Tier-A crops first so finance is demo-ready even if Tier-B rows land late.
5. **H6–H9, A:** scorer unit tests must include: a season-exclusion case (Jute/Aus-style window miss), a budget-exclusion case, and a **kharif-2 short-list case asserting the honest ≤2-candidate output** (§3.3) — that behavior is demo-relevant and must not regress.
6. **H12 Tier-0 gate check adds:** all six crops return a finance projection without provenance gaps; Rabi query returns ≥3 ranked candidates with component breakdowns.
7. **§5 demo script, step 2:** the farmer's ask is Rabi planning ("আগামী রবি মৌসুমে কী চাষ করব?") → 5 candidates enter, ≥3 ranked shown, ≥1 exclusion shown with reason. Step 4's budget-cut scenario should flip the ranking toward Mustard (low-cost) — verify in rehearsal that the numbers actually produce the flip; if not, use area-change instead and log it.
8. **README (H20–H22):** add §3.2's excluded-crops reasoning (one paragraph) and the §12 Horizon-2 section.

## 14. Success criteria → 100 pts (unchanged mapping)

Agentic 20: five behaviors + two recoveries in one run. Accuracy 20: finance tests pass, live input change recomputes, yields match crop.db. Scope 15: Tier 0 end-to-end, stable, rehearsed. KB 12: trace shows retrieval feeding advice, sources in README. bdapps 10: full checkout flow, labeled mode. Explainability 10: provenance on every number. Technical 8: pinned deps, tests on finance/units/scorer/redactor. Innovation 5: scenario sim + proactive alerts + Bangla PWA + Horizon-2 framing + any gated wins.

## 15. Open decisions (need Jawat + Shafin vai sign-off before H1)

1. **Ratify the six-crop set** (§3.2) — specifically the Aus/Jute → Maize/Mustard swap. Alternative (pure BBS six majors) rejected because two of six would be invisible in every live demo query; overrule only with a reason logged.
2. **Ratify crop.db DDL** (§5) — A commits `data/crop_schema.sql` at H1 on approval.
3. **Demo target season = Rabi** (§3.3) — B bakes it into the seeded farm and rehearsal script.
4. Confirm the raw yearbook extract source that `parse_agribase.py` targets actually contains district series for Maize and Mustard back to ~2016; if a series is shorter, `holt_projections.n_points` discloses it and the scorer's stability component uses what exists. If either crop's series is unusably thin, fall back per §3.4 degradation order — decided at the H3–H6 half-cap check, not silently.
