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

## [13:40] Phase 5 — the two judged behaviours that were wired but never fired
**Did:** `backend/tools/ask.py` (`ask_farmer`), `backend/tools/farm_memory.py`
(`remember_farm`), farm recall in `run_turn`, `InputRequestEvent` emission in the loop,
prompt sections for intake widgets and returning farmers, and the Bangla-numerals fix.
24 new tests; **352 green**.
**The finding:** two Tier-0 behaviours existed on both sides and connected to nothing.
(a) The five `input_request` widgets have been in the UI since H2 and the event in the
frozen contract since H1 — but no code path ever emitted one, so in the real flow they were
unreachable and the judged "each question ships with a widget" (PRD §8.1) simply did not
happen. (b) `get_farm`/`save_farm` were built with the session store and never called, so a
"returning farmer" could only ever be a row seeded by hand — and the demo opens on exactly
that (PLAN §5 step 1).
**Decision — the agent asks by calling a tool, not by writing a question.** `ask_farmer`
takes field + prompt_bn + input_kind + typed options, validates them, and the loop turns the
result into the SSE event. Inferring a widget from Bangla prose would be a guess in the one
place PRD is explicit that at most one question may be open.
**Decision — the 64 district options are filled in server-side**, not typed by the model.
Sixty-four hand-written options is a transcription error waiting to happen, and the spellings
have to match what geocode and crop.db accept. Added Bangla names for all 64 (a
transliteration of proper nouns, not an agronomic claim) so a farmer is not asked to read
Latin script to find their own district; a test asserts every label is actually in Bangla.
**Decision — the remembered profile is injected as a system note, once, on a fresh session.**
Not as words in the farmer's mouth, and not every turn: after turn one the history already
carries it, and repeating it burns tokens and drifts context. An unknown farm injects
nothing — a miss means proceeding without context, never inventing a farm.
**Decision — `remember_farm` merges rather than replaces.** Intake is incremental, so a later
call carrying only a budget must not erase the district learned three turns ago. It stores a
JSON blob rather than typed columns because a half-known farm has to be storable;
`FarmProfile` remains the shape for a complete profile reaching the UI.
**Fixed the open prompt bug from LOG1 [04:00]:** the model was rendering weather figures in
Bangla numerals (২৫.৫°C), violating rule 10 / NOTES #17. The instruction was one clause in a
sentence about tables; it is now its own emphatic rule with worked examples, and says why —
a judge checks a number on screen against the English trace panel, and Bangla digits make
that check impossible.
**Rejected:** Parsing the model's prose for questions (guesswork at the contract boundary).
Saving the farm automatically on every turn (stores what the model inferred mid-intake rather
than what the farmer confirmed — the prompt requires the restatement step first).

