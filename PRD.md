# PRD — AgriSense AI (TeamFixeth_AgriSense)

IUT 12th ICT Fest — Bdapps Agentic AI Hackathon, Final Round. 24h build: 24 Jul 09:00 → 25 Jul 09:00.

## 1. One-line product

A Bangla-first PWA where a smallholder farmer talks to an autonomous agent that produces a costed, weather-grounded season plan for their specific farm — and every number in that plan is traceable to a real tool call.

## 2. Target user

Bangladeshi smallholder farmer. Low literacy assumed. Speaks/reads Bangla. Uses a cheap Android phone. Thinks in bigha/katha, BDT, and district names — not hectares or lat/lon.

Secondary user: the judge. Needs to verify in <4 minutes that the agent is real (trace panel), the math is real (change input → outputs change), and the data is real (weather + KB citations).

## 3. Why an agent (not a chatbot)

The five judged agentic behaviors, and where we demonstrate each:

| Behavior | Where it shows |
|---|---|
| Tool use | Open-Meteo forecast + climatology, geocoder, Chroma RAG, agribase SQL, finance engine, bdapps CaaS. All real values, all in trace. |
| Multi-step planning | One request ("plan my season") triggers: geocode → weather → RAG → crop ranking → calendar → finance. Visible as chained tool calls. |
| Missing info handling | Intake checklist (location, size, soil, water, budget, season). Agent detects gaps, asks targeted Bangla follow-ups only for missing fields. |
| Memory | SQLite farm profile + conversation state. Survives restart → returning farmer never repeats. Demo opens with a remembered farm. |
| Explainability | Every recommendation names its inputs: "৪৫ কেজি ইউরিয়া... because soil=loam (you said), stage=vegetative (calendar), rain=0mm next 5 days (Open-Meteo, called 14:02)." |

## 4. Scope tiers (mirrors judging)

### Tier 0 — required, all 8 (target: done by H12, hardened by H15)

1. **Conversational intake (Bangla)** — collects location, farm size, soil, water availability, budget, season. Local units accepted (bigha/katha/decimal), normalized internally.
2. **Live weather grounding** — Open-Meteo forecast API (16-day, real) for near-term actions; Open-Meteo climate/historical API (real) for the long-range calendar. Agent states which source per claim. No invented forecasts, ever.
3. **Crop recommendation** — ≥3 ranked candidates with suitability, water need, risk, rough profit. Profit grounded in agribase district yields, not model recall.
4. **Season plan** — dated calendar: land prep → sowing window → fertilizer timings → irrigation → weed/pest checkpoints → harvest.
5. **Financial projection** — itemized costs, expected yield, revenue, net profit, ROI, break-even. Computed by deterministic finance engine (pure functions, unit-tested). LLM never does arithmetic. Change an input → outputs change correctly.
6. **Explained reasoning** — see table above; enforced by system prompt + response schema.
7. **Knowledge base with RAG** — curated markdown from BARC fertilizer guide, DAE/extension crop calendars, FAO-56 Kc table, covering 5–6 demo crops (boro/aman rice, wheat, potato, lentil, mustard). Chroma embedded, retrieval feeds advice. Plus structured agribase SQLite (yearbook 2016–2024, district-level yield/area) as an SQL tool.
8. **Visible agent trace** — live side/bottom panel streaming every tool call: name, params sent, raw values returned, timestamp. English. Judge can match any number in the plan to a trace entry.

### Tier 1 — differentiation (H15–H18, in priority order)

1. Persistent memory across sessions (mostly free from SQLite design — just demo it).
2. Scenario simulation — "rainfall −30%?", "budget −40%?" → re-run finance engine + plan deltas with changed numbers.
3. Fertilizer & irrigation scheduler — quantities by growth stage (BARC + FAO-56 Kc), organic alternatives, cost.
4. Proactive weather-triggered advice — forecast check on session open; if rain conflicts with a scheduled application, agent volunteers the adjustment.
5. Pest/disease risk from crop × stage × weather (KB-driven) — only if 1–4 done.

### Tier 2 — bonus (H18+, only if Tier 0/1 green)

