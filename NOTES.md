# NOTES — Caveats. Read before coding. Re-read at every sync.

Ranked by kill-probability. Each has a mitigation. If you hit one without a mitigation here, log it and tell the other person immediately.

## Kill-class

1. **Weather API can't cover a season.** Open-Meteo forecast = 16 days. Season = 90–120 days. Faking month-3 weather = judges catch it = credibility gone on the 20-pt accuracy criterion. → Two tools: `get_forecast` (real, near-term actions) + `get_climatology` (real historical/climate endpoint, long-range calendar). Agent names its source per claim.

2. **LLM arithmetic.** Judges will change an input and check consistency. Model-computed money drifts. → LLM NEVER does math. Finance engine = pure functions + unit tests. Model calls the tool and narrates the result. This rule is in CLAUDE.md; treat violation as a bug.

3. **bdapps portal risks.** (a) No app exists yet — create at portal immediately; approval timing unknown. (b) `E1312` — venue's public IP must be whitelisted; get it at venue (`curl ifconfig.me`) hour 0; NAT rotation would re-break it. (c) On error, bdapps may return HTML not JSON — guard for `<html`. → Simulator twin with exact documented request/response shapes built in parallel; brief allows "sandbox/simulator mode"; label mode in README and UI. Checkout flow is all-outbound: no public callback URL, no tunnel needed. Rehearse live Robi debit at H15–18, never first time on stage.

4. **Runaway agent loop burning credits.** Tool error → retry spiral → $80 gone. → Max 12 iterations/turn. Per-turn token+cost printed and sent in `done` event. Sonnet, not Opus. Prompt caching on system prompt + static KB context.

5. **Geocoding village names.** Wrong "Mirpur" = wrong weather = silently wrong everything. → Geocode tool returns candidates; agent confirms with farmer. Hardcoded 64-district fallback table.

## Hour-eater class

6. **Cross-lingual RAG.** KB is English, farmer speaks Bangla. Bangla query against English embeddings retrieves garbage, silently. → Agent formulates all `rag_query` calls in English (instructed in system prompt), converses in Bangla. Do NOT reach for multilingual embedding models — scope trap.

7. **Service worker cache in dev.** Stale JS ghosts, hour lost. → SW disabled in dev (`devOptions.enabled=false`), enabled only in final build. If weirdness: hard-reload + unregister SW first, before debugging code.

8. **Local units.** Farmers: bigha/katha/decimal, maund. Charts: kg/ha. One silent conversion bug = visibly wrong advice to any Bangladeshi judge. Bigha varies regionally — fix 1 bigha = 33 decimal = 0.1338 ha, state the convention in README. → Single `units.py`, tested at H1–3, everything internal in hectares/kg.

9. **KB curation rabbit hole.** Messy PDFs eat 6 hours. → Hard cap 3 hours. 15–25 hand-cleaned markdown docs, 5–6 demo crops only (boro/aman rice, wheat, potato, lentil, mustard). Judges test rice, not dragonfruit. Depth over breadth.

10. **Venue wifi + first-run downloads.** sentence-transformers pulls its model on first use; pip/npm need net. → Pre-cache embedding model, commit lockfiles, download wheels early, run one full offline boot test (weather degrades gracefully, app must not crash).

11. **Merge conflicts at 3am.** → Ownership map in PLAN.md is law. schemas.py frozen H1, single owner. Branch per person, sync merges every 2–3h, `tier0-stable` tag as demo lifeboat.

12. **SSE + CORS friction.** Vite dev → FastAPI stream: CORS/buffering burns an hour if discovered late. → Hello-world SSE pipe is B's first task, H0–1. SQLite WAL mode for concurrent reads during streams.

## Paper-cut class

13. **Chroma version churn.** Breaking API changes between versions. → Pin every dependency exactly, immediately, both `requirements.txt` and `package-lock.json`.

14. **Demo wandering.** Live intake conversation drifts, 4 minutes gone. → Scripted demo farm (district near venue, 2 bigha, loam, tube-well, ৳50,000, Aman) seeded in DB. Rehearse twice, timed. Code freeze H22.

15. **Bangla numerals vs math.** Bengali numerals in cost tables hurt judge inspectability. → Western numerals inside tables/trace; Bangla text around them. Trace panel English (it's for judges).

16. **Market prices.** No reliable free live BD price API. Inventing one = fake grounding. → Static reference price table with source + date, disclosed in README and in the plan's assumptions list. Honest beats fake-live.

17. **Yearbook data legality.** Rules ban pre-built application code, not data. Yearbook is public; our SQLite is a parsed artifact. → README discloses source + that parsing predates the event; publish the dataset publicly if 20 min spare. If judges ask, answer exactly this.

18. **Secrets in git.** bdapps password, Anthropic key. → `.env` only, `.env.example` committed, check `git diff` before every push.

19. **Sonnet response drift into English.** Long sessions can drift out of Bangla. → System prompt rule: mirror the farmer's language; default Bangla. Spot-check at each sync.

20. **Robi SIM balance.** Live debit demo fails on ৳0 balance. → Top up the SIM before H15. Debit tiny amounts (৳2) in tests.
