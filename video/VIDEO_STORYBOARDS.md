# Round 1 video: three storyboards (Mahmud)

Draft, 2026-09-29. Three versions for the team to choose from. Nothing is shot yet.

**Hard limits (docs/archive/round1/FUTUREMAKERS_BRIEF.md):** MP4, 2:00 or less, 300 MB or less, Bangla or English,
one member may present, screen recordings allowed. All three versions below are planned to run
about 1:55, which leaves a few seconds of margin.

**Scored on:** originality, problem relevance, AI integration, impact, feasibility, video
quality, responsible AI. Each version below marks where it covers each criterion.

---

## The farmer: Mahmud (replaces Rahima)

Mahmud is a boro farmer on **2 bigha**. He has a button phone, and his son reads the SMS for
him at the shop. He is a made-up example, and the video labels him that way ("নাট্যরূপ /
dramatization").

### His problem has to change, because the code cannot answer the old one

The form's journey says the farmer finds **brown spots on boro leaves** and gets a dose. I
checked `backend/kb/triage.py`, and **boro + leaf + spots has no rule.** The real system would
answer "তথ্য যথেষ্ট নয়" and hand him over. Filming the old journey would show a reply our own
system cannot give.

Boro problems the system answers **with a dose scaled to his land**:

| Problem he sees | Days after planting | System answer (source) |
|---|---|---|
| **Dead centre shoot, "ডগা শুকানো" (deadheart)** | 20–54 | Stem borer (মাজরা পোকা). Virtako 40WG, 75 g per hectare, scaled by code to 2 bigha (`boro_pest_stemborer`) |
| Yellow leaves | any | Sulphur deficiency. Extra 8 kg gypsum per bigha (`boro_nutrient_topdress`), no spray |
| Stunted plants | any | Zinc deficiency. 1.5 kg zinc sulphate per bigha |

**Recommendation: stem borer / deadheart.** It is a well-known boro pest. The dose is one
the seller could get wrong. And the answer carries the safety lines (show the SAAO before
spraying, wear a mask and gloves, 16123), which shows responsible AI on screen without anyone
having to explain it.

**Rule for the shoot:** run Mahmud's case through the real system first and use **the exact
text and gram figure it returns.** No number in the video is typed by hand.

The rain alert also exists (`channels/alerts_job.py`). Its real wording is: "{date}-এ {mm}
মিমি বৃষ্টির পূর্বাভাস (Open-Meteo)। '{task}' কাজটি পরের শুকনো দিনে করুন।" It says "the
next dry day", not "wait two days" as the form does. Film the real SMS.

---

## Version A — "শুক্রবার, রাত ৯টা" (One Friday night): a story film

**Idea:** One night in one farmer's life. The facts appear on screen as the story reaches
them. It should feel like a short film that happens to be a pitch.
**Needs:** someone to play Mahmud (a relative or a real farmer who agrees to it), a boro field,
a button phone, a night shoot, and a lamp or torch. Voice-over: one team member in Bangla, with
English subtitles.
**Strong on:** problem relevance, video quality, impact. **Weaker on:** showing the technology
in depth.

| Time | Picture | Sound / words (Bangla VO, English subs) |
|---|---|---|
| 0:00–0:08 | Dark. A torch beam moves over boro plants. Close-up: a dry, dead centre shoot. Caption: **শুক্রবার, রাত ৯:১০** | Crickets. Mahmud (quietly): "এ কী হলো..." |
| 0:08–0:14 | Mahmud looks at his button phone. Title card: **"কাকে ফোন করবেন?"** | VO: "মাহমুদের দুই বিঘা বোরো। আজ রাতে তাঁর প্রশ্নের উত্তর কে দেবে?" |
| 0:14–0:22 | Clock graphic: 16123 is **8 am–8 pm, closed Friday, Saturday and holidays** (AIS). The Friday tile turns grey. | VO: "সরকারি কৃষি কল সেন্টার আজ বন্ধ।" |
| 0:22–0:30 | A smartphone app icon crossed out. **26%** of rural adults own a smartphone (GSMA 2024). **28%** of rural people cannot read (Census 2022). | VO: "অ্যাপ চালাতে লাগে স্মার্টফোন, ডেটা, আর পড়তে জানা।" |
| 0:30–0:40 | Next morning: the pesticide shop. The seller holds out a bottle. **69%** get pesticide advice from dealers; **7.5%** from extension officers (Rahaman et al. 2018). | VO: "তাই বেশিরভাগ কৃষক শোনেন দোকানির কথা — যিনি লাভ করেন বিক্রি থেকে।" |
| 0:40–0:44 | **Rewind** effect back to Friday night. The phone in his hand again. | VO: "এবার একই রাত, অন্যভাবে।" |
| 0:44–1:10 | **Real call** through the voice bridge. Mahmud speaks. The agent asks for days since planting and which part is affected, then gives the cause and the dose for 2 bigha (real audio, Bangla subtitles on screen). | Real call audio. The agent's voice is the product itself, so the viewer hears the AI working. |
| 1:10–1:18 | The button phone buzzes: **the real SMS** arrives. Next day his son reads it aloud at the shop, and the seller nods. | The son reads the SMS aloud. |
| 1:18–1:28 | Caption **১০ দিন পর**. Another SMS: the rain alert before urea. Mahmud puts the urea sack back down. | VO: "বৃষ্টির আগেই সতর্কবার্তা, সারের টাকা বাঁচল।" |
| 1:28–1:45 | Clean motion graphic: **AI শোনে, বোঝে, বুঝিয়ে বলে** → **হিসাব করে পরীক্ষিত কোড, উৎস সরকারি গাইড** → **না জানলে বলে "তথ্য যথেষ্ট নয়", পাঠায় 16123-এ.** A short shot of the provenance graph. | VO: explains the division of work in three short lines. |
| 1:45–1:55 | **18.98 কোটি** mobile connections (BTRC 2026). Year-1 pilot: 1–2 upazilas. Logo, name, tagline, team name. | VO: "যেকোনো ফোনে, যেকোনো দিন। Agrosfeer." |

**Risk:** the night shoot and the acting. A bad actor costs more than no actor. Fallback: film
only hands, the phone and the field, and never show his face.

---

## Version B — "তিন পথ, একই উত্তর" (Three ways in): the proof demo

**Idea:** No acting. Everything the judge sees is real software running on real phones. The
same crop problem comes in by **voice, keypad and SMS**, and the same answer comes back each
time. The message is that no farmer is locked out by reading, device or data.
**Needs:** screen and phone recordings only, plus HyperFrames motion graphics. A presenter can
open and close on camera, or it can be VO only.
**Strong on:** AI integration, feasibility, originality of the channel mix. **Weaker on:**
emotion.

| Time | Picture | Words |
|---|---|---|
| 0:00–0:10 | Hook: a button phone on a table. Text builds up: "কোনো অ্যাপ নেই। ইন্টারনেট নেই। পড়তে জানা লাগে না।" | VO reads it. |
| 0:10–0:30 | Problem in three fast cards: seller 69% / 16123 hours / 26% smartphone + 28% cannot read. Mahmud is named on the last card: "মাহমুদ, ২ বিঘা বোরো, বাটন ফোন" | VO, one sentence per card. |
| 0:30–0:40 | The phone screen splits into **three phones.** Labels: **কল করে বলুন · বাটন চাপুন · SMS পাঠান** | "মাহমুদ তিনভাবে জিজ্ঞেস করতে পারেন।" |
| 0:40–1:05 | Three real recordings play side by side, then one at a time: (1) the voice call, (2) the USSD menu walk (**labeled "simulator"**, CLAUDE.md rule 13), (3) an SMS in, an SMS out on the real SIM. All three end on the **same diagnosis and the same gram figure.** | Light VO. Let the screens talk. |
| 1:05–1:15 | The rain-alert SMS arrives unprompted. Caption: "মাহমুদ জিজ্ঞেস করেননি — Agrosfeer আগে জানিয়েছে।" | VO. |
| 1:15–1:35 | "Behind the answer": the provenance graph animates. Tool calls light up (weather → triage table → dose scaler → SMS template). Caption: **AI বেছে নেয় কোন টুল; সংখ্যা আসে কোড থেকে.** The "তথ্য যথেষ্ট নয়" handover shown for an unknown symptom. | VO: the "where we keep AI out" point. |
| 1:35–1:45 | Dealer list (**labeled demo data**) ranked by price, distance and stock. "দোকানদার টাকা দিয়ে আগে আসতে পারে না।" How the service pays for itself, in one line. | VO. |
| 1:45–1:55 | Built at the IUT hackathon in July 2026 (**prior work, disclosed**) → Year 1 upazila pilot → scale. Logo. | VO. |

**Risk:** it can feel like a feature tour. The three-phone split is what holds it together.
Test it at phone size, because judges may watch on a phone.

---

## Version C — "একই রাত, দুই সকাল" (Same night, two mornings): a split-screen parable

**Idea:** The screen is split down the middle. **Left: Mahmud without Agrosfeer. Right: Mahmud
with it.** Both start from the same Friday night and the same dead shoot, then drift apart:
one wrong spray against one right dose, urea washed away against urea saved. At the end both
sides meet at harvest. The contrast carries the argument, so very little narration is needed.
**Needs:** illustration or motion graphics (HyperFrames); no actors. The right-hand side uses
real phone recordings as inserts. Characters can be simple flat illustrations in the earthy
palette.
**Strong on:** originality, clarity, video quality. **Weaker on:** proof, unless the real
inserts get enough screen time.

| Time | Left: without | Right: with Agrosfeer |
|---|---|---|
| 0:00–0:10 | Same frame on both sides: Friday 9 pm, torch, dead centre shoot. Title: "একই রাত।" | (mirror) |
| 0:10–0:22 | He dials 16123, hears the closed message, and waits for morning. | He dials Agrosfeer. **Real call audio** (short). |
| 0:22–0:35 | At the shop the seller sells a bottle "to be safe". **69%** appears. | **Real SMS**: stem borer, the dose for 2 bigha, SAAO and mask lines. |
| 0:35–0:48 | He sprays the wrong product. The pest keeps spreading. A ৳ counter climbs. | He buys the right amount, and his son checks the SMS at the shop. |
| 0:48–1:00 | Day 10: he spreads urea, it rains, and the urea washes off. The ৳ counter climbs again. | Day 10: the **real rain-alert SMS.** He waits for the dry day. |
| 1:00–1:10 | Harvest: a smaller pile. | Harvest: a healthy pile. **No invented yield or taka figures**: piles only, no numbers (rule 2). |
| 1:10–1:15 | The split line dissolves into one frame. | |
| 1:15–1:40 | Full screen: how it works in three beats (AI listens and explains → code calculates from cited sources → it says what it does not know and hands over to 16123). Short provenance-graph insert. Three channel icons: call, keypad, SMS. | |
| 1:40–1:55 | Reach (**18.98 কোটি** connections), Year-1 pilot, prior work disclosed, logo. | |

**Risk:** the ৳ counters on the left would be illustrative numbers, which breaks rule 2 in
spirit. **Use no numbers on the left side at all**, only visual loss (bottle, rain, small
pile). A judge could otherwise ask "where does that ৳ figure come from?"

---

## Side by side

| | A: story film | B: proof demo | C: split parable |
|---|---|---|---|
| Emotional pull | Highest | Low | High |
| Proof it is real | Medium (one real call) | **Highest** | Medium |
| Originality | Medium | Medium–high | **Highest** |
| Shooting effort | **High** (actor, night, field) | **Low** (screens only) | Medium (illustration work) |
| Failure risk | Bad acting or audio | Feels like a feature tour | Illustration takes too long |
| Time to finished cut | ~2 days | ~1 day | ~1.5 days |

**My pick: a blend of C's structure and B's proof.** Keep the split-screen contrast as the
spine, with originality and emotion and no actor. Make every right-hand beat a **real
recording** (call, SMS, rain alert), so the "with" side is proof, not illustration. If the team
can film a real farmer's hands and field, use that footage for the shared opening frame
instead of illustration.

## Applies to every version

- **Bangla VO, English subtitles.** A human voice from the team for the narration. The agent's
  own voice in the call is Sarvam TTS, which is real product audio. (Brag's Kokoro TTS has no
  Bangla voice; LOG4 [02:45].)
- **Honesty labels on screen:** Mahmud = "নাট্যরূপ / dramatization"; USSD = "simulator";
  dealers/buyers = "demo data"; call and SMS = real. Rule 13: never present simulated as live.
- **Sources as small on-screen citations** under every statistic (the same sources as the form).
- **Prior work disclosed** (the July hackathon), which the FAQ requires.
- **Product name** from `backend/branding.py` (currently Agrosfeer). Do not bake it into ten
  places; keep it in one title layer so a rename is a one-line change.
- **Numbers inside the video** are the ones the system returns. Nothing is typed by hand.
- Renderer: HyperFrames through brag (LOG4 [02:45]); FFmpeg for the final mux, 1080p, well
  under 300 MB.

## Decisions the team needs to make

1. Which version (or blend)?
2. Is there a real farmer or field to film? This decides between A and C for the opening.
3. Who narrates, and should they appear on camera?
4. Should the form's journey change to Mahmud and stem borer too, so the form and the video tell the same story?