1. **bdapps CaaS checkout** (10 pts — treated as near-required): balance query → direct debit (small real amount on Robi SIM) → SMS receipt (Bengali encoding 16). Simulator fallback with exact request/response shapes if portal app not approved or IP whitelist fails. All-outbound flow — no public callback URL needed.
2. SoilGrids REST cross-check of farmer-stated soil type (~30 min, second real external API).
3. Bengali interaction — already core, claim the bonus in README.
4. Market price / sell-store-wait — parking lot.
5. PlantVillage leaf-photo disease detection — parking lot, pretrained HF model only.

### Explicit non-goals

Marketplace/escrow, USSD/SMS inbound flows, satellite imagery (NASA/SERVIR/Sentinel), model training of any kind, auth/user accounts beyond farm profiles, polished visual design.

## 5. Product shape

- **PWA**: installable, manifest + service worker (prod build only), mobile-first layout. Chat is the primary surface; trace panel is a bottom-sheet/expandable on mobile, side panel on desktop.
- **Bangla-first**: agent converses in Bangla by default (mirrors user's language if they switch). UI labels Bangla, Noto Sans Bengali. Numbers in math tables stay Western numerals for judge inspectability. Trace panel English.
- **Views**: Chat | Plan (season calendar) | Finance (cost table, editable inputs) | Trace.

## 6. Stack (final)

| Layer | Choice | Why |
|---|---|---|
| Agent loop | Custom loop on Claude API (Sonnet), tool-use native | Own the loop → trivial trace emission; no framework debugging at 3am |
| LLM fallback | Gemini Flash / Groq behind a one-file client abstraction | Provider outage insurance |
| Backend | Python FastAPI + SSE | Tools are Python functions; fast to write; simple streaming |
| RAG | Chroma, embedded/local | Zero infra, survives venue wifi death |
| Embeddings | sentence-transformers (pre-cached locally) | Offline-safe; queries formulated in English by the agent (cross-lingual fix) |
| Structured data | agribase SQLite (yearbook 2016–2024) via SQL tool | Real district yields → real profit numbers |
| Memory | SQLite (farm profile, conversations, plans), WAL mode | Persistent memory Tier 1 nearly free |
| Frontend | Vite + React PWA (vite-plugin-pwa) | Real SSE trace panel; mobile-first; SW off in dev |
| Weather | Open-Meteo (forecast + climate endpoints) | Free, keyless, real, has historical |
| Payments | bdapps CaaS via httpx (plain JSON POST, auth in body) | Matches provided API reference; outbound-only |

## 7. Success criteria (map to 100 pts)

- Agentic (20): all five behaviors visible in one demo run.
- Accuracy (20): finance engine unit tests pass; judge changes an input live and outputs update; yields match agribase for the district.
- Scope (15): Tier 0 runs end-to-end, stable, rehearsed twice.
- KB/RAG (12): trace shows retrieval chunks feeding the advice; README lists sources.
- bdapps (10): live debit + SMS receipt on stage, or labeled simulator with correct shapes.
- Explainability (10): every recommendation cites its inputs inline.
- Technical (8): pinned deps, clean tool interfaces, tests on finance + units.
- Innovation (5): scenario simulation + proactive advice + SoilGrids cross-check + Bangla PWA.

## 8. Data sources & honesty ledger (mirror into README)

| Data | Source | Real/Mock |
|---|---|---|
| Weather forecast + climatology | Open-Meteo API, live | Real |
| District yield/area 2016–2024 | National Yearbook of Agricultural Statistics (BBS), parsed to SQLite before event (data artifact, not application code; also published publicly at <link>) | Real |
| Fertilizer doses, crop calendars | BARC / DAE public guides, curated to markdown during event | Real (curated) |
| Crop water coefficients | FAO-56 Kc table | Real |
| Soil cross-check | SoilGrids REST API | Real (if included) |
| Market prices for profit estimate | Static reference table with cited source + date | Semi-real (disclosed) |
| Supplier catalog | Not built | — |
| bdapps | Live CaaS on Robi SIM, or simulator with documented shapes | Disclosed either way |
