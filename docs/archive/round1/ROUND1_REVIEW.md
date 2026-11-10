# Round 1 form: review loop and scores (2026-09-30)

What produced `ROUND1_FORM.md` v5, how it scored, and what is still weak. The reviewers are
simulated (Claude subagents with a judge persona each), not the real FutureMakers panel.
Treat the scores as a stress test, not a forecast.

## The loop

1. **Write** a revision (the orchestrating session).
2. **Gate** with `python scripts/form_check.py`. It fails on word limits, old names, the
   hotline, blame phrases, or a missing prior-work disclosure. It also reports AI-writing
   tells (em dashes, stock AI words, "not X but Y", label lead-ins, contrast frames, triplets,
   flat sentence rhythm).
3. **Review** with four independent reviewers on a frozen snapshot (prompts in
   `scripts/form_review_prompts.md`):
   - Judge A, a telecom product lead: adoption, operator fit, scale, money.
   - Judge B, an agri-development and responsible-AI specialist: realism, evidence, safety,
     ethics.
   - A human-voice editor, who scores how human each answer reads and flags AI tells.
   - A fact auditor, who checks every claim against the repo, the brand rules and the sources.
4. **Qualify.** Critical audit issues are fixed first. A suggestion is kept only if it keeps
   facts true, passes the gate and doesn't lower another reviewer's score. Suggestions that
   would need a false claim are rejected (list below).
5. Repeat until both judges are ≥ 7.5, human-voice is ≥ 80 and the audit passes, or until
   gains stop.

## Scores by round

Judges score 1–10, where 5 is typical, 7 is top 25% and 8 is top 10%. "Advance" is the judge's
own estimate that the written part gets through Round 1.

| Round | Judge A (telecom) | Judge B (development) | Human-voice | Fact audit |
|---|---|---|---|---|
| r1: first Urbora draft | 7.2 · advance 38% · top 18% | 6.8 · advance 27% · top 25% | (cut off by rate limit) | (cut off) |
| r2: judges' fixes | 7.4 · advance 55% · top 13% | 7.1 · advance 40% · top 17% | 65 / 100 · 60% "looks AI" | **fail**: 7 critical |
| r3: audit + voice fixes | 7.4 · advance 55% · top 13% | (cut off) | 70 / 100 · 45% "looks AI" | (cut off; self-checked) |
| **final (r4)** | applies the r3 fixes; not re-scored | | | every r2 issue re-checked against the code |

Criteria detail (Judge A r3 / Judge B r2): Originality 6.6 / 6.6 · Problem relevance 7.6 / 7.4 ·
AI integration 7.4 / 7.6 · Impact 7.2 / 6.7 · Feasibility & clarity 7.4 / 7.2 · Responsible
AI 8.3 / 7.1.

## What the audit caught (true in v3 and v4 too, now fixed)

- "Phone numbers stored in a form that can't be read back" was false. The raw number is kept
  in `contacts`, because replies need it.
- "Doses from government guides" was false for the pest doses. Stem borer comes from
  BioProtection Portal, lentil from ApniKheti, mustard from a 2002 trial. Only sulphur and
  zinc are BAMIS (DAE). The form now says "cited sources", and Year 1 bases each dose on BRRI
  and DAE guides.
- Voice was implied to be live. No real call has completed a turn yet.
- GSMA says 26% of rural people *use* a smartphone, not "adults own". The census counts
  "not literate", not "cannot read".
- The photo model (PlantVillage) only really knows potato. The form now says so.

## Suggestions rejected, and why

- Mentioning or comparing with 16123: team rule.
- "Spray only past the guide's threshold": the triage asks how much of the field is hit, not
  a damage threshold, so we can't claim it. Logged as a product gap.
- "Fees on harvest sales only": the build charges dealers a commission. The form instead says
  the fee is flat and can't change the advice, which is true.
- "Nothing is stored without consent" as a blanket claim: narrowed to farm details (planned).

## What still holds the score down

1. **Originality (6.6)**: AI farm advice is a crowded field. Our edge is the combination:
   button phone plus guided questions that separate pests from soil shortages, a dose for his
   land or none, and action-first weather SMS.
2. **User evidence**: one farmer interview. Talking to five to ten more farmers before
   submitting, even by phone, and writing "we spoke to N farmers" is the cheapest big gain.
3. **Money**: no cost per answer, and no answer to who pays for calls and SMS beyond "free
   for farmers" as an ask. A measured cost per conversation from the prototype would help.
4. **Live proof**: voice isn't live yet. A real call working before the video is filmed turns
   "in testing" into "works".

## Files

- `ROUND1_FORM.md`: the answers (v5), Part 0 (farmer insights) and team notes (what's live,
  decisions to confirm, product gaps).
- `ROUND1_PASTE.txt`: paste-ready answers, one line per paragraph
  (`python scripts/form_check.py --paste`).
- `ROUND1_FORM_v4.md` and `ROUND1_FORM_v3.md`: earlier versions.
- `scripts/form_check.py`: the gate. `scripts/form_review_prompts.md`: the four reviewers.
