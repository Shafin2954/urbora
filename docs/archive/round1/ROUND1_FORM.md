# FutureMakers 2026 — Round 1 form answers (v5)

Category: Digital Inclusion & Education
Team: Team Uplift · University of Dhaka
Name: উর্বরা / Urbora · tagline স্বপ্ন ফলুক ("May your dreams bear fruit"). Story: `brand/BRAND-CORE.md` §3.

v5 (2026-09-30, after three review rounds). Rebuilt on the Urbora story: fertile soil is Bangladesh's gift and it is wearing
thin; the farmer can't tell a pest from a soil problem; everyone tells him something different;
expert help is far away. Nobody is blamed (BRAND-CORE framing rules). Earlier versions:
`ROUND1_FORM_v4.md`, `ROUND1_FORM_v3.md`. Review scores and the loop that produced this
version are in `ROUND1_REVIEW.md`. Run `python scripts/form_check.py` after every manual edit.

The answers are written to be pasted into plain form boxes, so they use no bold and few
bullets. Part 0 and the team notes are for us, not for the form.

---

## Part 0 — The farmer we are building for (not for the form)

A farmer in Parhail, Dinajpur, spoke to us by phone. Each thing he said points to a part
of the solution:

| What he told us | What it really means | What Urbora does about it |
|---|---|---|
| Crop and fertiliser choices come from what his father did and what the shopkeeper says | No neutral source he can check | Answers from government guides and real data. Urbora has nothing to sell |
| Every shop and every neighbour says something different | The pain is **too many answers and no one to trust**, not too little information | One clear answer, sent as an SMS he can show at the shop |
| He can't tell what the disease is, or describe it well enough for anyone to help | The hardest step is naming the problem: pest, disease, or the soil running short | Urbora asks step by step (crop, days since planting, which part, what it looks like) and tells pests from nutrient shortages. Smartphone users can add a photo |
| Wrong fertiliser amount and timing cost him harvests, mostly in boro | Money is lost on **how much** and **when** | The exact amount for his land in bigha and grams, plus reminders tied to his crop's stage |
| Costs are up and yield is down (50 maund last year, 30 this year) | The land's gift is wearing thin; every taka has to count | Balanced fertiliser for his soil, and the cost and expected profit before he spends |
| A bare storm warning is useless on a big paddy field | A warning is only useful when it says what to do | "Heavy rain on Thursday. Hold the urea and put it on the next dry day." |
| The agriculture office is far; he has gone once in his life | Expert help exists but distance keeps it out of reach | The expert comes to his phone, the way mobile banking brought the bank |
| "If you could ask and get a good answer directly, yes" | He would use it | Call, text or press keys, whatever he already does with his phone |
| Almost everyone in his village has a smartphone | Smartphones are common, but not everywhere | Works on both: smartphone, and basic button phone |

**One-line insight:** the farmer doesn't lack advice. He lacks advice he can trust, that
fits his own field, and that tells him exactly how much and when.

This is one farmer's account. Quote it as "a farmer in Dinajpur told us", never as a
statistic.

---

## Idea title

Urbora (উর্বরা): Bangla crop advice for each farmer's own land, even on a button phone

---

## Problem Statement (max 300 words)

Fertile soil is Bangladesh's biggest gift, but it is wearing thin. A farmer in Dinajpur told
us his harvest fell from 50 maund last year to 30 this year, while fertiliser kept getting
dearer.

He has plenty of advice, but no answer he can trust. When the crop falls sick, a pest, a
disease and a soil shortage can look alike, and the signs are hard to put into words. So he
asks around. The shopkeeper suggests one thing, a neighbour another, and his father always
used something else. The answers differ, and he has no way to check which one is right. In a
survey of 120 rice farmers, 69% got their pesticide advice from dealers (Rahaman et al.,
2018).

Nationwide, the soil is under strain. The Soil Resource Development Institute's map puts 78%
of the land below 1% organic matter (Prothom Alo, July 2026). A World Bank report this year
found that 95% of farmers use fertiliser in the wrong balance, and nine in ten give too
little sulphur. Getting the balance right could lift boro yields by a third (World Bank,
2026). Our farmer says wrong amounts and timing have cost him most in boro.

The knowledge exists, in guides and with agriculture officers, but for him the upazila
office is far away. He has been there once in his life. Farming apps could help, but they
expect reading, typing and mobile data. Only 26% of rural people use a smartphone (GSMA,
2024), and about 28% of rural people aged seven and over are not literate (Census 2022).
Farming still employs 45% of the country's workers (Labour Force Survey 2022).

---

## Proposed Solution (max 500 words)

