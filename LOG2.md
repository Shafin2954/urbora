# LOG2 — Instance B (api / frontend / finance / payments)

Append-only. Format defined in CLAUDE.md §1. Newest entry at the bottom.

---

## [00:00] Log initialized
**Did:** Created log file. Read PRD.md, PLAN.md, NOTES.md, CLAUDE.md.
**Decision:** none yet.
**Why:** —
**Rejected:** none.
**Impacts other instance:** no.

---

> Timestamps below are elapsed time since event start (H0 = 09:00), matching the
> `[00:00]` entry above.

## [00:10] Branched dev-b, added .gitignore and .env.example
**Did:** Created branch `dev-b`. Added `.gitignore` and `.env.example` at the repo root.
**Decision:** B creates these two shared-root files now rather than waiting.
**Why:** The repo had no .gitignore at all. One careless `git add -A` and node_modules or a real `.env` is in history — NOTES.md #20, and painful to undo. Too urgent to leave for a coordination round-trip.
**Rejected:** Waiting for A / asking first — the exposure window is the whole point; a missing .gitignore is a hazard from the first `npm install`, which was ten minutes away.
**Impacts other instance:** **yes.** (1) These are root files, outside anyone's directory — A, if you also created one, take mine or merge, don't duplicate. (2) `.env.example` has an empty **A-owned section** at the bottom for `ANTHROPIC_API_KEY` / `CLAUDE_MODEL` — headings only, fill it freely, no coordination needed. (3) I deliberately did **not** gitignore `data/crop.db`; PLAN.md §1 leaves that call to you.

## [00:25] FastAPI skeleton + hello-world SSE, streaming confirmed
**Did:** `backend/api/{__init__,config,main,sse}.py` + `requirements-api.txt`. Endpoints: `GET /api/health`, and `GET`+`POST /api/hello/stream` emitting a fixed 5-event script. Verified with curl: events arrive 400ms apart, correct `text/event-stream` + chunked headers.
**Decision:** Three, all load-bearing. (1) **SSE wire format = one `data:` line holding one JSON object, with the discriminator inside as `type`** — no SSE `event:` field. (2) **The frontend transport is fetch+streaming-body, not EventSource.** (3) Hand-rolled the SSE layer instead of adding `sse-starlette`.
**Why:** (1) is exactly the shape PLAN.md §2 already specifies, and a second naming system on the wire is just a second place to typo an event name. (2) EventSource can only do GET, and our real contract is `POST /api/chat` with a JSON body — building on EventSource means rewriting the client the day the agent lands, so we pay that cost now at zero. (3) One less dependency to churn (NOTES.md #15), and the redacting emitter needs custom shaping anyway.
**Rejected:** `sse-starlette` — it mainly buys disconnect handling and heartbeats, which are ~30 lines I wrote directly and now control. Also rejected putting my pins in `backend/requirements.txt`: that file is A's per PLAN.md H0–H1, so my pins live in `backend/api/requirements-api.txt`.
**Impacts other instance:** **yes, please read.** (a) A: pull my deps into `backend/requirements.txt` with `-r api/requirements-api.txt` rather than restating versions, so we can't drift. (b) I made the venv at **repo root `.venv`** (gitignored) — suggest we share it; if you make your own, nothing breaks. (c) `backend/api/sse.py` has the event constructors for the PLAN §2 contract; when your agent loop emits, it goes through there. (d) **`tool_call` / `tool_result` are NOT emittable yet** — the redactor (NOTES.md #19) doesn't exist until my next block, and I deliberately did not stub a no-op redactor, because one that silently does nothing is worse than none.

## [00:45] Frontend scaffolded — Vite + React, manifest-only PWA
**Did:** `frontend/` via Vite React template, then stripped the template: deleted its demo page, logos, hero image and its purple accent CSS. Added `vite-plugin-pwa`, `src/api/sse.js` (SSE-over-fetch client), `src/api/client.js`, design tokens in `index.css`, own SVG icons. Pinned every npm version exactly (the template ships `^` ranges). Build + lint clean.
**Decision:** (1) **Plain JavaScript, not TypeScript.** (2) **PWA is manifest-only and the service worker is neutered three ways:** `injectRegister: null`, `devOptions.enabled: false`, and `selfDestroying: true`; plus `main.jsx` unregisters any SW it finds in dev. (3) **No CDN webfont.** (4) Vite proxies `/api` → `:8000`.
**Why:** (1) 24h, one page, and pydantic is the real contract — TS would buy type errors to fix, not bugs prevented. (2) PRD §9 says manifest-only and NOTES.md #8 calls stale-SW ghost-JS an hour-eater. `selfDestroying` matters because the build still emits `dist/sw.js`; a dormant SW file is a loaded gun, so if anything ever registers it, it unregisters itself and drops all caches. The dev-side eviction is because `localhost:5173` is shared ground with every other Vite project on this machine. (3) Noto Sans Bengali from a CDN is a font that fails to load exactly when venue wifi dies (NOTES.md #11); system stack works always. (4) One origin in dev = zero CORS, and identical to production.
**Rejected:** TypeScript (above). `devOptions.enabled: true` — that serves a SW in dev, which is the precise thing NOTES.md #8 warns about. Google Fonts (above).
**Impacts other instance:** no — all inside `frontend/`.

## [01:00] Browser confirmed rendering live SSE — H1 gate item met
**Did:** Ran both servers and drove real Chrome headlessly against the dev server. Verified: page shell renders, health dot goes green **through the Vite proxy**, clicking the button streams 5 events that render **incrementally** (sampled row count climbed 1→2→3→4→5 over 1.6s), Bangla renders correctly, **0 service workers registered**, no page errors.
**Decision:** Test Bangla + Western numerals through the pipe at H0 rather than at first real content.
**Why:** Incremental row counts are the actual proof — if all 5 had appeared at once, something buffered the stream and we'd have found out on stage. Bangla is 3 bytes/char in UTF-8 and *will* straddle a chunk boundary eventually; the client decoder handles it, and now we know rather than hope. **PLAN.md H1 sync item "SSE confirmed in browser" is done.**
**Rejected:** Calling curl good enough — curl proves the server streams, not that React renders as events land. Also rejected adding Playwright to the repo: the check ran from a scratch dir, so no test dep is committed. A permanent browser E2E harness is a **proposal**, not something I'm building now (out of block scope).
**Finding worth knowing:** the PWA manifest `<link>` is injected **only into the production build**, not the dev server — a consequence of `devOptions.enabled: false`. So the **phone install test at H18–H20 must run against `npm run build && npm run preview`, not `npm run dev`.** Confirmed the link + `manifest.webmanifest` are present in `dist/`.
**Impacts other instance:** no.
