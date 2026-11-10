# FutureMakers 2026 — Round 1 form answers (v4)

Category: Digital Inclusion & Education
Team: Team Uplift · University of Dhaka
Name: Urbora (উর্বরা) · tagline স্বপ্ন ফলুক ("May your dreams bear fruit"). Story: brand/BRAND-CORE.md §3

v4 (2026-09-29). Rebuilt from the farmer interview (`FIELD_INSIGHTS.md`). The old v3 is in
`ROUND1_FORM_v3.md`. The answers talk about the farmer and the solution, not the technology.
Word counts are checked against the form limits. Part 0 and the team notes are for us, not
for the form.

---

## Part 0 — The farmer we are building for (not for the form)

A farmer in Parhail, Dinajpur, spoke to us by phone. Each thing he said points to a part
of the solution:

| What he told us | What it really means | What Urbora does about it |
|---|---|---|
| He chooses crops and fertiliser by what his father did and what the shopkeeper says | His decisions have no neutral source | Answers from government guides and real data. Urbora has nothing to sell |
| Every shop and every neighbour says something different | The pain is **too many answers and no one to trust**, not too little information | One clear answer, sent as an SMS he can show at the shop |
| He can't tell what the disease is, or describe it well enough for anyone to help | The hardest step is describing the problem | Urbora asks step by step (crop, days since planting, which part, what it looks like). Smartphone users can add a photo |
| Wrong fertiliser amount and timing cost him harvests, mostly in boro | Money is lost on **how much** and **when** | The exact amount for his land in bigha and grams, plus reminders tied to his crop's stage |
| Costs are up and yield is down (50 maund last year, 30 this year) | Every taka spent has to count | Cost and expected profit shown before he spends |
| A bare storm warning is useless on a big paddy field | A warning is only useful when it says what to do | "Heavy rain is forecast. Put the urea on the next dry day." |
| "If you could ask and get a good answer directly, yes" | He would use it | Call, text or press keys: whatever he already does with his phone |
| Almost everyone in his village has a smartphone | Smartphones are common, but not everywhere | Works on both: smartphone, and basic button phone |

**One-line insight:** the farmer doesn't lack advice. He lacks advice he can trust, that
fits his own field, and that tells him exactly how much and when.

This is one farmer's account. Quote it as "a farmer in Dinajpur told us", never as a
statistic.

---

## Idea title

Urbora: one trusted farm advisor on any phone. Ask by voice, keypad or SMS, and get the
exact amount for your own land.

---

## Problem Statement (max 300 words) — 294 words

When a farmer in Bangladesh sees something wrong in the field, the advice he acts on
usually comes from the shop that sells the inputs. In a survey of 120 rice farmers in
Mymensingh, Tangail and Jamalpur, 69% took pesticide advice from dealers (Rahaman et al.,
2018). The seller earns from what he sells, not from whether it works.

A farmer in Dinajpur told us about three problems.

- **Too many answers, none he can trust.** Which crop to plant and which fertiliser to use
  come from what his father did and what the shopkeeper says. Every shop and every
  neighbour tells him something different.
- **He cannot name the problem.** When the crop falls sick he cannot tell what it is, or
  describe it well enough for anyone to help. So he does not know what to buy.
- **Amount and timing cost money.** Fertiliser put on at the wrong time or in the wrong
  amount has cost him harvests, most of all in boro season. His costs keep rising while
  his yield falls: 50 maund last year, 30 this year.

Even a storm warning is no use to him unless it says what to do: hold the urea, or delay
the spray.

People in cities can check a question against expert, data-backed answers on their phones.
That advantage has not reached the village. Farming apps and chatbots expect reading,
typing and mobile data, and their answers do not know his crop, his land or this week's
weather. Only 26% of rural adults own a smartphone (GSMA, 2024), and about 28% of rural
people aged 7 and over cannot read and write (Census 2022).

Agriculture employs 45% of Bangladesh's workforce (Labour Force Survey 2022). The farmers
with the least access can least afford a wrong decision.

---

## Proposed Solution (max 500 words) — 495 words

Urbora (উর্বরা) is a farm advisor that answers like a trusted agriculture expert who knows
the farmer's own field. It works on whatever phone the farmer has. On a smartphone they can
talk, type or send a photo of the sick plant. On a basic button phone they can call and
speak Bangla, press keys, or send an SMS. Every answer also arrives by SMS, to keep, show at
the shop, or have read out by family.

**It helps with three questions.**

1. **"What is wrong with my crop, and what do I do?"** Urbora does not expect the farmer to
   describe the disease. It asks one step at a time: which crop, how many days since
   planting, which part of the plant, what it looks like. Smartphone users can add a photo.
   The answer comes from government crop-protection guides, with the amount worked out for
   the farmer's own land in bigha and grams. If a case is unclear or serious, Urbora says
   so and passes it to a human agronomist with the details already collected.
