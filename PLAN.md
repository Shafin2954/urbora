# PLAN v2 — Parallel Execution (TeamFixeth_AgriSense)

Two humans, two Claude Code instances (+ Codex assist), one repo. Zero blocking by design. PRD v2 is the spec; this is the schedule.

## 1. Ownership map (hard boundaries)

```
TeamFixeth_AgriSense/
├── backend/
│   ├── agent/        ← A   (agent loop, prompts, orchestration)
│   ├── tools/        ← A   (weather, geocode, rag_query, cropdb_sql, crop_scorer, check_plan_conflicts)
│   ├── kb/           ← A   (curated markdown, ingest.py, parse_agribase.py, holt.py)
│   ├── memory/       ← A   (farm profile, conversations, plans, alerts — SQLite)
│   ├── api/          ← B   (FastAPI routes, SSE stream + redacting trace emitter, sessions)
│   ├── finance/      ← B   (pure-function engine, 3 scenarios, provenance, tests)
│   ├── payments/     ← B   (bdapps client + simulator twin + mode toggle)
│   ├── units.py      ← B   (bigha/katha/decimal/acre ↔ ha; maund ↔ kg; tested)
│   └── schemas.py    ← A owns, B imports. Post-freeze changes: log entry + A approval + ping B.
├── frontend/         ← B   (Vite React, one responsive page: chat + Plan/Finance/Trace tabs)
├── data/
│   ├── raw/          ← A   (public yearbook extracts; link in README)
│   ├── crop.db       ← generated in-event by A's parser (gitignored or committed with meta timestamp)
│   └── prices.md     ← B   (every row: source + URL + date)
├── PRD.md PLAN.md NOTES.md CLAUDE.md LOG1.md LOG2.md README.md
```

Rule: never edit outside your directories. Cross-boundary need → log entry + tell the other human.

## 2. The contract (freeze at H1)

`backend/schemas.py`, owner A. Frozen H1; later changes announced + logged.

```python
# --- API ---
# POST /api/chat        {session_id, farm_id|null, message}  → SSE stream
# GET  /api/farms       → [FarmProfile]
# GET  /api/plan/{farm_id} → SeasonPlan | 404
# POST /api/finance/recompute {farm_id, overrides:{field:value}} → FinanceProjection
# POST /api/checkout    {farm_id, mobile, amount, items} → CheckoutResult
# POST /api/plan/{farm_id}/check → [Alert]        # proactive conflict check

# --- SSE events ---
# {type:"token", text}
# {type:"tool_call",   id, name, params, ts}          # REDACTED by emitter
# {type:"tool_result", id, name, result_raw, ts}      # REDACTED by emitter
# {type:"plan_update", plan}
# {type:"finance_update", finance}
# {type:"alert", alert}
# {type:"done", usage:{in_tokens, out_tokens, cost_usd}}
# {type:"error", message}

# --- Core models (pydantic) ---
# Provenance: value, unit, source_type: "kb"|"api"|"dataset"|"static_table"|"computed",
#             source_id, source_title, locator, retrieved_at, formula|null,
#             confidence: "high"|"medium"|"low"
# FarmProfile: farm_id, name, district, lat, lon, area_ha, area_local:{value,unit},
#              soil_type, water_source, budget_bdt, season, created_at
# CropCandidate: crop, composite_score, components:[{name, points, max, provenance}],
#                excluded:bool, exclusion_reason|null,
#                water_need, risk_level, est_profit_bdt, provenance:[Provenance]
# SeasonPlan: farm_id, crop, tasks:[{date, task, category, details,
#             depends_on_weather:bool, provenance}]
# FinanceProjection: scenarios:{conservative|base|optimistic:
#                      {items:[{name,qty,unit,unit_cost,total,provenance}],
#                       total_cost, expected_yield_kg, price_per_kg, revenue,
#                       net_profit, roi_pct}},
#                    breakeven_yield_kg, breakeven_price_bdt,
#                    assumptions:[Provenance]
# Alert: alert_id, farm_id, task_date, task, conflict, suggestion, created_at, status
# CheckoutResult: status, trx_id|null, mode:"live"|"simulator", receipt_sms_sent:bool, raw
```

A fills models; B renders. Finance is B's pure function exposed to A as a tool — A never computes money; the LLM never computes anything.

## 3. Hour-by-hour

