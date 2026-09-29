# FutureMakers 2026 — Round 1 form answers (v3)

Category: Digital Inclusion & Education
Team: Team Uplift · University of Dhaka

v3 (2026-09-29). Written around the idea, the plan and the farmer's problem. Round 1 asks for
an idea, not a finished product, so the answers describe what Agrosfeer does and how we will
take it to farmers. Word counts are checked against the form limits. Team notes at the bottom
are not for the form.

---

## Idea title

Agrosfeer: a neutral farm expert on any phone. Call, press keys or text, any day of the week.

---

## Problem Statement (max 300 words)

When a farmer in Bangladesh finds spots on the leaves or insects in the field, the person they
can reach that day is usually the pesticide seller. In a survey of 120 rice farmers in
Mymensingh, Tangail and Jamalpur, 69% took pesticide advice from dealers and 7.5% from
government extension workers (Rahaman et al., 2018). A seller earns from what he sells, not from
whether it works. The result is the wrong spray, the wrong dose, or the right treatment too late,
and the farmer pays twice: once at the shop and again at harvest.

Neutral advice exists, but it is hard to reach when the decision has to be made:

- The government Krishi Call Center (16123) answers from 8 am to 8 pm and is closed on Fridays,
  Saturdays and government holidays (AIS). It receives about 200 calls a day (BSS, 2025),
  for a country with 16.88 million farm holdings (Agriculture Census 2019).
- Farming apps and AI chatbots need a smartphone, mobile data and typing. Only 26% of rural
  adults own a smartphone (GSMA, 2024), and about 28% of rural people aged 7 and over cannot read
  and write (Population and Housing Census 2022).
- The advice that does arrive is general. It does not know the farmer's crop, when it was sown,
  how much land there is, or that heavy rain is forecast on the day urea is due.

Agriculture still employs 45% of Bangladesh's workforce (Labour Force Survey 2022). The
farmers with the least access, those with basic phones and limited reading, are the ones who
can least afford a wrong decision.

---

## Proposed Solution (max 500 words)

Agrosfeer is a phone number that works like a neutral agriculture officer. A farmer can reach
it from any phone, including a basic button phone with no internet, at any hour and on any day.
They can call and speak Bangla, call and press keys, send an SMS, or dial a USSD menu. Every
answer also arrives by SMS, so it can be kept, or read out by someone in the family.

**It does three jobs for the farmer.**

1. **"What is wrong with my crop?"** The farmer gives the crop, days since planting, the affected
   part and what it looks like, by voice or by pressing keys. The answer comes from government
   guides (AIS, BRRI, BARC), with the dose worked out for the farmer's own land in bigha. When a
   case is serious or unusual, Agrosfeer hands it to an agriculture officer or 16123 with the
   farm details already collected, so the farmer does not have to explain twice.
2. **"What should I do this week?"** It remembers each farm: crop, sowing date, land, soil and
   water. From the sowing date it knows the crop's stage and what is due next. It watches the
   16-day forecast and sends an SMS first when the weather clashes with the plan, for example
   when heavy rain is forecast on the day urea is due.
3. **"What should I grow, and will it pay?"** Before a season, and especially before switching
   crops, it ranks the crops that suit the land and local weather, and gives a dated season
   calendar with itemised cost, expected yield and profit for the farmer's own land.

**A farmer's journey.** Rahima grows boro on two bigha. At 9 pm on a Friday she sees brown
spots on the leaves. She dials Agrosfeer from her button phone and describes the problem in
Bangla. It asks two short questions, names the likely cause and tells her the dose for her two
bigha, then sends the same advice by SMS so her son can check it at the shop. Ten days later,
before she spreads urea, an SMS warns her that heavy rain is due and suggests waiting two days.

**Inputs and harvest.** When the farmer needs inputs, Agrosfeer lists nearby dealers ranked by
price, distance and stock; dealers cannot pay for a higher place. After harvest, farmers can
list produce by SMS and accept buyer offers. Small fees on these sales fund the service, so
advice stays free for farmers.