2. **"What should I do this week?"** Urbora remembers the farm: the crop, the sowing date and
   the land size. From the sowing date it knows the crop's stage and what is due next. It
   messages the farmer when the forecast changes the plan, and says what to do: "Heavy rain is forecast. Put the urea on the next dry day."
3. **"What should I grow, and will it pay?"** Before a season or a crop switch, it ranks the crops that suit the land and the local weather, and shows the cost, expected
   yield and profit for the farmer's own plot, with a dated plan.

**Mahmud's story.** Mahmud grows boro on two bigha. Some of his young plants have dry, dead
centres. The shop suggests one spray and his neighbour another. He calls Urbora from his
button phone and answers a few questions in Bangla. Urbora tells him it looks like
stem borer, what to use, and exactly how many grams his two bigha need. He shows the SMS
copy at the shop and buys only what he needs. Ten days later an SMS
tells him heavy rain is coming and to hold his urea until the next dry day.

**Buying inputs and selling the harvest.** Urbora lists nearby dealers by price,
distance and stock; no dealer can pay to rank higher. After
harvest the farmer can list the crop and compare buyers' offers. Small fees on these sales
pay for the service, so advice stays free.

**Why farmers can trust it.** Urbora has nothing to sell. Its numbers come from named
sources: weather forecasts, government yield records and price statistics, and government
crop guides. When Urbora does not know, it
says "তথ্য যথেষ্ট নয়" (not enough information) instead of guessing.

**What changes for the farmer.** No more choosing between three opinions: one answer for his
own field, the exact amount and the right day, on the phone he already has.

---

## How does AI enable your solution? (max 300 words) — 288 words

AI does the parts that a fixed menu cannot:

1. **Listening and speaking Bangla.** AI turns a farmer's spoken Bangla on a phone call into
   text and reads the answer back in a natural voice. A farmer who cannot read can still use
   Urbora. We use a speech model built for Bangla, which on a public Bangla test made about
   one-quarter of the errors of a leading general-purpose model.
2. **Understanding everyday words.** A farmer might say "এক বিঘা জমি, পানি জমে থাকে". AI turns
   this into farm details and asks only for what is still missing.
3. **Looking at a photo.** On a smartphone, AI suggests the likely problem from a picture of
   the plant, and the step-by-step questions then confirm it.
4. **Explaining.** AI finds the relevant passages in government guides and explains the
   answer in plain Bangla, naming where it came from.

**Where we keep AI out.** AI does not do the maths or make the decision on its own. Crop
ranking, doses, costs and dates come from tested calculations on cited data. Every number a
farmer hears or reads comes from those calculations, and a number without a source is never
shown. AI never assumes a farm detail the farmer has not given. It asks.

**Responsible by design.**

- **Mishearing:** key facts are read back for the farmer to confirm, and pressing keys is
  always available instead of speaking.
- **Privacy:** phone numbers are stored in a form that cannot be read back, records show only
  the last three digits, and any pest counts we share carry no one's identity.
- **Knowing its limits:** when Urbora is unsure, it says so and hands the case to a human
  agronomist.
- **No paid influence:** no seller or company can pay to be recommended.

---

## Impact Potential (max 300 words) — 290 words

**Who benefits.** Smallholder farmers, including those on basic phones and those who cannot
read. Voice and keypad need no reading, and a family member can read the SMS later. These
are the barriers the category names: literacy, language and device.

**What changes for a farmer.**

- **Less money wasted.** They buy what the crop needs, in the amount their land needs,
  instead of what the shop pushes.
- **Fewer losses from timing.** Reminders follow the crop's stage, and a warning comes before
  rain washes the fertiliser away.
- **Safer fields.** The right dose instead of "a bit more to be safe" means less chemical on
  the land, in the water and on the person spraying.
- **Better choices.** Before switching crops, they see the expected cost and profit.
- **Confidence.** One clear answer they can show at the shop, instead of three opinions.

**Evidence that phone advice works.** A review in *Science* (Fabregas, Kremer and Schilbach,
2019) found that mobile agricultural information raised yields by 4% and the odds of
adopting recommended inputs by 22%, and that even text and voice messages on basic phones
change what farmers do.

**A wider benefit.** Every crop-problem report is counted by district and crop, with no
identity attached. With enough farmers, these counts become an early warning of pest
outbreaks for agricultural authorities and researchers.

**Reach.** Voice, SMS and keypad menus work on every handset, and Bangladesh has 189.8 million
mobile connections (BTRC, June 2026). One system can answer many farmers at once, so reach
grows without hiring a person for every call.

**How we will measure it.** Repeat use, alerts acted on, farmers' reported changes in spray
and fertiliser spending, and yield and price reported at harvest. An agronomist will check
a sample of answers for accuracy.

---

## Feasibility (Execution plan, 2–3 years) (max 300 words) — 285 words

**Starting point.** We are not starting from zero. We built the first version at the IUT
12th ICT Fest bdapps Agentic AI Hackathon (July 2026) and have since grown it into a working
prototype. It covers five crops (aman and boro rice, potato, mustard, lentil), with cited
data, and works over SMS, a keypad menu and voice calls.

