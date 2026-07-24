# CLAUDE.md — Rules for Claude Code (TeamFixeth_AgriSense)

Two Claude Code instances work this repo in parallel. Instance A (agent/tools/kb/memory, human: Person A) and Instance B (api/frontend/finance/payments, human: Person B). Read PRD.md, PLAN.md, NOTES.md before your first task. Re-read NOTES.md when anything behaves strangely — your bug is probably listed there.

## 0. Identity and boundaries

- You are Instance A or Instance B. The human tells you which at session start. If they didn't, ask.
- Directory ownership is defined in PLAN.md §1. **Never create, edit, or delete files outside your owned directories.** If you believe a change is needed in the other instance's territory, write the request into your LOG file and tell your human to relay it. No exceptions, even for "obvious one-line fixes" — that's how 3am merge conflicts happen.
- `backend/schemas.py` is owned by A. After the H1 freeze, any change to it requires: a LOG entry with reasoning, human A's approval, and a heads-up to B before merging.

## 1. Logging protocol (mandatory)

- Instance A writes to `LOG1.md`. Instance B writes to `LOG2.md`. Append-only — never rewrite or delete past entries.
- **Write an entry for every unit of work**: a feature completed, a decision taken, a bug found/fixed, a dependency added, an approach abandoned.
- Entries are for the humans. Write them so a tired teammate at 4am understands in 20 seconds what happened and why. Plain language. No jargon walls.

Entry format:

```
## [HH:MM] <short title>
**Did:** what changed, which files.
**Decision:** what was decided (if any).
**Why:** the reason, in one or two plain sentences.
**Rejected:** alternatives considered and why not. Write "none" if none.
**Impacts other instance:** yes/no — if yes, what they need to know.
```

- Decisions with no code (e.g., "chose fixed 1 bigha = 33 decimal convention") get entries too. Silent decisions are the enemy.
- If you abandon an approach after sinking time into it, log it honestly with the time cost. That entry saves the other person from repeating it.

## 2. Hard technical rules

1. **The LLM never does arithmetic.** All money, yield, dose, and unit math goes through `backend/finance/` or `backend/units.py` as tool calls. If you catch a prompt letting the model compute numbers, that is a bug — fix and log it.
2. **No invented data.** Weather numbers come from Open-Meteo responses. Yields come from agribase.db. Doses come from KB retrieval. If a real source is unavailable, degrade honestly (say so in the agent's reply) — never fabricate.
3. **Every tool call is traced.** Any new tool must emit `tool_call` and `tool_result` SSE events with raw params and raw results. A tool that doesn't appear in the trace panel doesn't exist for the judges.
4. **Pin all dependencies** exactly on first add. requirements.txt and package-lock.json are commitments.
5. **Secrets never touch git.** `.env` only; keep `.env.example` current. Check diffs before pushing.
6. **Agent loop guards:** max 12 iterations per turn; log token usage and cost per turn to console and the `done` event.
7. **Bangla-first:** farmer-facing text defaults to Bangla, mirrors the user's language. Internal reasoning, tool params, RAG queries, trace, and code comments: English. Western numerals inside tables and computed values.
8. **Units:** everything internal is hectares and kg. Local units exist only at the intake/display edges via `units.py`.
9. **Tests where they matter:** finance engine and units.py must have unit tests, run before each merge to main. Do not write tests for UI polish — tests are for math correctness (20 judged points), not coverage theater.
10. **Simulator honesty:** bdapps simulator responses must match the documented shapes exactly and be labeled `mode:"simulator"` in code, UI, and README. Never present simulated as live.

## 3. Workflow rules

- Branch: A on `dev-a`, B on `dev-b`. Merge to `main` only at sync points (PLAN.md §3), A merges first, B rebases.
- Commit small and often, imperative messages ("add climatology tool", not "stuff").
- Before merging to main: run the finance/units tests + one manual end-to-end chat turn. Broken main is forbidden after H12.
- At H15, tag `tier0-stable`. Late-night experiments must never make the tag unreachable.
- **All application code is written during the event window** (competition rule). The agribase.db is a pre-existing *data artifact* from a public source — data is allowed, code is not. Do not copy code in from prior projects; rewrite fresh. Public scaffolding (CLI generators, templates) is fine.
- Scope discipline: check PLAN.md before starting anything. If a task isn't in the current hour block, it goes to the log as a proposal, not into the code. Tier 0 before Tier 1 before Tier 2, always.

## 4. When in doubt

- Uncertain about a cross-boundary interface → ask the human, don't guess.
- Uncertain whether a feature is in scope → it isn't; log the proposal.
- Uncertain whether data is real → treat as mock and label it, or remove it.
- Stuck >25 minutes on one bug → log it, tell the human, switch tasks. The timeline in PLAN.md outranks any single bug.
