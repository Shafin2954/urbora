# PLAN — Parallel Execution (TeamFixeth_AgriSense)

Two people, two Claude Code instances, one repo. Zero blocking by design.

## 1. Ownership map (hard boundaries)

```
TeamFixeth_AgriSense/
├── backend/
│   ├── agent/        ← A   (agent loop, prompts, orchestration)
│   ├── tools/        ← A   (weather, geocode, rag_query, agribase_sql, soilgrids)
│   ├── kb/           ← A   (curated markdown docs + ingest script + Chroma store)
│   ├── memory/       ← A   (farm profile, conversation persistence, SQLite)
│   ├── api/          ← B   (FastAPI routes, SSE stream, session plumbing)
│   ├── finance/      ← B   (pure-function engine + tests)
│   ├── payments/     ← B   (bdapps client + simulator fallback)
│   ├── units.py      ← B   (bigha/katha/decimal/acre ↔ hectare; maund ↔ kg; tested)
│   └── schemas.py    ← A owns, B imports. Changes ONLY with log entry + ping.
├── frontend/         ← B   (Vite React PWA: Chat, Plan, Finance, Trace views)
├── data/
│   └── agribase.db   ← A   (read-only artifact)
├── PRD.md PLAN.md NOTES.md CLAUDE.md LOG1.md LOG2.md README.md
```

Rule: never edit outside your directories. Need a change there? Ask the other person or write it in your log and ping.

## 2. The contract (freeze at H1)

Everything crossing the A/B boundary lives in `backend/schemas.py`. Freeze these shapes at H1; after that, changes are announced, logged, and versioned.

```python
# --- API ---
# POST /api/chat        {session_id, farm_id|null, message}  → SSE stream
# GET  /api/farms       → [FarmProfile]
# GET  /api/plan/{farm_id} → SeasonPlan | 404
# POST /api/finance/recompute {farm_id, overrides: {field: value}} → FinanceProjection
# POST /api/checkout    {farm_id, mobile, amount, items} → CheckoutResult

# --- SSE event types (one JSON per event) ---
# {type:"token",        text}
# {type:"tool_call",    id, name, params, ts}
# {type:"tool_result",  id, name, result_raw, ts}          # raw values, judges must see
# {type:"plan_update",  plan: SeasonPlan}
# {type:"finance_update", finance: FinanceProjection}
# {type:"done",         usage:{in_tokens, out_tokens, cost_usd}}
# {type:"error",        message}

# --- Core models (pydantic) ---
# FarmProfile: farm_id, name, district, lat, lon, area_ha, area_local:{value,unit},
#              soil_type, water_source, budget_bdt, season, created_at
# CropCandidate: crop, suitability_score, water_need, risk_level, est_profit_bdt, reasons:[str]
# SeasonPlan: farm_id, crop, tasks:[{date, task, category, details, depends_on_weather:bool, source}]
# FinanceProjection: items:[{name, qty, unit, unit_cost, total}], total_cost,
#                    expected_yield_kg, price_per_kg, revenue, net_profit, roi_pct,
#                    breakeven_yield_kg, assumptions:[{name, value, source}]
# CheckoutResult: status, trx_id|null, mode:"live"|"simulator", receipt_sms_sent:bool, raw
```

Agent (A) fills these models; UI (B) renders them. Finance engine (B) computes FinanceProjection from inputs the agent passes as a tool call — A calls B's function as a tool, never computes money itself.

## 3. Hour-by-hour

