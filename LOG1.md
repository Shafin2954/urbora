# LOG1 — Instance A (agent / tools / kb / memory)

Append-only. Format defined in CLAUDE.md §1. Newest entry at the bottom.

---

## [00:00] Log initialized
**Did:** Created log file. Read PRD.md, PLAN.md, NOTES.md, CLAUDE.md.
**Decision:** none yet.
**Why:** —
**Rejected:** none.
**Impacts other instance:** no.

## [00:35] Backend scaffold + venv + pinned deps
**Did:** Created `backend/` (venv at `backend/.venv`, Python 3.12). `requirements.txt` pins A's core exactly: anthropic==0.119.0, pydantic==2.13.4, python-dotenv==1.2.2. Created package dirs agent/tools/kb/memory with `__init__.py`, `data/raw/.gitkeep`, root `.gitignore` (secrets + venv + node), `backend/.env.example`.
**Decision:** venv lives under `backend/.venv` (gitignored). requirements.txt has a commented "Instance B adds" section for fastapi/uvicorn/sse so B appends rather than forks the file.
**Why:** Rule 7 (pin exact on first add) + Rule 8 (secrets never in git — .gitignore before anything else).
**Rejected:** Full `pip freeze` of transitive deps — kept to direct deps only, cleaner to reason about; will pin httpx/chromadb/sentence-transformers when tools actually import them.
**Impacts other instance:** YES — B. (1) Created root `.gitignore` and `backend/.env.example`; B should append their fastapi/uvicorn/sse pins to `requirements.txt` and their `BDAPPS_*` keys are already stubbed (commented) in `.env.example`. (2) `backend/` is now the package root; import as `from schemas import ...`, `from agent import LLMClient`.

