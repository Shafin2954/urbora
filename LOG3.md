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

## [12:05] Phase 2 — checkout UI done; bdapps is demo-able end to end
**Did:** `frontend/src/components/CheckoutPanel.jsx` + styles in `App.css`, wired into
`App.jsx` as a tab that only exists once there is a basket. Two dev-harness baskets. The
checkout route now returns `receipt_bn` additively. Verified in **real Chrome at 390px**:
17/17 assertions on the happy path, 7/7 on the insufficient-balance path. Suite 328 green,
lint + production build clean.
**Decision — the on-screen receipt is the server's string, not a copy built in JS.**
`POST /api/checkout` returns `receipt_bn` alongside the `CheckoutResult` fields (additive,
same pattern as `redacted` on trace events), null unless the charge succeeded.
**Why:** The farmer should see exactly what was texted to their phone. A second copy composed
in the frontend would drift from the SMS the first time anyone edited either — and a receipt
for a payment that did not happen is the one lie this module must never tell.
**Decision — three stages are three views, not one form with a disabled button.** At the
confirm step the only things on screen are the amount (1.6rem, the largest thing on the page),
the masked number, the balance, and two choices.
**Why:** This is the screen where money leaves, read outdoors on a cheap phone. One decision
at a time is the whole design.
**Decision — the mode badge reports `unknown` when the server did not answer**, rather than
assuming simulator. Guessing "simulator" wrongly is exactly the failure CLAUDE.md §2.13
exists to prevent; guessing it rightly buys nothing.
**Design fixes made after looking at the rendered screen:** the honesty note ("সিমুলেটর — আসল
টাকা কাটা হচ্ছে না।") was inside the mode pill and ran together with the mode name — it is now
its own sentence below it. On the receipt screen the secondary action was leading; primary now
comes first.
**E1326 without a back door:** the drill basket is simply priced above the simulator's ৳100
balance, so the insufficient-balance recovery can be rehearsed on cue without draining an
account fifty times or adding a dev-only balance-setting endpoint to the API. Verified: warns
*before* charging, then reports "টাকা কাটা হয়নি", names the status, shows no receipt, offers retry.
**Verified in-browser, worth stating explicitly:** the full mobile number never appears on the
confirmation screen — only `***678`. Every control clears the 44px floor. No page errors.
**Rejected:** A dev endpoint to set the simulator balance (more API surface for something a
basket amount already expresses). Committing the Playwright script — it ran from the scratch
dir, so no browser test dependency enters the repo.

## [12:50] Phase 3a — Finance tab + provenance on tap; season plan deferred to after the KB
**Did:** `FinancePanel.jsx` (three scenarios, itemised costs, break-even, live area edit),
`Provenance.jsx` (tap any number), styles, wired into `App.jsx` as a tab that appears only
once a projection exists. Added an `AGRISENSE_PRICES_MD` env override so a curated price file
can be swapped in without editing the committed one. Verified in Chrome at 390px: **15/15**.
Suite 328 green ×3, lint + build clean.
**Decision — the season plan waits for the KB, and is NOT built yet.** PRD §8.4 wants a dated
calendar from BRRI/BARI crop calendars. Those documents are not curated yet (Phase 4), so
generating task dates now would mean inventing them — rule 2, on the screen a farmer would
actually act on. Phase 4 comes first and the plan follows it.
**Why the Finance tab still shipped:** its inputs are real. Yields come from crop.db; money
comes from cited rows or is refused. Nothing is invented, so it can ship ahead of the KB.
**Decision — `<Value>` takes a number and its provenance together, and renders "—" if the
provenance is missing.** You cannot print an unsourced figure by forgetting a prop; you have
to pass one. That turns "a number without provenance must not render" (CLAUDE.md §2.3) from
a review rule into a structural one.
**Decision — no arithmetic in the frontend at all.** Item totals, the total, ROI, break-even
and the recomputed values are all the server's. The area editor posts to
`/api/finance/recompute` and re-renders the response, so the tab and the agent cannot show
different numbers for the same farm.
**Verified — the judged moment, in the rendered DOM, not just in the engine:** the cost column
adds up to the paisa (2151189 vs 2151189 in cents), 2 bigha → 3 scales cost, revenue and
profit by exactly 1.5, ROI stays 60.23%, and break-even price does not move.
**Two layout bugs found by looking at the screenshot, not the tests:** (a) a four-column item
table clipped the totals column off the right edge at 390px — the one column the farmer is
there for; it is now two columns with `qty × rate` under the name, which also shows the
multiplication that produces each total. (b) An open provenance panel widened its table
column and squeezed item names to a few characters; it now overlays instead.
**Fixed a pre-existing flake:** `test_determinism_same_inputs_same_output` compares two
`score_crops` runs including provenance derived from cropdb results, whose `retrieved_at` is
stamped per call at second precision. Two runs either side of a second boundary differed on a
field unrelated to scoring — visible only under a full suite, i.e. exactly at a merge gate.
The read clock is now frozen in that test.
**Rejected:** A harness that emits a fake `finance_update` (a finance projection is inherently
an agronomic claim — the dev button calls the real endpoint instead, and shows the real
refusal when prices are missing).
