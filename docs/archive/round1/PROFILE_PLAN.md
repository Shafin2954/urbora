# Farmer profiles and return-visit personalization — plan (2026-09-29, not built yet)

Goal: a farmer never repeats himself. The second call, SMS or USSD dial — tomorrow, next
week or next season — starts from what we already know, and the first question the agent
asks is the one that matters *now* for that farmer.

## What exists already (build on it, don't rebuild)
- Identity: phone → `ph-<hmac>` farm id (`backend/channels/identity.py`), shared by web, SMS, USSD, voice.
- `farms` table: district, area, soil, water, season, budget — written by USSD intake and the agent.
- Fresh-session injection in `backend/agent/loop.py::run_turn`: the saved profile is given to
  the agent as a system note ("do NOT re-ask these fields").
- Persisted per farm: season plan with dated tasks (`plans`), weather alerts, crop-problem
  reports (`triage_reports`), market orders/listings, every phone turn (`channel_turns`).
- USSD already offers "আগের তথ্যে পরামর্শ?" to a known farmer.

## 1. The profile — three layers, each fact with where and when it came from
| Layer | Examples | Freshness (re-confirm after) |
|---|---|---|
| **Who** | name (optional, asked once), preferred language, preferred channel, prefers voice (literacy hint), first/last seen, visits | name: never; channel: rolling |
| **Land** (stable) | district/upazila, area, soil, land type (high/medium/low), water source | 12 months (water: each season) |
| **Season** (changes) | current crop, sowing/transplant date, budget, plan tasks, problems reported, orders, listings | the season |

Every fact is stored as `{value, source: farmer_stated | ussd_menu | tool, stated_at}` —
never an inference. A fact past its freshness is not deleted; the agent re-confirms it
("এখনও রাজশাহীতে 2 বিঘা?") instead of re-asking from zero.

Name: asked once, at the end of a first conversation that went well
("আপনাকে কী নামে ডাকব?"), optional, stored only in `contacts` (the one PII table, next to
the number), used in greetings. Never required to get advice.

## 2. Episode memory — what was discussed
At the end of each conversation (call hang-up, USSD end, SMS thread idle 30 min) write one
**episode**: `{date, channel, topics, crop, stage, advice_refs, farmer_intents, follow_ups}`.
- `advice_refs` point at the tool results already saved (plan, finance, triage report) —
  no numbers copied into the summary (rule 1/15: figures only from tools).
- `farmer_intents` / `follow_ups` ("will sow next week", "will spray tomorrow", "will
  check price") are extracted by the LLM into a fixed JSON schema, validated, and stored
  as open items with a due date.
Tables: `episodes`, `followups (farm_id, text_bn, due, status)`.

## 3. The return briefing — computed, not guessed
At the start of every session, code (not the model) builds a short **briefing** and
injects it instead of today's raw profile dump:
- days since last contact, visit count, name;
- current crop and **stage computed from the sowing date and today** (reuse
  `backend/kb/triage.py` STAGES) — the model never does the date arithmetic;
- plan tasks due or overdue in the next/last 7 days, open weather alerts;
- the last episode's topics and open follow-ups; pending orders/offers;
- which facts are stale and must be re-confirmed.

## 4. What the agent does with it — chosen by the gap, in code
The gap bucket is decided deterministically; the prompt tells the agent what to lead with.

| Gap | Lead with | Example |
|---|---|---|
| same day | continue; no re-greeting | "আর কী জানতে চান?" |
| 1–7 days | the open follow-up | "গত সপ্তাহে জাব পোকার কথা বলেছিলেন — স্প্রে করেছিলেন? এখন কেমন?" |
| 8–45 days | stage + due tasks | "আলু এখন 40 দিনের — সেচ আর ইউরিয়ার সময়।" |
| 45 days – end of season | harvest and selling | "কাটার সময় কাছে — বিক্রি করতে চাইলে দাম দেখাই?" (→ produce market) |
| new season / > 4 months | outcome, then next season | "গত মৌসুমে আলুর ফলন কেমন হয়েছিল?" then "এবার কী চাষ করবেন?" — land facts reused, only season/budget/water asked |
| > 12 months | re-confirm land | "এখনও রাজশাহীতে 2 বিঘা, নলকূপের সেচ?" |

Per channel: voice greets by name and asks the follow-up out loud; SMS keeps it to one line;
USSD adds one personalised line on the first screen ("আলু: আজ সেচের দিন") within the 80-unit budget.

## 5. Outcome capture — the loop that makes it better (and the impact metric)
At harvest or on the next-season visit, ask yield and sale price. Stored as
`farmer_stated`, it (a) checks our advice against reality, (b) with consent, adds
district-level evidence to the crop scorer, (c) gives the pitch a real impact measure
(advice followed → yield/price reported).

## 6. Privacy and trust
- First contact: one-line consent ("আপনার জমির তথ্য মনে রাখব যাতে বারবার বলতে না হয়") —
  opt-out keeps advice working, just without memory.
- "তথ্য মুছুন" (SMS/USSD/voice) deletes profile, episodes and follow-ups.
- Name and number only in `contacts`; traces keep the existing redaction; the surveillance
  summary never carries farm ids.
- Shared family phones: when the stored name exists, confirm it ("আপনি কি রহিম ভাই?"); a
  "no" starts a separate profile under the same number (profile per phone + person).

## 7. Build order
1. **Briefing + gap buckets + name** (≈½ day; demo-critical): `backend/memory/profile.py`
   (facts with source/date, freshness), `backend/memory/briefing.py` (deterministic),
   `loop.py` injects the briefing, `prompts.py` rules for using it. Tests: bucket edges,
   stage from dates, stale facts, no re-asking fresh facts.
2. **Episodes + follow-ups** (≈½ day): summarizer at session end with a JSON schema and
   validation; follow-ups surfaced by the briefing.
3. **Outcome capture, consent, deletion** (≈½ day).
Demo: call once ("রাজশাহী, 2 বিঘা, আলু, 1 নভেম্বর রোপণ"), then simulate day +7 and
day +95 with a clock override to show the two different openings.