| Hours | A (agent/tools/kb/memory) | B (api/ui/finance/payments) | Sync |
|---|---|---|---|
| H0–H1 | Scaffold backend, venv, pinned requirements. schemas.py drafted. Claude client (single, env-var model switch). | Scaffold Vite React (no SW). FastAPI skeleton + hello-world SSE reaching browser — kills CORS friction now. units.py started. | **H1: schemas frozen. SSE confirmed in browser.** |
| H1–H3 | Agent loop with get_forecast + get_climatology (labeled source_type). Geocode tool with candidate-confirm + 64-district fallback. Loop guards: max 12 iters, cost per turn. Weather wrapper: retry → labeled cached fallback. | Chat UI + SSE wiring. Redacting trace emitter + unit test (fake bdapps payload). units.py tests done. | H3: A's loop streams through B's UI end to end. |
| H3–H6 | KB curation, 3 demo crops deep (**cap 3h total incl. yearbook tables**): BARC/DAE docs + hand-curate from BBS Yearbook: crop calendar (Ch1.8), demo-region AEZ soil rows (Ch1), optional district damage (Ch4). parse_agribase.py + holt.py written + run → crop.db generated in-event (meta timestamps). ingest.py → Chroma index in-event. rag_query + cropdb_sql + aez_soil_check tools. | Finance engine: 3 scenarios, provenance on every item, break-even yield+price, consistency tests. bdapps simulator twin (exact shapes incl. E1326 path) + confirmation step + mode toggle. prices.md hand-curated from Yearbook Ch10 (prices) + Ch7.5 (wages), table/page cited. | H6: agent retrieves KB + crop.db numbers, visible in trace with provenance. |
| H6–H9 | crop_scorer.py (exclusions + 5 components) + unit tests. Intake state machine: gap detection, Bangla follow-ups. Budget-exclusion → replan path. | Checkout UI + receipt (Bengali). One responsive page: Plan/Finance/Trace tabs, provenance on tap. Bangla labels + Noto Sans Bengali. Manifest PWA. | H9: intake → ≥3 ranked crops, real numbers, exclusions with reasons. |
| H9–H12 | Season plan generation (KB calendars + climatology dates, tasks flagged depends_on_weather). Memory: save/load FarmProfile, resume sessions, alerts table. | Finance view editable inputs → /recompute live. Mobile responsive pass. plan_update/finance_update/alert events wired. | **H12: TIER 0 END-TO-END. Nothing else until this passes.** |
| H12–H15 | Fix H12 findings. Explainability audit: every number has provenance, every weather claim labeled. check_plan_conflicts tool. | Fix H12 findings. Seed demo farm. Error states (API down, geocode miss, insufficient balance). "আমার প্ল্যান চেক করুন" button + alert banner. | **H15: tag `tier0-stable`. GATE OPENS.** |
| H15–H18 | Tier 1: scenario simulation tool (scorer + finance re-run, deltas). Fertilizer/irrigation scheduler (BARC + Kc). Proactive check on session open. | If portal unblocked: live bdapps, whitelist venue IP, real ৳2 debit + SMS on Robi SIM; rehearse live↔simulator toggle. Else simulator polish. Trace polish. | H18: Tier 1 demo-able. |
| H18–H20 | GATED picks (only if green), suggested order: pest/disease risk → SoilGrids. | GATED picks: voice input or PlantVillage only if truly green; else PWA install test on phone, receipt polish. | H20: **feature freeze.** |
| H20–H22 | README: data rules story (§8 PRD), real-vs-mock table, setup, tiers reached. | README: bdapps, finance, frontend sections. **Demo rehearsal ×2, timed 4 min, including one recovery + toggle drill.** Offline boot test. | Submit repo link early. |
| H22–H23 | **Code freeze.** Demo-breaking bugfix only. Push. | Same. Verify final commit before cutoff. | — |
| H23–H24 | Buffer / sleep shifts. | Buffer. | — |

## 4. Git workflow

- `main` demo-ready only; `dev-a`, `dev-b`. Merge at sync points, A first (schemas authority), B rebases.
- Small commits, imperative messages. Before merging: finance/units/scorer/redactor tests + one manual end-to-end turn. Broken main forbidden after H12.
- Tag `tier0-stable` at H15 — the demo lifeboat AND the gate key for stretch scope.
- Never commit secrets. `.env.example` only. Check diff before push.
- Both push before cutoff even mid-polish. Late perfect commit = zero points.

## 5. Demo script (4 min, rehearsed twice)

1. **0:00–0:20** Returning farmer (seeded). Agent greets in Bangla, recalls farm. → memory.
2. **0:20–1:30** "এবার কী চাষ করব?" One targeted follow-up (gap detection), then chain: geocode (confirm district = recovery #1) → forecast + climatology → RAG → scorer → 3 ranked crops with component breakdown + one exclusion shown with reason. Trace filling live. → agentic + grounding.
3. **1:30–2:20** Pick crop → dated plan + 3-scenario finance. **Change area 2→3 bigha live** → everything recomputes. Tap a number → provenance. → accuracy + explainability.
4. **2:20–3:00** "বাজেট ৪০% কমলে?" → scorer + finance re-run, deltas; if crop flips, budget-replan = recovery #2. → Tier 1.
5. **3:00–3:40** Checkout fertilizer → confirmation → balance → debit → Bengali SMS receipt. Live on Robi SIM if portal unblocked; otherwise simulator, mode label visible; live-fail → one-click toggle, rehearsed. → 10 pts.
6. **3:40–4:00** Trace + provenance close: "every number came from a call you can read." Mention proactive alert banner if seconds remain.

Q&A prep: where each number comes from; what's mock (README table); no-internet behavior; how memory persists; why in-event-generated crop.db is rules-clean.

## 6. Communication protocol

- Each instance logs to its own LOG per CLAUDE.md. Cross-boundary need = say aloud + log.
- Every sync: 5 min — read other's log since last sync, run end-to-end, agree next block.
- Codex credits: use as a second pair of hands INSIDE each person's own territory (tests, boilerplate, CSS). Never point two agents at the same directory.