**Why the numbers can be trusted.** The AI listens, talks and explains, but it does not calculate
or decide. Crop ranking, costs, doses and dates come from tested code working on cited sources:
live Open-Meteo weather, district yield records, BBS price statistics and government guides.
If a source is missing, the farmer hears "তথ্য যথেষ্ট নয়" (not enough information) instead of
a guess.

---

## How does AI enable your solution? (max 300 words)

AI does the parts that a fixed menu cannot:

1. **Listening and speaking Bangla.** Speech-to-text turns telephone-quality Bangla into text,
   and text-to-speech reads the answer back, so a farmer who cannot read can still use the
   service. We use Sarvam, a Bangla-specialised model. On a public Bangla benchmark of 1,001
   clips (September 2026) its character error rate was 6.9%, against 28.7% for a leading
   general-purpose model.
2. **Understanding everyday descriptions.** A farmer might say "এক বিঘা জমি, পানি জমে থাকে".
   A language model turns this into a structured farm profile and asks only for what is
   missing.
3. **Choosing the steps.** One question can need a location lookup, the forecast, crop ranking,
   costing and a calendar. An AI agent decides which of its 17 tools to call and in what order.
4. **Explaining.** It retrieves passages from cited government sources and explains the result
   in plain Bangla, naming the facts behind it.

**Where we keep AI out.** The model never computes a number, ranks crops or picks a pest
diagnosis. Those come from deterministic, tested code. In SMS, USSD and voice replies, every
figure is inserted from tool output through fixed templates, and a figure without a source is
not shown. The agent never assumes a farm detail the farmer has not given; it asks.

**Responsible by design.**

- **Mishearing:** key facts are read back for the farmer to confirm, and the keypad menu is
  always there as an alternative to speech.
- **Privacy:** phone numbers are stored as salted hashes, logs show only the last three
  digits, and crop-problem counts shared with the government carry no identity.
- **Knowing its limits:** when it is unsure, it says so and hands the case to a human expert.

---

## Impact Potential (max 300 words)

**Who benefits.** Smallholder farmers on basic phones, including those who cannot read. Voice
and keypad need no reading, and a family member can read the SMS copy later. These are the
barriers the category names: literacy, language and device. Extension workers can use the web
version to follow more farmers.

**What changes for a farmer.** Before paying for a spray, they can check what the government
guides say, at any hour, with the dose for their own land. During the season they get
reminders, and a warning before rain washes away a fertiliser application. Before switching
crops, they see the expected cost and profit.

**Evidence that phone advice works.** A review in *Science* (Fabregas, Kremer and Schilbach,
2019) found that mobile agricultural information raised yields by 4% and the odds of adopting
recommended inputs by 22%, and that even basic-phone text and voice messages change farmer
behaviour. In a randomised trial of a phone advisory line in Gujarat (Cole and Fernando, 2021),
farmers adopted recommended inputs.

**A signal no call centre collects.** Every crop-problem report is counted by district and crop,
with no farmer's identity attached. With enough farmers, these counts become an early warning
of pest outbreaks for the Department of Agricultural Extension.

**Reach and cost.** Voice, SMS and USSD work on every mobile handset, and Bangladesh has 189.8
million mobile connections (BTRC, June 2026). Software answers many calls at once, so capacity
grows with servers rather than staff. Hard cases go to 16123 with the farm details collected,
so human experts spend their time where it matters most.

**How we will measure it.** Repeat use, alerts acted on, handover rate, farmers' reported
changes in spraying and fertiliser use, and yield and price reported at harvest. An
agronomist will review a sample of answers for accuracy.

---

## Feasibility (Execution plan, 2–3 years) (max 300 words)

**Starting point.** We are not starting from zero. We built the first version at the IUT 12th
ICT Fest bdapps Agentic AI Hackathon (July 2026) and have since grown it into a working
prototype: an AI agent with 17 tools, cited data for five crops (aman and boro rice, potato,
mustard, lentil), and SMS, USSD and voice access.

**Year 1: pilot with farmers (late 2026 to 2027)**

