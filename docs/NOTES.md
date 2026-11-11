# NOTES — known traps, numbered

Code cites these by number ("NOTES #13"); keep the numbers stable and append new ones. Written during the July hackathon, so some mitigations mention hours (H12) and two instances (A/B); the traps themselves still apply.

## Original header: NOTES v2 — Caveats. Read before coding. Re-read at every sync.

Ranked by kill-probability. Each has a mitigation. Hit one without a mitigation here → log it + tell the other person immediately.

## Kill-class

1. **Weather API can't cover a season.** Forecast = 16 days; season = 90–120. Faking month-3 weather = credibility gone on 20-pt accuracy. → Two labeled tools: `get_forecast` (actionable) + `get_climatology` (planning assumption). Every claim carries `source_type`; Bangla wording differs ("পূর্বাভাস অনুযায়ী" vs "গত বছরের গড় অনুযায়ী, ভিন্ন হতে পারে"). Climatology presented as prediction = bug.

2. **LLM arithmetic or LLM ranking.** Judges change an input and check consistency. → LLM never computes and never ranks. Finance engine + crop_scorer are pure tested functions; model narrates their output. Violation = bug.

3. **Rules risk on pre-event artifacts.** "All application code written during the event." → Parser, Holt fit, Chroma ingest all WRITTEN AND RUN in-event; crop.db + index generated in-event with meta timestamps; raw yearbook data hosted publicly, link in README. Pre-cached third-party model/wheels/packages are fine. If judges ask: raw public data in, all code and derived artifacts produced in-window.

4. **bdapps portal blocked** (needs receiving URLs → no app yet). → Simulator is PRIMARY, built H3–H6, exact request/response shapes incl. error codes (E1326 insufficient-balance path is demo-able). Confirmation step before any charge. `mode` label in UI + README. If portal unblocks: whitelist venue IP (`curl ifconfig.me`), real ৳2 debit on Robi SIM tested H15–18, never first time on stage; on-stage live failure → one rehearsed click to simulator. Guard for HTML-not-JSON error responses.

5. **Runaway agent loop burning credits.** → Max 12 iterations/turn, per-turn token+cost in `done` event and console. Sonnet. Prompt caching on system prompt + static context. Two Pro accounts ≠ infinite; watch the cost line.

6. **Geocoding village names.** Wrong "Mirpur" = silently wrong everything. → Geocode returns candidates, agent confirms with farmer (doubles as recovery demo #1). Hardcoded 64-district fallback.

## Hour-eater class

7. **Cross-lingual RAG.** English KB, Bangla queries → silent garbage retrieval. → Agent formulates all rag_query calls in English (system prompt rule), converses in Bangla. No multilingual embedding models — scope trap.

8. **Service worker cache in dev.** Stale JS ghosts. → No SW at all in core scope; manifest-only PWA. SW is [GATED] and prod-build-only if ever attempted. If frontend weirdness: hard-reload + check for a rogue SW before debugging code.

9. **Local units.** bigha/katha/decimal/maund vs kg/ha; bigha varies regionally. → Fix 1 bigha = 33 decimal = 0.1338 ha, convention stated in README. Single tested units.py; internal = ha/kg only.

10. **KB curation rabbit hole.** → Hard cap 3h. 3 demo crops deep. Judges test rice, not dragonfruit.

11. **Venue wifi + first-run downloads.** → Pre-cache embedding model, lockfiles, wheels. One full offline boot test: app must not crash; weather degrades to labeled cached data (this is also recovery behavior #3).

12. **Merge conflicts at 3am.** → Ownership map is law; schemas.py frozen H1; branch per person; sync merges; `tier0-stable` tag = demo lifeboat.

13. **SSE + CORS friction.** → Hello-world SSE pipe is B's first hour. SQLite WAL mode.

14. **Scope sprawl via agent enthusiasm.** Two Claude Codes + Codex generate code faster than two humans can integrate and verify. The brief: "ten half-built features is the most common way teams lose." → GATE: no [GATED] item starts before `tier0-stable` exists and main is green. Agents propose in logs; humans open the gate.

## Paper-cut class

15. **Chroma / dependency churn.** → Pin exact versions immediately, both ecosystems.

16. **Demo wandering.** → Seeded scripted farm, rehearsed twice, timed. Code freeze H22. Rehearse the live↔simulator toggle and one recovery moment explicitly.

17. **Bangla numerals in math tables.** → Western numerals in tables/trace/computed values; Bangla text around them. Trace panel English.

18. **Market prices.** No reliable free live BD price API; inventing one = fake grounding. → SOLVED by BBS Yearbook Ch.10: harvest-time + wholesale prices 2023–24, hand-curated in-event into data/prices.md, each row table/page cited. Labor costs from Yearbook Ch.7.5 wages. Remaining input prices (seed, fertilizer) cited with URL + date or deleted. No placeholders anywhere.

18b. **Yearbook extraction is mangled.** The PDF→markdown dump has broken tables. Do NOT write a general yearbook parser — 6-hour trap. Hand-curate ONLY the needed small tables (prices for demo crops, demo-region AEZ soil rows, wages, crop calendar) into clean CSV/markdown during the event. Programmatic parsing is only for the big yield/area tables via parse_agribase.py.

19. **Trace leaking secrets.** bdapps auth rides in request bodies. → Redacting emitter: password/appId/key/token/secret → `***`; phone/subscriberId → last 3 digits. Unit-tested with fake bdapps payload.

20. **Secrets in git.** → .env only, .env.example committed, diff check before every push.

21. **Sonnet drifting out of Bangla.** → System prompt: mirror farmer's language, default Bangla. Spot-check each sync.

22. **Robi SIM balance = 0 at demo.** → Top up before H15 if live path is on. ৳2 test debits only.

23. **Holt overclaim.** 9 data points = wide uncertainty. → Damped Holt point estimate as base + residual-sd band, labeled "projection, not guarantee." Never quote the projection without the band in finance views.

24. **Provenance gaps discovered late.** → H12–H15 includes an explicit audit: click every number, confirm provenance renders. A number without provenance must not ship.

## Added after the hackathon

25. **Bangla through `curl` on Windows Git Bash arrives as `???`.** A Bangla string passed as a command-line argument (`curl --data-binary '{"message":"আমি…"}'`) is mangled to question marks before curl sends it. The agent then rightly asks for facts it "was never told", which looks exactly like an intake bug (cost ~20 min on 2026-11-10, LOG.md [17:05]). → Send Bangla test messages from Python (`httpx`, `json=`), or from a UTF-8 file with `curl --data-binary @msg.json`. Check what was stored with `store.get_session_messages(session_id)`.