## [14:15] Phase 6a — README, seeded demo farm, farm wired through the UI
**Did:** `README.md` (the judges' first artifact), `backend/memory/seed_demo.py`, and the
frontend now sends a real `farm_id` instead of `null`. 352 green, lint + build clean.
**Decision — the README leads with the honesty ledger, not the feature list.** The
real-vs-mock table says plainly which tables are still empty, and a section explains why
retail prices cannot become revenue with the actual numbers (retail coarse rice 50–60৳/kg
vs paddy farm-gate roughly half). It carries the exact `AGRIBASE_CLEANING` disclosure
wording so we never claim BBS-verified.
**Why:** Q&A prep is half the score of the data-rules story, and a judge who reads that the
price tables are empty *before* they see a refusal on screen reads the refusal as design
rather than breakage.
**Decision — the demo farm is seeded, and only the farm is seeded.** `seed_demo.py` writes
one profile (Rajshahi, 2 bigha, clay loam, tubewell, ৳15000, rabi — PRD §3.3/§15 fix the
district and season). No yields, no prices, no advice: everything the agent says at demo
time still comes from live tools and cited data. What is seeded is only what a farmer would
have told us in a previous conversation.
**Decision — one farm per install** (`VITE_FARM_ID`, default `demo-rajshahi`). PRD §8 lists
auth beyond farm profiles as a non-goal, so there is no picker and no login. The chat and
the Finance tab now key on the SAME farm id — previously the tab used the session id, so a
live area edit would have recomputed a projection the agent never made.
**Verified:** seeded, then read back — `করিম উদ্দিন / Rajshahi / 2 bigha` recalls from SQLite.


## [15:05] Phase 7 — data/prices.md filled from agristats.db + BARC/BARI PDFs; Profit + Budget live for real
**Did:** Filled both `data/prices.md` tables — farm-gate prices for all 5 crops (harvest 2024-2025, `agristats.db` view `v_prices`, Table 10.5.1 p.638) and input costs for all 5 (boro/aman/potato from `v_cost_of_cultivation` Tables 8.3/8.4/8.5, converted acre→ha via `units.py`'s `ACRE_HA`; mustard/lentil from BARC FRG-2024 + BARI Krishi Projukti Hatboi real fertilizer doses, priced against a dated Daily Star government fertiliser-price notice). Zero code changes — the whole catalog→engine→tool→crop_scorer chain was already built and tested, exactly as the previous phase's note predicted. Fixed two tests whose assumptions were the empty-file state (`test_the_shipped_retail_rows_are_not_reachable_as_revenue` now checks the structural invariant — stripping the retail section changes nothing about farm-gate prices — instead of asserting prices are missing, which is no longer true; `test_crop_scorer_tool_returns_candidates_and_degraded_list` now expects 3 degraded lines, not 4, since Profit switched on). **352 tests green.**
**Decision — mustard/lentil costs are fertiliser-only (Urea/TSP/MoP), confidence `low`.** No citable seed price or Gypsum/Zinc/Boron price was found anywhere (checked both PDFs' full text and two web searches for BADC/DAE rates); the fertiliser price itself is a 2023-04-11 government notice, the most recent found. These two crops' costs are a documented minimum bound, not a complete input cost — stated in `prices.md` itself, not hidden.
**Why:** Rule 2 — real cited numbers only; a partial, honestly-labeled cost beats a complete but invented one.
**Verified — live, over real HTTP, not just unit tests:** `POST /api/chat` with a ৳50,000 budget on 2 bigha (~0.8 ha) at Rajshahi correctly **excludes boro_rice/aman_rice/potato on the Budget filter for the first time ever** (real min_cost_per_ha × area > budget, e.g. potato 157,532/ha × 0.8 = 126,026 > 50,000) and scores mustard/lentil with real, formula-transparent Profit numbers that reconcile exactly against the curated cost lines (mustard: 2216.22 kg/ha × 78.53 − 14,000 input cost; lentil: 1305.48 × 90.78 − 4,292.50). This is PRD §6's Budget-exclusion recovery moment, real for the first time.
**Data note worth knowing:** potato's Profit (876,552 Tk/ha at Rajshahi, unconstrained candidate set) is a real outlier — its Holt yield (~26,080 kg/ha) times its price genuinely dwarfs the other 4 crops, which compresses everyone else's min-max-normalized Profit points toward 0 per PRD §6's own normalization rule. Not a bug; worth knowing before narrating a demo.
**Rejected:** Building an extraction script for a 5-row + 8-row table (NOTES #18b — hand-curate small tables, no pipeline). Inventing a seed price or fertilizer-price estimate to complete mustard/lentil more fully — left as an honest partial rather than guessed.
**Flagged, not done (recommended next steps):** (a) re-instating wheat as a 6th crop — `agristats.db` now has real wheat price+cost+district production data, but this reopens a deliberate prior scope decision and needs its own pass (crop.db regen, `CANON_TO_KEY`/`catalog.CROPS` updates, retest). (b) Curating the `crop_facts` KB seam (season/soil/water/climate) from the 4 staged PDFs — still the only fully-unavailable component set (Agronomic fit, Climate fit, Season/Soil/Water screening); a separate research pass, different content than the fertilizer-dose lookup done here.
**Impacts:** none outstanding — single operator.
