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