Urbora (উর্বরা) brings expert crop advice to farmers on any phone, the way mobile banking
brought the bank to people's hands. On a smartphone the farmer can talk, type or send a
photo. Button phone users can call and speak Bangla, press keys, or text. Every answer also
comes as an SMS to keep and show at the shop. A son or daughter can read it out.

It helps with three questions.

1. What is wrong with my crop, and what do I do? Urbora doesn't expect the farmer to name
the problem. It asks, one step at a time: which crop, how many days since planting, which
part of the plant, what it looks like, and how much of the field is hit. It then works out
the likely cause: a pest, a disease, or a soil shortage such as sulphur or zinc in boro. The
treatment comes from cited sources, with the amount worked out for the farmer's land in
bigha and grams. It gives a dose only when one cause clearly fits, and every spray answer
says to wear a mask and gloves. If the case is unclear or widespread, it tells the farmer to
see the local agriculture officer, with the details in the SMS.

2. What should I do this week? Urbora remembers the farm: crop, sowing date, land size. So it
knows the crop's stage and what is due next. When the forecast clashes with the plan, it
says what to do: "Rain is forecast on your urea day. Put it on the next dry day."

3. What should I grow, and will it pay? Before a season, it ranks the crops that suit the
land and weather, and shows the cost, yield and profit for the farmer's plot, with a dated
plan and the right fertiliser for each stage.

Say Mahmud grows two bigha of boro. The centre shoots of some plants are
drying. The shopkeeper suggests one spray; a neighbour thinks the soil needs potash. Mahmud
calls Urbora from his button phone and answers a few questions. Urbora tells him it looks
like stem borer, not a soil problem, and gives the dose for his land: 20 grams of the
insecticide it names. He shows the SMS at the shop. Ten days later another SMS warns that
rain is due on his urea day, so he waits for a dry one.

For inputs, Urbora lists nearby dealers by price, distance and stock; none can pay to rank
higher. Farmers can also list their harvest for buyers. A small fee on sales, the same for
every dealer and product, aims to keep the advice free.

The fee can't change the advice. The diagnosis and dose come from fixed rules before any
shop is mentioned, and the fee is the same whatever the farmer buys. Other numbers come from
named sources such as weather forecasts and price statistics. When the data isn't there,
Urbora says "তথ্য যথেষ্ট নয়" (not enough information) rather than guess.

---

## How does AI enable your solution? (max 300 words)

Without AI, a button-phone user would face long keypad menus; with it, they can just say
what they see. AI does four jobs.

1. On a phone call, AI turns spoken Bangla into text and reads the answer back in a natural
voice, so a farmer who can't read can still use Urbora. We use Sarvam's speech model; on a
public Bangla test it made about a quarter as many errors as a leading general model. We test
it next on farmers' calls.

