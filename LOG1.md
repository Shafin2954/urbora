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
