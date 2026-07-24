# AgriSense frontend

Vite + React PWA (manifest-only). B-owned per PLAN.md §1.

## Run

Two processes. From the **repo root**:

```bash
# 1. API
.venv/Scripts/python -m uvicorn backend.api.main:app --reload --port 8000

# 2. frontend
cd frontend && npm install && npm run dev
```

Open <http://localhost:5173>. `npm run dev:host` also binds the LAN address,
for testing on a real phone.

## Two things to know before changing config

**The `/api` proxy is why there is no CORS.** `vite.config.js` forwards `/api`
to `http://127.0.0.1:8000`, so the browser only ever talks to one origin — in
dev and in production alike. Point the frontend straight at `:8000` and you have
re-invented the CORS problem (NOTES.md #13).

**There is no service worker, on purpose.** `vite-plugin-pwa` runs with
`injectRegister: null`, so it emits a manifest and nothing else — the app is
installable and themed, but no SW ever caches our JS (PRD.md §9, NOTES.md #8).
`src/main.jsx` additionally unregisters any service worker it finds in dev,
because `localhost:5173` is shared ground with every other Vite project on this
machine. If the UI ever behaves impossibly, check the console for the eviction
warning before debugging your own code.

## Layout

```
src/
├── api/
│   ├── client.js   API base + health check
│   └── sse.js      SSE over fetch (POST-capable; EventSource cannot POST)
├── App.jsx         H0 connection self-test — replaced by the chat UI at H1–H3
├── App.css         layout for the above
├── index.css       design tokens: earthy palette, farmer-first sizing
└── main.jsx        entry + dev service-worker eviction
```
