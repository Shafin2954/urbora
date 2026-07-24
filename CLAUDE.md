# CLAUDE.md v2 — Rules for Claude Code (TeamFixeth_AgriSense)

Two Claude Code instances work this repo in parallel: Instance A (agent/tools/kb/memory, human A) and Instance B (api/frontend/finance/payments, human B). Codex may assist inside a person's own territory only. Read PRD.md, PLAN.md, NOTES.md before your first task. Re-read NOTES.md when anything behaves strangely — your bug is probably listed.

## 0. Identity and boundaries

- You are Instance A or Instance B; the human tells you which at session start. If they didn't, ask.
- Directory ownership: PLAN.md §1. **Never create, edit, or delete files outside your owned directories.** Cross-boundary need → LOG entry + human relays. No exceptions, including "obvious one-line fixes."
- `backend/schemas.py`: owned by A. After the H1 freeze, changes require a LOG entry with reasoning, human A's approval, and a heads-up to B before merge.
- Never point two agents (Claude Code, Codex) at the same directory simultaneously.

## 1. Logging protocol (mandatory)

- Instance A → `LOG1.md`. Instance B → `LOG2.md`. Append-only; never rewrite past entries.
- One entry per unit of work: feature done, decision taken, bug found/fixed, dependency added, approach abandoned.
- Written for humans: a tired teammate at 4am understands it in 20 seconds. Plain language.
- Write into repograph.md after creating any entry saying which file/folder is about what, so that exploration s easier for the other instance. If you don't know, say so.
- save the explored data whenever possible to remove unnecessary exploration and token usage.

Format:

```
## [HH:MM] <short title>
**Did:** what changed, which files.
**Decision:** what was decided (if any).
**Why:** one or two plain sentences.
**Rejected:** alternatives considered and why not. "none" if none.
**Impacts other instance:** yes/no — if yes, what they need to know.
```

- Decisions without code (e.g., "1 bigha = 33 decimal convention") get entries too. Silent decisions are the enemy.
- Abandoned an approach? Log it with the time it cost. That entry saves the other person from repeating it.

## 2. Hard technical rules

1. **The LLM never does arithmetic and never ranks crops.** Money/yield/dose/unit math → `backend/finance/` or `units.py`. Crop ranking → `crop_scorer.py` (deterministic, PRD §4). The model narrates tool outputs. A prompt letting the model compute or rank = bug; fix and log.
2. **No invented data.** Weather from Open-Meteo responses. Yields from crop.db. Doses from KB retrieval. Source unavailable → degrade honestly in the agent's reply ("তথ্য যথেষ্ট নয়") — never fabricate.
3. **Provenance is mandatory.** Every number reaching the UI carries a Provenance object (schemas.py). A number without provenance must not render. This is schema-enforced, not prompt-hoped.
4. **Weather labeling.** Every weather-derived claim carries `source_type: forecast | climatology`. Climatology is a planning assumption, never a prediction — wording rules in PRD §6 Tier0.2.
5. **Every tool call is traced, and traced redacted.** New tools must emit `tool_call`/`tool_result` SSE events with raw params/results. The emitter (B) redacts: password/appId/key/token/secret → `***`, phone/subscriberId → last 3 digits. Untraced tool = doesn't exist for judges. Unredacted trace = security bug.
6. **In-event artifacts.** parse_agribase.py, holt.py, ingest.py are written and run during the event; crop.db and the Chroma index are generated in-event with timestamps in a meta table. Never copy application code from prior projects — rewrite fresh. Raw public data and pre-cached third-party models/wheels are fine.
7. **Pin all dependencies** exactly on first add.
8. **Secrets never touch git.** `.env` only; `.env.example` current; check diffs before push.
9. **Agent loop guards:** max 12 iterations/turn; token usage + cost per turn in the `done` event and console.
10. **Bangla-first:** farmer-facing text defaults to Bangla, mirrors user language. Internal reasoning, tool params, RAG queries (always English), trace, code comments: English. Western numerals in tables/computed values.
11. **Units:** internal = hectares/kg only; local units exist at intake/display edges via units.py. 1 bigha = 33 decimal = 0.1338 ha.
12. **Tests where they matter:** finance engine, units.py, crop_scorer.py, trace redactor. Run before every merge to main. No coverage theater on UI.
13. **Simulator honesty:** bdapps simulator matches documented shapes exactly, labeled `mode:"simulator"` in code, UI, README. Never present simulated as live. Checkout always has a confirmation step before charging.
14. **Scope gate:** [GATED] items in PRD §6 may not be started until the `tier0-stable` tag exists AND main is green. Until then they are LOG proposals only. Tier 0 > Tier 1 > gated, always.

## 3. Workflow rules

- A on `dev-a`, B on `dev-b`. Merge to `main` only at sync points (PLAN.md §3); A merges first, B rebases.
- Small commits, imperative messages.
- Before merging to main: run the test suite (rule 12) + one manual end-to-end chat turn. Broken main forbidden after H12.
- Tag `tier0-stable` at H15. Late-night experiments must never make the tag unreachable.
- Check PLAN.md before starting anything; off-schedule ideas go to the log as proposals.

## 4. When in doubt

- Uncertain cross-boundary interface → ask the human, don't guess.
- Uncertain scope → it's gated; log the proposal.
- Uncertain whether data is real → treat as mock and label, or remove.
- Stuck >25 min on one bug → log, tell the human, switch tasks. The timeline outranks any single bug.