- Tune Bangla speech recognition with recordings from farmers in several regions.
- Have an agronomist review the crop-problem guidance and season plans.
- Connect handover to 16123 and local agriculture officers.
- Pilot in one or two upazilas over an operator voice line, USSD short code and SMS, with
  farmers recruited through the agriculture office or an NGO.
- Onboard verified input dealers in the pilot area.

**Year 2: widen coverage (2027 to 2028)**

- Add more crops and vegetables, with cited seed and pesticide prices.
- Grow the knowledge base with agronomist-reviewed content.
- Open the produce marketplace to verified buyers.
- Set marketplace fees from pilot cost-per-conversation data.

**Year 3: scale (2028 to 2029)**

- Expand district by district.
- Offer the service to government extension and agribusinesses (B2G and B2B).
- Reuse the phone layer (voice, keypad, SMS) for other advice to people without smartphones,
  such as livestock or maternal health.

**Resources needed**

- Operator access: voice line (IVR), USSD short code and SMS.
- Cloud and AI API credits for speech and the language model.
- Agronomist time for content and review.
- A field partner to recruit pilot farmers.

**Risks and responses**

- Dialects: regional recordings, key facts read back, keypad fallback.
- Wrong advice: cited numbers only, gaps disclosed, hard cases handed over.
- Slow adoption: familiar channels, recruitment through extension workers.

---

## Differentiation (max 200 words)

**Versus the pesticide seller.** The seller's advice is free, but he earns from what he sells.
Ours comes from government guides, no one can pay to be recommended, and it says so when it
does not know.

**Versus 16123.** We extend it rather than replace it. 16123 is open 8 am to 8 pm, closed on
Fridays, Saturdays and holidays, and hears from a farmer only when the farmer calls. Agrosfeer
answers at any hour, remembers the farm, sends a written SMS and warns the farmer first when
the weather threatens the plan. Hard cases go to 16123 with the details already collected.

**Versus apps and chatbots.** They need a smartphone, data and typing, and general chatbots can
state a wrong dose with confidence. Agrosfeer works by voice, keypad and SMS on a basic phone,
and every number comes from a cited source through tested code.

**What is new** is the combination: Bangla voice and keypad access on a button phone, advice
tied to one farm and its crop stage, warnings sent before the damage, and a rule that no
number reaches the farmer without a source.

---

## Video pitch (2 minutes)

To be made in a separate session, following this framing: the farmer's problem first, then
Rahima's journey, then the plan.

---

## Team notes (not for the form)

**What changed from v2.** The answers now describe the idea and the plan. Removed the
"Current status" paragraph and the "Limitations and risks" paragraph; what we have not built
yet is in the Year 1 plan, not written as a weakness. Added a farmer's journey (Rahima is a
made-up example, not a real user). The safety points are now under "Responsible by design",
because the judges score responsible AI use and the FAQ asks us to explain risks.

**Checks before submitting**

- **Prior work must be disclosed** (FAQ rule, disqualification risk). The July hackathon is
  named in Feasibility → Starting point. Keep that sentence.
- **Smartphone figure conflict.** We quote GSMA 26% rural (individual ownership). BBS Q1 FY26
  reports 69% rural smartphone (almost certainly *household* access). Keep the words "adults
  own" exactly, and be ready to explain the difference.
- **Rahaman et al. 2018** is 120 farmers in three districts, a small sample. A second source
  (77.88% follow dealer advice) was seen in search results but not opened; open it before
  quoting.
- **16123 cost:** AIS says 25 paisa/min + VAT, BSS and FAO say free. We do not quote a cost.
- **IP terms:** submitted ideas become Grameenphone's IP until the programme ends
  (FUTUREMAKERS_BRIEF.md). All three members should read the T&C.
- **Be ready for Q&A:** if judges ask what already works, SMS runs on real SIM cards, USSD
  runs on the bdapps-format simulator, and voice answers real calls through an Android bridge.
  Marketplace rows are demonstration data. Say this plainly if asked.