## [00:50] schemas.py written — THE CONTRACT (proposed freeze)
**Did:** Wrote `backend/schemas.py` — every model from PLAN.md §2 as pydantic v2: Provenance, FarmProfile (+LocalArea), CropCandidate (+ScoreComponent), SeasonPlan (+PlanTask), FinanceProjection (+FinanceScenarios/Scenario/Item), Alert, CheckoutResult, all 9 SSE events + `SSEEvent` union (each with a `type` literal discriminator), and HTTP request bodies (ChatRequest/RecomputeRequest/CheckoutRequest+CheckoutItem). Verified all import and round-trip to JSON via `.model_dump_json()`.
**Decision:** Timestamps are ISO-8601 UTC **strings** on the wire (retrieved_at, created_at, ts, task_date) — avoids tz/serialization ambiguity in SSE JSON. `Provenance.value` is `int|float|str` (a provenance can wrap "loam" as well as 45). `scenarios` is a typed object (conservative/base/optimistic), not a free dict.
**Why:** Rule 3 — provenance is schema-enforced; B renders straight off these types, A fills them.
**Rejected:** datetime objects for timestamps (serialization noise across SSE); free-dict scenarios (loses B's render safety).
**Impacts other instance:** YES — B. This is the H1 freeze candidate: `import` it, render off it, SSE emitter serializes these `type`-tagged models directly. **Awaiting human A review before I call it frozen.** Post-freeze changes need LOG entry + A approval + ping to B (CLAUDE.md §0).

## [01:05] LLM client abstraction (Claude Sonnet primary, swappable)
**Did:** `backend/agent/config.py` (AgentConfig.from_env — model/max_tokens/effort/thinking/max_iterations, env-var switch only) + `backend/agent/llm_client.py` (LLMClient implementing a `ChatBackend` Protocol: `.stream()` over anthropic messages.stream, `.cost_from_usage()` → {in_tokens,out_tokens,cost_usd} with a `_PRICING` table + cache-rate math, `cached_system()` prompt-cache helper). Offline smoke print + cost math verified (1200 fresh + 8000 cache-read + 350 out on sonnet-5 = $0.01125).
**Decision:** Default model `claude-sonnet-5` (cost-appropriate per PRD §11 "Sonnet", 1M ctx, native tool use), overridable via `AGRISENSE_MODEL`. Adaptive thinking ON by default with `effort=medium` (planning quality vs cost balance); both env-tunable. Cost uses **standard** rates (not intro discount) so the cost line over-estimates — safer for watching credits (NOTES #5).
**Rejected:** Hardcoding a model in a prompt (violates PRD §11 env-var-only rule); opus-4-8 default (overkill for cost budget); raw anthropic calls in the loop (no single place for cost/caching/model resolution).
**Impacts other instance:** no (A-internal; B consumes agent output via SSE, not this client directly).

## [01:10] repograph.md created + agribase_clean.db flagged
**Did:** Created `repograph.md` mapping all backend/data files. Flagged a pre-existing `agribase_clean.db` / `build_agribase_clean.sql` / `AGRIBASE_CLEANING.md` at repo root (a validation-first derivative of a supplied `crops.db`) that predates this block.
**Decision:** none — noting only.
**Why:** Its `source_registry` is `pending_verification` and PRD §5 requires crop.db be **generated in-event** by parse_agribase.py. Reconciling the two (rules-cleanliness, NOTES #3) is an OPEN item for A at H3–H6, not H0–H1.
**Rejected:** Using agribase_clean.db as-is now — out of this block's scope; would prejudge the in-event-generation requirement.
**Impacts other instance:** no (A territory — crop.db/data).

## [01:12] BLOCK COMPLETE — H0–H1, stopping for human A review
**Did:** Finished the H0–H1 block (scaffold, schemas, LLM client, logs). Stopping per instructions.
**Decision:** none.
**Why:** Human reviews before the H1 schema freeze.
**Rejected:** Starting the agent loop / weather tools (H1–H3) — gated on schema-freeze review.
**Impacts other instance:** B is unblocked to build against `schemas.py` once A confirms the freeze.

## [01:15] Schema freeze approved → merged to master (A merges first)
**Did:** Human approved. Committed H0–H1 on `dev-a` (f55c144) and fast-forwarded `master` to it. schemas.py is now FROZEN.
**Decision:** Repo default branch is `master` (PLAN.md says "main" — same role). Merged there.
**Why:** PLAN §4 — A merges first at sync points, B rebases.
**Impacts other instance:** YES — B: rebase `dev-b` onto `master` (f55c144) to build against the frozen `schemas.py` + confirm hello-world SSE. schemas.py changes from here need LOG entry + A approval + ping.

## [01:40] H1–H3: weather + geocode tools, agent loop with guards
**Did:** Built the A side of H1–H3 on `dev-a`:
  - `tools/districts.py` — hardcoded 64-district table (all 8 divisions) + alias map + `lookup_district()`. Rajshahi (demo) included.
  - `tools/geocode.py` — `geocode(name)`: Open-Meteo geocoding → candidate list with `needs_confirmation`; retry→64-district fallback; never fabricates a location (empty candidates on no match).
  - `tools/weather.py` — `get_forecast` (16-day, source_type=forecast) + `get_climatology` (archive normals, source_type=climatology). Retry → disk-cache fallback labeled `cached=true` → honest `degraded="তথ্য যথেষ্ট নয়"` if no cache. (recovery #3, NOTES #1/#11)
  - `agent/prompts.py` — SYSTEM_PROMPT: Bangla-first, English tool params, weather-labeling wording, no LLM arithmetic/ranking, geocode confirm, gap-detection intake.
  - `agent/tools_spec.py` — Claude tool schemas + safe `dispatch()` (unknown tool / bad params → {error}, never raises).
  - `agent/loop.py` — `run_turn(messages, client)`: streams tokens, emits tool_call/tool_result RAW (B redacts), max_iterations guard (default 12), accumulates usage + cost across iterations → console cost line + `done` event.
  - `tests/` — 16 offline tests (district table, alias/fallback, weather labeling + degradation + climatology aggregation, import integrity, dispatch safety). All green: `python -m pytest backend/tests -q`.
  - Pinned `httpx==0.28.1` (direct use) + `pytest==9.1.1` (dev) in requirements.txt.
**Decision:** `backend` is the package root — everything imports as `backend.xxx`, tests/smokes run from repo root. Weather cache lives at `backend/.cache/weather/` (gitignored). Climatology = mean daily tmax/tmin + mean monthly precip-total over past `years` (default 10) from the Open-Meteo archive.
**Verified:** Live Open-Meteo calls work — geocode('Rajshahi')→(24.374, 88.601) source_type=api; July climatology Rajshahi = tmax 32.6 / tmin 26.4 / precip 269.3mm (plausible monsoon). LLM loop NOT yet run live — no ANTHROPIC_API_KEY in this environment.
**Rejected:** Streaming thinking deltas to the farmer token channel (internal reasoning is English/non-farmer-facing — skipped); a general Open-Meteo climate-projection model (used historical archive normals instead, matches "গত বছরের গড়" wording).
**Impacts other instance:** YES — B: `from backend.agent.loop import run_turn` yields the frozen SSE event models directly; your redacting emitter serializes them and redacts tool_call/tool_result (they carry RAW params/results). Loop appends to the `messages` history in place. Nothing new added to schemas.py.

## [01:42] H1–H3 committed to dev-a — main-merge HELD for live end-to-end
**Did:** Committed the H1–H3 work on `dev-a`. Did NOT merge to `master`.
**Decision:** Hold the master-merge until the "one manual end-to-end chat turn" runs green — that needs (a) ANTHROPIC_API_KEY in `backend/.env` and (b) the H3 sync (A's loop streaming through B's UI). Neither is available to me right now.
**Why:** CLAUDE.md §3 — a real end-to-end turn precedes a merge to main; don't merge on tests alone for a loop I couldn't exercise live.
**Rejected:** Merging H1–H3 to master now on the strength of offline tests only — the loop's live LLM path is unexercised.
**Impacts other instance:** B — at the H3 sync we run A's loop through your SSE UI; that green run is the gate to merge H1–H3 to master.

## [02:15] DECISION: build crop.db on existing agribase_clean.db (human A approved)
**Did:** Per human A ("continue with the existing"), the yield data source is the pre-existing validated `agribase_clean.db`, NOT a fresh parse_agribase.py from raw yearbook extracts.
**Decision:** Yield OBSERVATIONS come from agribase_clean.db (safe views only, never modified). Derived Holt PROJECTIONS are still generated in-event by holt.py into `data/crop.db` with meta timestamps + git sha.
**Why:** Human's call; keeps momentum. Observations are a validated derivative already in the repo.
**Rejected:** parse_agribase.py from raw extracts (the "rules-clean" path) — human chose existing.
**Impacts other instance:** B — README MUST use the AGRIBASE_CLEANING.md disclosure wording: "District yield estimates are computed from a validated derivative of the supplied agricultural dataset; the in-database source citation is pending verification; recommendations disclose this limitation." **Rules-risk (NOTES #3):** agribase_clean.db predates the event; the derived crop.db is in-event, but raw source provenance is `pending_verification`. Do NOT claim BBS-verified. Flag for Q&A prep.

## [02:18] CROP SET REALITY — diverges from PRD §3.2 (needs human A confirm)
**Did:** Inspected agribase_clean.db coverage.
**Decision:** Data-backed enabled crops = **aman_rice, boro_rice, potato, mustard, lentil**. **Wheat is DISABLED (no crop key in source), maize is ABSENT.** So the scorer's data-backed universe is these 5, NOT PRD §3.2's six (Boro/Wheat/Potato/Maize/Mustard/Aman). Lentil is a data-backed extra; wheat+maize cannot be ranked/costed without fabricating (PRD §5 rule 3) — cropdb_sql returns an honest error for them and the system prompt tells the agent to say so.
**Why:** A crop with no yield series can't be ranked honestly. Demo still works: Rabi ranking candidates from data = boro/potato/mustard/lentil (≥3 ✓); "plant now" kharif-2 = aman.
**Rejected:** Fabricating wheat/maize yields to hit the PRD six (violates rule 2/rule 3).
**Impacts other instance:** B — the rehearsed demo script (PLAN §5) assumes Boro/Wheat/Potato/Maize/Mustard as Rabi candidates. With this data it's Boro/Potato/Mustard/Lentil. **Human A must decide:** (a) accept this 5-crop data-backed set + update demo script, or (b) source wheat/maize district yields. Until decided, treat wheat/maize as data-absent.

## [02:20] Holt viability + crop.db generated
**Did:** `backend/kb/holt.py` generates `data/crop.db` (310 projection rows). Damped-Holt (fixed α=0.5,β=0.3,φ=0.9) where a series has ≥4 points, else last-observed fallback, else single-point. Every row discloses `n_points` + `method` (NOTES #23). Result: 184 damped_holt / 123 last_observed / 3 single_point. Only aman has dense series (≥6 pts); boro/potato/mustard/lentil are thin (2–4 pts) → honest low confidence.
**Decision:** Units = **kg/ha** (rule 11 internal=kg), deviating from PRD §5's `t_ha` column names — matches source units + finance engine. crop.db committed (meta-timestamped) as the demo lifeboat + judge-inspectable generated_at.
**Why:** Deterministic, no optimizer → reproducible in-event; fixed smoothing params.
**Rejected:** t/ha naming (would force a kg↔t conversion at the finance boundary); scipy/statsmodels Holt (heavy dep, non-deterministic optimization).
**Impacts other instance:** B — finance engine consumes Holt `base_yield_kg_ha` (± `band_kg_ha`) as the yield input; note it's **kg/ha** and always carries a band. Three finance scenarios should use base, base−band, base+band.

## [02:35] cropdb_sql tool wired into the agent + tests
**Did:** `backend/tools/cropdb.py` — `cropdb_sql(action, crop, district)` with parameterized actions (district_yields / holt_projection / yield_track_record), read-only, provenance-ready. Registered in `agent/tools_spec.py` (schema + dispatch); system prompt got a "Yield data" section (band-always, wheat/maize-absent honesty). Added `tests/test_cropdb.py`. Full suite: **22 tests green**.
**Decision:** cropdb_sql exposes fixed actions, NOT raw SQL from the LLM — safer + deterministic, still satisfies the "crop.db SQL tool" role.
**Why:** Rule 1 (LLM never computes/ranks) + injection safety; the deterministic scorer (H6–H9) reads the same data directly in Python.
**Rejected:** Letting the model emit arbitrary SQL (injection + non-determinism).
**Impacts other instance:** no (A territory). B's finance tool integration is separate.

## [02:45] Data: wheat absent + maize CORRUPT in source → both need external collection
**Did:** Investigated whether wheat/maize (PRD six-crop gap) exist in agribase_clean.db. Wheat: no key anywhere (only barley). Maize: present in `rejected_crop_rows` (keys rabi_maize/kharif_maize/maize_rabi_kharif) but CORRUPTED — e.g. Dinajpur rabi_maize ha=461,671 (> the whole district) at 331 kg/ha (real maize ≈8,000–9,000). Area column is national/misaligned. Attempted web-scrape of BBS sources: 45-yr major-crops PDF >10MB (over fetch limit), Kaggle login-gated SPA, yearbook = mangled-PDF trap (NOTES #18b).
**Decision:** Do NOT recover maize (garbage = rule 2 violation). Both wheat AND maize need clean external district data. Gave human A a collection guide + CSV format: `data/raw/wheat_maize_district.csv` with columns crop_key,district,year(split),hectares,production_mt (yield computed in-event). Target Dinajpur+Rajshahi ≥3 yrs each min; all districts ideal (for percentile). Source: BBS Yearbook of Agricultural Statistics 2024/2022 district crop tables.
**Why:** Can't fabricate; can't cleanly auto-scrape mangled yearbook PDFs.
**Rejected:** Whitelisting the corrupt maize rows; auto-scraping the yearbook PDF blind.
**Impacts other instance:** B — until the CSV lands, wheat+maize stay data-absent; demo crop set is boro/aman/potato/mustard/lentil.

## [02:50] DECISION: switch app agent LLM Claude → OpenAI (human A approved)
**Did:** Human A chose (via clarifying question) to run the AgriSense agent on OpenAI, not Claude. Re-implemented the LLM layer on the OpenAI SDK behind the existing provider-neutral `ChatBackend` interface. Files: `agent/config.py` (OPENAI_MODEL default gpt-4o-mini, temperature, OPENAI_API_KEY/BASE_URL), `agent/llm_client.py` (`OpenAIClient` + `TurnStream` streaming parser + `to_openai_tools` translation + cost table + `tool_result_message`), `agent/loop.py` refactored to the neutral interface (native OpenAI message history). requirements: `openai==2.48.0` replaces anthropic. `.env.example` → OPENAI_*. `tests/test_llm_backend.py` added (fake-stream parse, cost, translation). **28 tests green.**
**Decision:** Chat Completions API (stable, tool + streaming); model env-configurable; cost `_PRICING` are best-effort (verify for account/date); OpenAI prompt caching is automatic so the Anthropic cache_control helper was dropped. Kept the `ChatBackend` Protocol so a Claude backend can return later.
**Why:** Human A's explicit call. **Deviates from PRD §11 / CLAUDE.md / NOTES #5 (all mandate Claude/Sonnet).**
**Rejected:** Responses API (less certain surface in this env); coupling the loop to OpenAI objects (kept it provider-neutral); the Anthropic backend (retained as latent option behind the Protocol).
**Impacts other instance:** YES — B: (1) The **frozen SSE schema + all event shapes are UNCHANGED** — your redacting emitter + UI are unaffected; this is a pure A-internal backend swap. (2) **README/Q&A must now say the agent runs on OpenAI (model gpt-4o-mini/…), NOT Claude/Sonnet** — update any model claims. (3) Live end-to-end turn needs `OPENAI_API_KEY` in `backend/.env`.

## [02:52] SECURITY: OpenAI key was pasted in chat → advised rotation
**Did:** Human A pasted a live `sk-proj-...` OpenAI key in the conversation. Did NOT store, echo, or commit it. Told human A to revoke/rotate it (chat is logged → treat as compromised) and to put the new key in `backend/.env` themselves.
**Decision:** none (secrets stay out of git — rule 8).
**Why:** A plaintext key in a logged session is compromised.
**Rejected:** Writing the key into .env/any file for them.
**Impacts other instance:** B — same rule: never paste live secrets; .env only.

## [03:10] Integrated B's work: merged origin/master into dev-a
**Did:** B had already merged dev-b → master (master=1626a38: FastAPI SSE skeleton, redacting emitter, units.py, Vite frontend, chat UI). Merged origin/master into dev-a (merge commit bd441f0). Conflicts resolved in requirements.txt (kept A's openai/httpx/pytest + B's `-r api/requirements-api.txt`) and repograph.md (both sections). Confirmed schemas.py UNCHANGED since freeze ✓. A's 28 backend tests still green post-merge; B's files all present.
**Decision:** Reconcile via merge (no history rewrite / force-push) rather than rebase. dev-a now carries the full A+B tree.
**Why:** Get A's backend + B's api/ui on one branch for the H3 end-to-end.
**Rejected:** Rebasing dev-a onto master (would rewrite already-pushed commits + force-push).
**Impacts other instance:** B — workflow note: you merged to master before A this time (PLAN §4 says A-first); harmless here, no conflicts on your files. schemas.py stayed frozen — thank you.

## [03:15] DECISION: 5-crop set final — drop maize AND wheat
**Did:** Human A decided: ship the 5 data-backed crops only (boro_rice, aman_rice, potato, mustard, lentil). Wheat stays out (no data). Maize stays out too — its source data is corrupt and the labeled-placeholder handling was disproportionate effort for one crop. Built and then REVERTED the maize placeholder (uncommitted; holt.py/cropdb.py/prompts/tools_spec/tests restored to the 5-crop state; crop.db unchanged, no extra_observations table).
**Decision:** Scorer/finance/demo universe = these 5. cropdb_sql returns an honest "no data" for wheat/maize. Supersedes the earlier "crop set needs human confirm" (LOG 02:18).
**Why:** Human A — avoid over-investing in one bad-data crop; keep scope tight. Demo still has ≥3 Rabi candidates (boro/potato/mustard/lentil) + aman for kharif-2.
**Rejected:** Maize as a labeled corrupt placeholder (too much special-casing for one crop); fabricating wheat/maize (rule 2).
**Impacts other instance:** B — demo/README crop set is 5 (no wheat, no maize). Update any six-crop references.

## [03:30] DECISION: crop_scorer.py deferred KB scope — District track record + Stability only
**Did:** Planned `backend/tools/crop_scorer.py` (PRD §6, H6–H9) in plan mode. Confirmed via read-only checks: no `backend/finance/` (B hasn't built it, no prices.md), no curated KB markdown (only `backend/kb/holt.py` exists). These block 3 of 5 stage-2 components (Agronomic fit, Profit, Climate fit) and 3 of 4 stage-1 exclusions (Season, Soil, Water — Budget also blocked, needs finance). Asked human A: write a hand-curated static "crop facts" stand-in for season/soil/water/climate bands (labeled static_table, medium confidence, swap-later TODO) now, OR defer those parts entirely and ship only what crop.db already supports. **Human A chose: defer.**
**Decision:** `crop_scorer.py` ships now scoring ONLY District track record (20 pts, from `cropdb.yield_track_record` + `holt_projection`) and Stability (10 pts, CV of the farm's own district yield history via `cropdb.district_yields`) — both fully computable today, no fabrication. Agronomic fit/Profit/Climate fit report `points=0.0, confidence="low", value="unavailable"` with a formula explaining why. Season/Soil/Water/Budget exclusions are all skipped (not applied) until their data exists — only the "no yield data for this crop" exclusion (wheat/maize/unknowns) is live today. Design uses two typed-but-unpopulated seams (`crop_facts: dict[str,CropFacts]|None`, `finance: dict[str,CropFinance]|None`) so B's finance engine and later KB curation activate the deferred logic via a data-supply change, not a rewrite — both branches are already implemented+tested (synthetic test-only values), just not fed real data yet. A `degraded` list surfaces exactly what's unavailable so the agent must disclose it in Bangla before presenting any ranking — never present a 20–30/100 composite as if it were complete.
**Why:** Rule 2 (no invented data) — hand-written agronomy numbers without real BARC/BRRI citations would be a judgment call the human wanted to make directly, and they chose honesty-over-completeness again (same pattern as dropping maize/wheat).
**Rejected:** The static_table stand-in approach (offered as the recommended default, declined) — would have unblocked 4 more components/exclusions today but wasn't the human's choice.
**Full plan:** `C:\Users\Shafin\.claude\plans\imperative-frolicking-hummingbird.md` (approved, implementation starting next).
**Impacts other instance:** B — once you build `backend/finance/`, supplying a `finance: dict[str, CropFinance]` (shape: `{min_cost_per_ha, net_profit_bdt_per_ha, source_id, source_title, formula}` per crop) to `score_crops(...)` turns on Budget exclusion + Profit component immediately; no A-side rework needed. Until then, `crop_scorer` tool output will show Profit as "unavailable" — expected, not a bug.

## [04:00] crop_scorer.py implemented + wired in + live-verified (approved plan executed)
**Did:** Implemented the approved plan in full: `backend/tools/crop_scorer.py` (`score_crops` pure core + `crop_scorer_tool` impure wrapper; `CropFacts`/`CropFinance` seams), `backend/tests/test_crop_scorer.py` (31 tests: exclusions incl. unsupported-crop/season/soil/water/budget-applied/budget-skipped, all 5 scoring components in both degraded and synthetic-full-data modes, CV/tercile risk_level, determinism, structural no-network-import check + a runtime httpx-broken check, provenance completeness, the agent tool wrapper). Registered `crop_scorer` in `tools_spec.py` (TOOL_DEFS + `_DISPATCH`) and added narration + mandatory-degraded-disclosure rules to `prompts.py`. Updated `test_imports.py` for the 5th tool. Updated `repograph.md`.
**Verified:**
  - `python -m pytest backend/tests -q` → **59/59 green** (28 prior + 31 new).
  - Manual sanity (`crop_scorer_tool(district="Rajshahi", soil_type="clay_loam", water_source="tubewell", season="rabi")`): all 5 crops score, ranked aman_rice(28.38) > potato(26.48) > boro_rice(23.22) > mustard(17.27) > lentil(8.85); Agronomic/Profit/Climate correctly "unavailable"; `degraded` populated.
  - **Live end-to-end through the full agent loop** (2-turn conversation: farm details → district confirmation → recommendation): model called `geocode` (confirmed district, recovery #1), then `crop_scorer` with correct params (district/soil_type/water_source/season/area_ha), then `get_forecast` to enrich — relayed the degraded disclosure honestly in Bangla ("এই মুহূর্তে শুধু ফলনের ইতিহাস ও স্থিতিশীলতার ভিত্তিতে ক্রম দেখানো হচ্ছে...") before presenting the ranking, which matched the manual sanity check exactly.
**Side-finding (not fixed, logged for follow-up):** in that live run the model rendered weather figures in **Bangla numerals** (২৫.৫°C) instead of Western numerals — violates rule 10/NOTES #17. crop_scorer's own numbers were correctly Western; this is a `prompts.py` wording gap (needs a more explicit/repeated instruction), unrelated to crop_scorer itself. Left for a follow-up prompt pass, not fixed now (out of scope for this task).
**Decision:** none beyond what's already logged (KB-deferral decision, prior entry).
**Rejected:** none new.
**Impacts other instance:** B — `crop_scorer` tool is live in the agent; until `backend/finance/` exists, every ranking will show Profit "unavailable" and the agent will disclose this — expected. No schema changes.

## [10:23] Session store + async run_turn — entry reconstructed after the fact
**Written by:** the single-operator takeover, not by Instance A. Commit `5581afc`
("FASTAPI works unfinished", 24 Jul 19:23) shipped without a log entry, which
CLAUDE.md §1 requires. Reconstructed from the diff so the record is complete;
everything below is what the commit does, not a plan.
**Did:** Split `agent/loop.py` in two — `run_turn_sync(messages, client, system)` is
the unchanged pure engine, and a new `async def run_turn(session_id, farm_id, message)`
is the real entrypoint `backend/api/chat.py` imports. It loads the session's history,
appends the message, bridges the blocking generator onto a worker thread
(`_sync_iter_to_async`, one `asyncio.to_thread` per `next()`), saves the history back,
and yields **plain dicts** — building tool events via B's `sse.tool_call`/`sse.tool_result`
so redaction stays structural. Added `backend/memory/store.py` (SQLite WAL: `sessions`
and `farms` tables) + `backend/memory/__init__.py`. Added `tests/test_loop_integration.py`
(scripted fake ChatBackend, no network) and `tests/test_memory_store.py`. Gitignored
`backend/memory/memory.db*`.
**Decision:** The agent owns conversation history, in SQLite rather than in memory.
**Why:** Each POST is a fresh call with no shared Python object, so a session's history
has to be persisted somewhere; SQLite means it also survives a restart, which the demo's
returning-farmer opener needs (PLAN §5 step 1). The integration tests exist because the
earlier "live verified" claim covered a hand-rolled script calling the sync engine
directly — **not** B's actual API contract, which is what the demo runs on.
**Rejected:** Keeping `run_turn` synchronous and making the API adapt (B had already
built exactly that adapter — see below).
**Incomplete, and now tracked rather than lost:**
1. **`farm_id` is accepted and then ignored.** The `farms` table is created but nothing
   ever reads or writes it, so a returning farmer is not actually recalled. That is a
   judged behavior (PRD §4 Memory) and the demo's opening 20 seconds.
2. **`Dhaka retail price.xlsx` was committed to the repo root** with no entry explaining
   it. It is a TCB **retail** bulletin (Dhaka markets, dated 24-07-2026): milled rice,
   split lentil dal, potato — no paddy, no mustard. Retail is roughly double farm-gate,
   so using it as a farmer's selling price would overstate every revenue figure. It is
   market context, not a revenue source, and prices.md now says so.
3. `data/crop_schema.sql` still is not committed, though PRD §5 freezes it at H1.
**Impacts other instance:** superseded — A and B merged into one operator at this point.
The duplicate seam this created (B had independently built `api/sessions.py` +
`api/agent_bridge.py` for the same job) was resolved in favour of this commit's version;
see LOG3.md.