2. A farmer might say "এক বিঘা জমি, পানি জমে থাকে" (one bigha, water stands in it). A
language model (OpenAI's GPT-4o) turns everyday words like these into farm details and asks
only for what is missing.

3. On a smartphone, a photo model suggests likely problems from a leaf picture. It only knows
potato well so far, so the questions always check its guess.

4. AI finds the right passages in our sources and explains the answer in plain Bangla,
saying where it came from.

AI doesn't set the numbers or make the final call. The likely cause is matched by fixed rules
built on cited sources. Crop ranking, doses, costs and dates come from tested calculations,
and every number shown has a source.

Speech recognition can mishear a dialect, so key facts are read back for the farmer to
confirm, and the keypad is always there instead of speaking. When no single cause clearly
fits, Urbora gives no dose and tells the farmer to see the local agriculture officer. Farm
details are saved only with the farmer's agreement, and farmers are told that outside AI
services process their voice. Phone numbers sit in one table, used only to send replies;
identity uses a salted hash, and logs show just the last three digits.

---

## Impact Potential (max 300 words)

Urbora is built for smallholder farmers, including the ones a smartphone app would miss:
people with basic phones, people who read with difficulty, older farmers who would rather
talk than type, and women farmers who can ask from home. That covers the language, literacy
and access barriers this category names.

A farmer buys the treatment the crop needs, in the amount worked out for their land.
Fertiliser goes on at the right stage, on a dry day. The right dose instead of "a bit extra
to be safe" means less chemical in the soil and water, and whoever sprays breathes in less.
Before switching crops they see the likely cost and profit. They reach the shop with one
clear answer instead of three opinions.

Because answers name the cause, farmers can learn to spot problems themselves, and the SMS
history becomes the family's farm notebook.

Phone advice does change behaviour. A review in Science (Fabregas, Kremer and Schilbach,
2019) found that mobile agricultural information raised yields by 4% and the odds of
adopting recommended inputs by 22%, and that even cheap text and voice messages can change
what farmers do.

Crop-problem reports are also counted by district and crop, with no identity attached. With
enough farmers, those counts can warn agricultural authorities and researchers of pest
outbreaks early.

Every handset can make a call, send an SMS and open a USSD menu. Bangladesh has 189.8 million
mobile connections (BTRC, June 2026) and 16.9 million farm holdings (Agriculture Census
2019). One system answers many farmers at once, without a person per call.

In the pilot of about 500 farmers, we will compare spending, yield and harvest price with
villages chosen at random to join later, and an agronomist will check a sample of diagnoses
every month.

---

## Feasibility (Execution plan, 2–3 years) (max 300 words)

We built the first version at the IUT 12th ICT Fest Agentic AI Hackathon in July 2026 and
have kept working on it since. The prototype covers five crops: aman and boro rice, potato,
mustard and lentil. SMS works on real SIM cards. Voice calls and the USSD keypad menu run on
our simulator, and real calls are in testing.

Year 1, late 2026 to 2027: pilot. We will record consenting farmers in several regions so
Urbora learns local Bangla. An agronomist will review every crop-problem rule and
season plan, and we will base each dose on BRRI and DAE guides where they exist. Then about
500 farmers in two upazilas, recruited through a local NGO or farmer group, use it for one
boro season on Grameenphone's voice line, USSD short code and SMS, with verified input
dealers nearby.

Year 2, 2027 to 2028: more crops and vegetables, cited seed and pesticide prices, and
more agronomist-reviewed guidance. Harvest selling opens to verified buyers, with fees set
from the pilot's real costs.

Year 3, 2028 to 2029: expand district by district and offer the service to agribusinesses,
cooperatives and development programmes. We move ahead only when farmers keep coming back,
agronomists rate the answers safe, and the fees cover costs.

What we need: a voice line, USSD code and SMS that are free for farmers; cloud and AI
credits; agronomist time; a field partner; and the upazila agriculture office's support.

Dialects are the first risk, so we record regional voices, read key facts back and keep the
keypad. Wrong advice is the worst: no dose when Urbora is unsure, every answer logged, and
farmers texted if a mistake is fixed. For slow uptake, we use phone habits farmers already have and recruit through
people they trust.

---

## Differentiation (max 200 words)

Asking the shopkeeper or a neighbour is free and close, and they want to help. But their
answers differ, and the farmer can't tell which is right. Instead of one more opinion, Urbora
gives a sourced answer based on this farmer's crop, its stage, the size of the land and this
week's weather. Nobody can pay it to recommend anything.

Most farm apps need a smartphone and data. Photo apps judge from a picture, yet pests,
diseases and soil shortages can look alike, and a general chatbot can state a wrong dose with
total confidence. Urbora works on any phone. Its questions help tell those causes apart, and
every amount is calculated from published data, not made up by the model. Cases it can't
settle are referred to the local agriculture officer, with the details written down.

What is new: on a button phone, even a farmer who can't read is guided by voice or keypad to
a likely cause. Then they get an exact dose for their land with its source, or none when
unsure, an SMS to show at the shop, and weather warnings that say what to do.

---

## Video pitch (2 minutes)

Made in a separate session (`VIDEO_HANDOFF.md`). Idea from the team: a scene with two farmers
on the phone asking for advice, one on a smartphone and one on a button phone. We don't hear
their voices, only a voiceover or music. It shows that Urbora works on both.

---

## Team notes (not for the form)

**What changed from v4**

- Name: Urbora (উর্বরা). The story follows BRAND-CORE §3: the soil's gift wearing thin, "pest
  or soil shortage?", many voices, help far away, mobile banking as the comparison.
- **Nobody is blamed.** v4 said the seller "earns from what he sells" and "pushes" products,
  which BRAND-CORE forbids. The shop is now one of several well-meaning voices.
- **The agriculture office appears only as distance** ("far away; he has been there once") and
  as the place unclear cases are referred to, which is what the live SMS already does (SAAO
  line in `triage.py`). It is never described as failing. 16123 is still out. Judges in the
  review loop asked "why not the government helpline?"; we answer it without naming it: one
  cited answer, any phone, no one on duty needed, officers for hard cases.
- **Honesty fixes found by the fact audit (they were also wrong in v3/v4):**
  - Phone numbers are *not* hashed at rest. `contacts.msisdn` keeps the raw number because
    replies and alerts need it. Only the farm id is a salted hash, and logs show 3 digits.
  - Most pest doses are *not* from government guides. Boro stem borer (Mahmud's 20 g) comes
    from BioProtection Portal, lentil pod borer from ApniKheti, mustard aphid from a 2002 trial.
    Only the sulphur/zinc doses are BAMIS (DAE). The form now says "cited sources", and Year 1
    moves every dose onto BRRI/DAE guides.
  - No real voice call has completed a turn yet (README, LOG4 [16:40] and [01:05]). The form
    says voice runs on the simulator, with real calls in testing.
  - GSMA 2024 says 26% of rural people *use* a smartphone; "adults own" was not the source's
    wording. Census 2022: 28% are "not literate", not "cannot read".
- New evidence: the World Bank report (June 2026) on unbalanced fertiliser, and the SRDI
  organic-matter map (Prothom Alo, 21 July 2026).
- New from the judges: the fee never shapes advice; pesticide safety (mask and gloves, no dose
  unless one cause fits); consent before saving farm details and before recording voices; a
  500-farmer, one-season pilot on GP's network; a comparison with villages that join later;
  success gates before each expansion; texting farmers when a wrong answer is corrected.
- Answers are plain text for the form boxes: no bold and few bullets.

**Decisions the team must confirm (proposals in the text)**

- **Pilot size and design:** about 500 farmers, two upazilas, one boro season, comparison
  villages picked at random to join later. Change the numbers if you have a better plan.
- **Naming Grameenphone** as the pilot network (Feasibility). Remove if you'd rather stay
  operator-neutral.
- **Hackathon name:** the form says "IUT 12th ICT Fest Agentic AI Hackathon"; the full name is
  "IUT 12th ICT Fest Bdapps Agentic AI Hackathon" (bdapps is Robi's platform). If it won any
  prize, the FAQ requires disclosing the award too.

**Product gaps the form promises (build them or keep them in the plan)**

- Consent step before saving a farm profile and before recording voices.
- A spray-threshold question (how many dead shoots per square metre) before giving a pesticide
  dose. Today triage only asks how much of the field is hit.
- `dose_allowed()` still gives a dose when one strong cause sits next to a weaker one (boro
  stunted: zinc + BPH virus). The form says "only when one cause clearly fits".
- The voice agent says "সরকারি তথ্য অনুযায়ী" for every cited source (`backend/agent/loop.py`),
  including non-government ones. Fix before any demo call.
- Photo check (`backend/tools/leaf_diagnosis.py`) is not in the phone flows yet.
- Texting farmers when a wrong answer is corrected: the traces exist, but no job does this yet.
- The live SMS still ends with the 16123 line (`HOTLINE_LINE`, triage.py).

**Checks before submitting**

- **Prior work must be disclosed** (FAQ rule, disqualification risk). Keep the hackathon
  sentence in Feasibility.
- **Third-party contributions:** Sarvam (speech) and OpenAI GPT-4o (language) are named in the
  AI answer. District yield history comes from a supplied dataset whose citation is "pending
  verification" (README, AGRIBASE_CLEANING.md); be ready to say so if asked.
- **"20 grams for his two bigha"** is the system's real output for boro stem borer (75 g/ha ×
  0.2676 ha). Re-run the case before the video shows it.
- **"About a quarter of the errors"**: 6.9% vs 28.7% character error rate on 1,001 clips in a
  public Bangla benchmark (Sept 2026, LOG4). Sarvam is trained mostly on Indian Bengali.
- **World Bank 2026**: "Repurposing Agricultural Public Spending for Quality Growth and Jobs in
  Bangladesh's Agrifood System", launched 15 June 2026, reported by The Daily Star on 27 June
  2026. The 33% boro figure is the report's estimate, not ours.
- **SRDI 78% figure**: Prothom Alo, 21 July 2026, quoting the SRDI organic-matter map. A Dec
  2023 Prothom Alo piece gives about 79% (2020 data).
- **GSMA**: "The State of Mobile Internet Connectivity 2024" (October 2024): 26% of rural and
  41% of urban residents use smartphones.
- **Rahaman et al. 2018** is a small sample (120 farmers, three districts), and it measured
  pesticide advice specifically.
- **The 50 → 30 maund figures** are the farmer's own, and neither the crop nor the land size was
  stated. Keep them as his words.
- **Mahmud is an example farmer**, not a user. The form says so.
- **Competitors to know for Q&A:** iFarmer's Folon already has an AI voice agent, and DAE's
  BAMIS has AI disease detection. Our answer: any phone including button phones, questions
  that separate pests from soil shortages, advice tied to one farm's stage and land, weather
  warnings that say what to do, and cited, calculated numbers.
- **Name collision:** a Dhaka agri-fintech is listed as "Urbor" on Crunchbase. Always write
  "Urbora" in full and show the Bangla wordmark.
- **IP terms:** submitted ideas become Grameenphone's IP until the programme ends. All three
  members should read the T&C.