**Year 1: pilot with farmers (late 2026 to 2027)**

- Record farmers from several regions to improve how well Urbora understands local Bangla.
- Have an agronomist review the crop-problem advice and season plans.
- Set up handover of hard cases to partner agronomists.
- Pilot in one or two upazilas through a mobile operator's voice line, keypad menu and SMS,
  recruiting farmers through a local NGO or farmer group.
- Sign up verified input dealers in the pilot area.

**Year 2: widen coverage (2027 to 2028)**

- Add more crops and vegetables, with cited seed and pesticide prices.
- Grow the guidance with agronomist-reviewed content.
- Open harvest selling to verified buyers.
- Set the marketplace fees from pilot cost data.

**Year 3: scale (2028 to 2029)**

- Expand district by district.
- Offer the service to agribusinesses, cooperatives and development programmes.
- Reuse the same phone service (voice, keypad, SMS) for other advice to people without
  smartphones, such as livestock care.

**Resources needed**

- Mobile operator access: voice line, keypad menu short code and SMS.
- Cloud and AI service credits.
- Agronomist time to review content.
- A field partner to recruit pilot farmers.

**Risks and responses**

- Dialects: regional recordings, key facts read back, and pressing keys as a fallback.
- Wrong advice: cited numbers only, gaps said out loud, and hard cases passed to a human.
- Slow adoption: the phone habits farmers already have, and recruitment through trusted local
  groups.

---

## Differentiation (max 200 words) — 170 words

**Versus the input seller.** The seller's advice is free, but he earns from what he sells.
Urbora has nothing to sell and nothing to push, no one can pay to be recommended, and it
says so when it does not know.

**Versus neighbours and habit.** They mean well, but their advice was made for another
field, another year and another weather. Urbora's answer is made for this farmer's crop, its
stage, their land size and this week's forecast.

**Versus farming apps and chatbots.** They need a smartphone, data and typing. General
chatbots can state a wrong dose with confidence. Urbora works by voice, keypad and SMS on any
phone. Every amount comes from a cited source, calculated rather than guessed.

**What is new** is the combination:

- the same advisor on a smartphone and on a button phone;
- questions that help the farmer describe the problem;
- the exact amount for their own land;
- weather warnings that say what to do;
- a rule that no number reaches the farmer without a source.

---

## Video pitch (2 minutes)

Made in a separate session (`VIDEO_HANDOFF.md`). Idea from the team: a scene with two farmers
on the phone asking for advice, one on a smartphone and one on a button phone. We don't hear
their voices, only a voiceover or music. It shows that Urbora works on both.

---

## Team notes (not for the form)

**What changed from v3**

- Built around the Dinajpur interview. The problem is now confusion, having no one to trust,
  not being able to describe the problem, and losses from amount and timing. The main villain
  is no longer only the seller.
- **16123 and the extension office are gone** (team rule). Hard cases now go to "a human
  agronomist" or "partner agronomists".
- The farmer is **Mahmud** (boro on two bigha, stem borer, button phone), matching the
  storyboards. Rahima and the brown leaf spots are gone: `triage.py` has no rule for that
  case.
- Smartphone and button phone are presented as equals, with the photo check added for
  smartphones.
- Marketplace cut to one paragraph. The technical detail (the tool count, the Sarvam figures)
  is cut down to plain words.

**Checks before submitting**

- **Prior work must be disclosed** (FAQ rule, disqualification risk). The July hackathon is
  named in Feasibility → Starting point. Keep that sentence.
- **Photo check.** It is prototyped (`leaf_diagnosis.py`) but not part of the phone flows.
  The form describes it as part of the idea. Don't show it in the demo as finished unless it
  works end to end.
- **Human agronomist handover.** The live SMS still points to 16123 (`HOTLINE_LINE`,
  triage.py). No partner agronomist is signed up yet. It is in the Year 1 plan, so the
  wording is fine for an idea round.
- **"One-quarter of the errors"** is from the Sarvam test in v3: 6.9% vs 28.7% character
  error rate on 1,001 clips (Sept 2026). Be ready to cite it.
- **Smartphone figure.** GSMA 26% is rural *adults owning* one. BBS reports much higher
  *household* access. Keep "adults own" word for word.
- **Rahaman et al. 2018** is a small sample (120 farmers, three districts).
- **The 50 → 30 maund figures** are the farmer's own, and land size was not stated. Keep them
  as his words, not a statistic.
- **Competitors to know for Q&A:** iFarmer's Folon already has an AI voice agent, and DAE's
  BAMIS has AI disease detection. Our answer: any phone including button phones, advice tied
  to one farm's stage and land, weather warnings that say what to do, and cited, calculated
  numbers.
- **IP terms:** submitted ideas become Grameenphone's IP until the programme ends. All three
  members should read the T&C.
