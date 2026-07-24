# LOG3 — single operator (both roles)

The A/B split ended at H10.5 on 24 Jul 2026. One operator now works the whole
tree: agent, tools, kb, memory, api, frontend, finance, payments. Format is
CLAUDE.md §1, unchanged. Append-only, newest at the bottom.

`LOG1.md` (A) and `LOG2.md` (B) are closed and stay as history — with one late
addition to LOG1 for a commit that shipped undocumented. Everything from here
lands in this file.

Timestamps are elapsed since event start (H0 = 24 Jul 09:00).

---

## [10:30] Phase 0 — merged the two halves, retired the duplicate seam
**Did:** Merged `origin/master` into `dev-b` (clean, no conflicts). Deleted
`backend/api/sessions.py` and `backend/api/agent_bridge.py`. Restored `chat.py` to call
`run_turn(session_id=…, farm_id=…, message=…)`. Rewrote `tests/test_chat_seam.py` around
the new shape. Appended the missing entry to `LOG1.md` for commit `5581afc`. Opened this
file. **293 tests green** (234 root + 59 backend).
**The problem this fixes:** the two instances had independently built the same seam from
opposite sides. B asked for `async run_turn(session_id, farm_id, message)` at [02:30];
A built a sync generator over a message list; B then wrote an adapter (in-process session
dict + worker-thread bridge) to fit it — and A, in the same window, rewrote `run_turn`
into exactly the async signature originally asked for, with its own SQLite session store
and its own thread bridge. Two session stores, two bridges, one seam.
**Decision:** Keep the agent-side version; delete the API-side adapter.
**Why:** It persists history in SQLite instead of a process-local dict, so a session
survives a restart — which the demo's returning-farmer opener actually needs. It also
puts conversation state next to the memory feature that will own it, rather than in the
transport layer. The adapter was good work that the other half made redundant; keeping
both would have been the real mistake.
**Kept from the deleted work:** `sse.ensure_redacted` in `format_sse` stays as a second
redaction layer. The loop already masks tool events by construction, but `schemas.py`
declares those events carry RAW params, so any future producer that skips the
constructors would leak bdapps credentials into the judge-facing trace. It distinguishes
masked from raw by the `redacted` marker rather than re-masking blindly — **re-masking a
phone is lossy** (`***678` has three digits left and collapses to `***`). Also kept the
outer `try/except` in the route: a missing `OPENAI_API_KEY` raises at client construction,
which is *above* the loop's own try block and escapes it entirely.
**Rejected:** Keeping the API-side store and asking the agent to go back to a message
list (would have thrown away restart-persistence and rewritten a just-pushed commit).
Deleting the second redaction layer as redundant (it is redundant exactly until the day
it isn't, and that day is unrecoverable).
**Verified:** `POST /api/chat` over real HTTP reaches the loop and degrades honestly —
no `.env` on this machine, so it returns `error` naming the missing key, then `done`.
**Impacts other instance:** n/a — one operator from here.

## [11:20] Phase 1 — finance wired end to end, waiting on data not on code
**Did:** `data/prices.md` (the citation table), `backend/finance/catalog.py` (parses it into
engine inputs), `backend/tools/finance.py` (`finance_projection` agent tool, registered in
`tools_spec.py`), the finance seam supplied to `crop_scorer_tool`, `backend/api/finance.py`
(`POST /api/finance/recompute`), and `_panel_event` in the loop so a costing emits a
`finance_update` the Finance tab can render. 55 new tests; **328 green**.
**Decision — prices are a data drop, not a code change.** The yearbook extraction is still
running, so `prices.md`'s farm-gate and input-cost tables ship **empty**, and every consumer
degrades honestly: the tool returns `price_data_unavailable` naming exactly what is missing,
the route returns 422, the scorer reports Profit unavailable. Filling in one markdown row
switches all of it on with no code touched — proven by tests that write a filled table and
assert the whole chain lights up, rather than by hoping.
**Why:** "It'll work when the data lands" is the class of claim that turns out to be false at
4am. The tests make it checkable now.
**Decision — retail prices are structurally unreachable from revenue.** The TCB bulletin A
committed is *retail Dhaka*: milled rice 50–60৳/kg, split dal 90–100, potato 25–30, dated
24-07-2026. A farmer sells **paddy**, unmilled, at roughly half that. `prices.md` keeps those
rows (they are real, cited, and genuinely useful as market context) in a third table that
`catalog.py` parses but `projection()` cannot read. A test pins it: costs present + retail row
present + no farm-gate row still refuses.
**Why:** Wiring retail into revenue would roughly double every profit figure on screen, in the
direction that flatters us, and a judge who knows paddy prices would catch it in one question.
**Decision — partial price coverage supplies the scorer nothing at all.** PRD §6 normalizes
Profit min-max *within the candidate set*, so pricing three of five crops would rank the other
two down for lacking a citation rather than for being worse crops. All five or none.
**Also:** the finance tool converts the farmer's bigha/katha itself and returns
`max_area_ha_within_budget` precomputed, so the reduced-area replan (demo recovery #2) needs no
arithmetic from the model — rule 1 holds even in the recovery path.
**Verified:** over HTTP, all three refusals name the cause — uncited prices, missing inputs, and
a typo'd override field (`aera` fails loudly instead of silently recomputing the old area).
With a filled fixture table, 2 bigha → 3 scales cost/revenue/profit by exactly 1.5, holds ROI
constant, leaves break-even price unmoved, and the cost column still adds up in the JSON the
browser receives.
**Rejected:** Deriving farm-gate from retail with a milling-ratio conversion (defensible only
with a citation for the ratio; without one it is invented data). Shipping example rows in
prices.md to make the tables look filled (placeholder content, banned).
