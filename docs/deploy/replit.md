# AgriSense AI

Bangla-first farm advisor app built for the IUT 12th ICT Fest Bdapps Agentic AI Hackathon (July 2026).

A smallholder farmer talks to an autonomous agent that produces a costed, weather-grounded season plan — and every number in that plan carries provenance you can inspect.

## Stack

- **Frontend**: Vite + React 19, port 5000
- **Backend**: FastAPI (Python 3.12) + OpenAI agent loop, port 8000
- **Auth**: Supabase (email/password + guest bypass)
- **LLM**: OpenAI gpt-4o (gpt-4o-mini verified broken for this 14-tool loop)

## How to run

The `Start application` workflow runs everything:

```bash
bash start.sh
```

This starts:
1. `uvicorn backend.api.main:app --port 8000 --reload` (background)
2. `cd frontend && npm run dev` (foreground, port 5000)

Vite proxies all `/api/*` requests to the backend, so the browser sees a single origin with no CORS issues.

## Required secrets (set in Replit Secrets)

| Secret | Purpose |
|--------|---------|
| `OPENAI_API_KEY` | Agent LLM calls — must be gpt-4o capable |
| `VITE_SUPABASE_URL` | Supabase project URL (browser) |
| `VITE_SUPABASE_ANON_KEY` | Supabase anon key (browser) |
| `SUPABASE_URL` | Supabase project URL (backend) |
| `SUPABASE_ANON_KEY` | Supabase anon key (backend) |

## Key env vars (set as Replit env vars)

| Var | Default | Notes |
|-----|---------|-------|
| `OPENAI_MODEL` | `gpt-4o` | Do not swap to mini — tool calls break |
| `VITE_DEMO_GUEST` | `false` | Set `true` to skip login entirely |
| `BDAPPS_MODE` | `simulator` | Payments module is dormant in this submission |

## Architecture notes

- Every number rendered by the UI comes from a tool call with a source citation — the `<Value>` component refuses to render without provenance
- Money arithmetic lives only in `backend/finance/engine.py` (Decimal, never the LLM)
- Crop ranking lives only in `backend/tools/crop_scorer.py` (deterministic)
- The agent streams Server-Sent Events; the frontend reads them via `fetch` + streaming body reader (not EventSource, because the real contract is POST)
- Two knowledge sources: `rag_query` (52 cited passages) + `crop_scorer` (hand-curated facts table)

## User preferences

- Keep exact pinned versions in `backend/requirements.txt` and `frontend/package.json` — no `^` ranges
- Do not merge `backend/.env` and repo-root `.env` — they serve different consumers
- `VITE_*` vars are read by Vite from `envDir: '..'` (repo root), not from `frontend/.env`
