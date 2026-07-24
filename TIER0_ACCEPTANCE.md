# Tier 0 acceptance audit

Run: 2026-07-25. Do not start advanced features until every row is green in a
fresh live API session.

| Capability | Evidence exercised | Status |
|---|---|---|
| Conversational intake | `ask_farmer` contract and remembered-profile tests; live complete-profile turn | Needs a fresh vague-opening replay |
| Live weather grounding | Live Open-Meteo forecast response previously traced; weather unit tests | Needs a fresh default-demo replay |
| Crop recommendation | Seeded Rajshahi Rabi profile now yields mustard, lentil, Boro rice | Green in scorer; repeat live after reload |
| Season plan | Deterministic cited tasks and persistence tests | Green in tests; repeat live after reload |
| Financial projection | Itemized engine/recompute tests and 2→3 bigha API rehearsal | Green |
| Explained reasoning | Provenance objects and trace/plan/finance render paths | Green in contracts |
| Knowledge base retrieval | New cited `rag_query` retrieval and orchestration tests | Green in tests; **live trace must show rag_query** |
| Visible agent trace | Tool-call/result redaction tests and Trace/Evidence UI | Green in contracts; retrieval trace is the outstanding live check |

## Release blocker

The fresh Uvicorn process still served a chat turn without the expected
`rag_query` trace event despite the source-level orchestration tests passing.
Treat that as a deployment/loaded-code issue until a fresh live chat trace shows
`rag_query` before `crop_scorer` and before `season_plan`.