| Hours | A (agent/data) | B (api/ui/finance/payments) | Sync |
|---|---|---|---|
| H0–H1 | Scaffold backend, venv, pin deps. Draft schemas.py. Claude client abstraction. | Scaffold Vite PWA (SW disabled in dev). FastAPI skeleton. **bdapps portal: create app, get creds, whitelist venue IP (`curl ifconfig.me`).** | **H1: freeze schemas. Confirm SSE hello-world reaches browser.** |
| H1–H3 | Agent loop working with one tool (get_forecast). Geocode tool with candidate-confirm. Max-iteration guard + cost logging. | Chat UI + SSE wiring + Trace panel rendering tool_call/tool_result live. units.py + tests. | H3: A's loop streams through B's UI. First end-to-end token. |
| H3–H6 | KB curation (**hard cap 3h**): 15–25 markdown docs, 5–6 crops. Chroma ingest. rag_query tool (English queries). agribase_sql tool. | Finance engine + unit tests (cost items, yield, revenue, ROI, break-even). Finance view with editable inputs → /recompute. Plan calendar view. | H6: agent retrieves KB + yearbook numbers in trace. |
| H6–H9 | Intake state machine (gap detection, Bangla follow-ups). Crop recommendation (weather × soil × season × agribase). | bdapps httpx client + simulator twin (identical shapes). Checkout UI. Bangla labels + Noto Sans Bengali. PWA manifest. | H9: intake → 3 ranked crops with real numbers. |
| H9–H12 | Season plan generation (KB calendars + climatology dates). Memory: save/load FarmProfile, resume sessions. | Mobile-first responsive pass. Trace bottom-sheet. Finance ↔ plan_update events wired. | **H12: TIER 0 END-TO-END RUN. Everything else waits until this passes.** |
| H12–H15 | Fix what H12 exposed. Explainability audit: every rec names inputs. | Fix what H12 exposed. Seed demo farm in DB. Error states (API down, geocode miss). | H15: Tier 0 stable. Commit tag `tier0-stable`. |
| H15–H18 | Scenario simulation tool (delegates to finance engine). Fertilizer/irrigation scheduler (BARC + Kc). Proactive forecast check on session open. | bdapps live test with Robi SIM (small real debit + SMS). If blocked → simulator confirmed + labeled. Trace polish. | H18: Tier 1 demo-able. |
| H18–H20 | Optional: SoilGrids tool. Pest/disease risk if green. | Optional: PWA install flow test on phone. Receipt rendering. | H20: feature freeze. |
| H20–H22 | README (real vs mock table, setup, tiers reached). | README sections (bdapps, finance, frontend). **Demo rehearsal ×2, timed to 4 min.** | Offline test: kill wifi, confirm app boots (weather gracefully degrades). |
| H22–H23 | **Code freeze.** Bugfix only if demo-breaking. Push. | Same. Push. Verify repo link + final commit before cutoff. | Submit link early; polish locally only. |
| H23–H24 | Buffer. Sleep in shifts if ahead. | Buffer. | — |

## 4. Git workflow

- Branches: `main` (demo-ready only), `dev-a`, `dev-b`.
- Merge to main every 2–3 hours at sync points, small commits, imperative messages.
- Merge order at each sync: A first (schemas authority), B rebases on main, then merges.
- Conflict rule: ownership map decides. Conflicts should only ever occur in schemas.py or README — both have a single owner per section.
- Tag `tier0-stable` at H15. If late-night work breaks things, demo from the tag.
- Never commit: `.env`, bdapps credentials, API keys. `.env.example` committed instead.
- Both push before cutoff even mid-polish. A late perfect commit = zero points.

## 5. Demo script (4 min, rehearsed twice)

1. **0:00–0:20** Open app as returning farmer (seeded). Agent greets in Bangla, recalls farm. → memory, instantly.
2. **0:20–1:20** New request: "এবার কী চাষ করব?" Agent asks one missing field, then chains: geocode → forecast → climatology → RAG → agribase → 3 ranked crops. Trace panel visibly filling. → agentic + grounding.
3. **1:20–2:20** Pick crop → dated season plan + finance table. **Change one input live** (e.g. area 2→3 bigha) → all numbers recompute. → accuracy.
4. **2:20–3:00** Scenario: "বৃষ্টি ৩০% কম হলে?" → revised numbers, not platitudes. → Tier 1.
5. **3:00–3:40** Checkout fertilizer order → bdapps balance → debit (real 2 BDT on Robi SIM) → Bengali SMS receipt shown on the phone. → 10 pts.
6. **3:40–4:00** Point at trace: "every number came from a call you can read." Close.

Q&A prep: where each number comes from; what's mock (answer from README table); what happens with no internet; how memory persists.

## 6. Communication protocol between A and B

- Each person's Claude Code instance logs to its own LOG file (see CLAUDE.md).
- Cross-boundary need = say it out loud + log entry. No silent edits in the other's directories.
- At every sync point: 5 min — read each other's log since last sync, run the end-to-end, agree next block.
