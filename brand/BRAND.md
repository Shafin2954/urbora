> **Superseded in part (2026-09-30).** Name, story, tagline, palette v2 and fonts now live in
> `brand/BRAND-CORE.md`, which wins where this file disagrees. The trust psychology in §3 still holds.

# Brand system — v0.1 (draft for team approval)

**Purpose of this file.** The single reference for anything that carries the brand: the
website, the phone emulator, the video, the pitch deck, social posts. Build from
`brand/tokens/` rather than copying hex values around. Layout mirrors the team's WaffleUp
brand kit: `BRAND.md`, `VOICE.md`, `LOGO-BRIEF.md`, `NAMES.md`, `tokens/`, `assets/`,
`guidelines/`.

Status: **draft**. The name is not final (see `NAMES.md`); the logo will be made by the team
from `LOGO-BRIEF.md`. The product name in code still comes from `backend/branding.py` and
`frontend/src/branding.js`.

---

## 1. What the brand is for

**The farmer's problem, in his words** (FIELD_INSIGHTS.md, a farmer in Dinajpur):

- "Every shopkeeper says something different, everyone says something different; everyone is
  confused."
- He cannot tell what is wrong with his crop, and he cannot explain it to the seller.
- Mistakes with fertiliser amounts and timing cost him money.
- Costs keep rising while his yield falls.

**The brand's job.** Be the one answer a farmer trusts: clear, tied to *his* land, and
honest when it does not know.

**Purpose.** City people already get expert, data-backed help on their phones. We bring the
same help to every farmer, on any phone, in his own language, with no social barrier.

**Promise, one line.** *Ask once, get a straight answer, for your own land.*

## 2. Who we speak to

- **Primary.** Smallholder farmers, men and women, 25–60. Most have a phone and many a
  smartphone; many read with difficulty. They trust people, not institutions. They buy from
  a local seller they know by name.
- **Secondary.** The farmer's son or daughter, who reads the SMS and teaches the parent.
- **Also.** Judges, partners and agriculture officers, who need to see that it is serious,
  sourced and scalable.

## 3. Psychology: how trust is built here

Rural trust in Bangladesh is personal and earned slowly. People trust the *জানাশোনা মানুষ*,
the person who knows, has been right before, and has nothing to sell you. The brand
borrows that role. Each rule below comes from that.

| What builds trust | So the brand… |
|---|---|
| Nothing to sell | Never pushes a product. Dealer lists are ranked by price, distance and stock, and no one can pay to rank higher. It says so. |
| Being right, specifically | Gives numbers for *his* land in *his* units (bigha, মণ), with the source named. |
| Admitting limits | Says "তথ্য যথেষ্ট নয়" instead of guessing. Honesty about gaps raises trust in everything else. |
| Familiarity | Looks and sounds local: paddy, soil, monsoon sky, spoken Bangla, "ভাই". Not a foreign tech product. |
| Calm | Unhurried visuals, no alarm colours except for real warnings. The farmer is already stressed; the brand lowers the temperature. |
| Respect | Farmers shown as capable decision-makers, never as victims. No pity imagery. |
| Belonging | The colours of home, the green of the flag and the field, plus the telecom blue people already trust on their phones. |

**Archetype: the Sage with a Caregiver's heart.** Knows, explains simply, and cares whether it
worked. Not the Hero (no rescue stories), not the Jester (no jokes about crop loss), not the
Ruler (no lecturing).

## 4. Colour

Four brand colours plus neutrals. Names come from the Bengali landscape so the team can talk
about them in their own words.

| Role | Name | Hex | Use |
|---|---|---|---|
| **Primary** | শ্যামল · Shyamol Green | `#0F5C3B` | Identity, headings, primary buttons, large fields. The deep green of *শস্যশ্যামলা* Bengal and of the flag: "ours", growth, stability. |
| **Secondary** | আকাশ · Akash Blue | `#1570B8` | Anything about the phone: call, SMS, links, "try it". Echoes the telecom blue people know from Grameenphone, so the channel feels familiar. |
| **Accent** | ধানি · Dhani Gold | `#E3A92F` | Ripe paddy, prosperity (সোনার ধান). Small highlights: a key number, the active step, a badge. Never as text on white. |
| **Ground** | পলি · Poli Ivory | `#F6F4EC` | Page background, like river silt or rice paper. Softer than white in sunlight, still high contrast. |
| Ink | কালো মাটি · Kalo Mati | `#14221A` | All body text. Never pure black. |
| Warning | মাটি লাল · Mati Red | `#B34A24` | Real warnings only (rain before fertiliser, excluded crops). |

**Tints** (for surfaces and states): green 50 `#EAF3EC`, 100 `#D3E6D8`, 300 `#8DBB9C`,
600 `#1E7A4F`, 900 `#0A3F28`; blue 50 `#E8F2FA`, 100 `#CFE3F4`, 700 `#0F5690`; gold 50
`#FCF5E3`, 100 `#F7E6B8`, 700 `#A8761A`.

**Ratio.** About 60% ground and white, 25% Shyamol green, 10% Akash blue, and at most 5%
Dhani gold. Gold is special because it is rare.

**Contrast (WCAG 2.1 formula, computed by hand; re-check with a tool before print).**
- Shyamol green on white 8.1:1 and on Poli 7.3:1.
- Akash blue on white 5.2:1 and on Poli 4.7:1.
- Ink on Poli 15:1.
- White on Shyamol 8.1:1.
- Ink on Dhani gold 7.8:1, so gold buttons and badges take ink text, not white.
- Mati red on white 5.3:1.
- Gold 700 on white 4.0:1, so large text only. Plain gold is never used for text.

## 5. Typography

| Role | Face | Why |
|---|---|---|
| Display: headlines, big numbers, the wordmark's Bangla | **Tiro Bangla** (Google Fonts) | A Bangla serif with the authority of a respected newspaper or schoolbook. Serif reads as "considered and trustworthy", not "app". Use at 28px and up. |
| Text: body, UI, buttons | **Hind Siliguri** 400/500/600 | Clear Bangla and Latin at small sizes on cheap screens; tabular figures for money. |
| Fallback | Noto Sans Bengali | Ships on most Android phones. |
| Data and code (judge-facing only) | JetBrains Mono | Trace and provenance views. |

**Scale.** 14 / 16 / 18 / 22 / 28 / 36 / 48 / 64 px. Body text is 16–18px (never under 15 on
farmer screens). Line height is 1.6 for Bangla body text and 1.2 for display.

**Numbers.** Western numerals for computed values and tables, as in CLAUDE.md rule 10;
Bangla numerals are fine in running prose. Units always written out: বিঘা, মণ, কেজি, গ্রাম.

## 6. Shape, space and motion

- **Radius.** 10px for controls, 16px for cards, pills only for tags and badges. The shape is
  calm, not bubbly.
- **Lines, not shadows.** 1px borders in green 100. No drop shadows, gradients or blur
  (CLAUDE.md).
- **Space.** An 8px grid and generous margins. Elegance comes from what is left out.
- **Touch targets** at least 48px. One primary action per screen.
- **Motion.** Slow and explanatory only: a step appearing, an SMS arriving. 200–300ms,
  ease-out, and `prefers-reduced-motion` is respected.

## 7. Imagery

- **Real people in real light**: morning field light, hands on paddy, a phone held in a
  weathered hand, a son reading an SMS to his father. Eye-level camera; subjects look capable
  and busy, not sad.
- **Setting.** Northern and central Bangladesh paddy (boro and aman), tin-roof homes, a
  roadside input shop, a tea stall.
- **Never.** Pity framing, crying farmers, cracked-earth drought clichés, stock photos of
  Indian or African farms, futuristic "AI" imagery (robots, circuit brains, glowing blue
  holograms).
- **AI-generated footage** (e.g. Higgsfield) is disclosed as such in credits.
- **Icons.** 1.75px line icons with rounded ends, drawn from farm life: leaf, drop, sack,
  calendar, phone, SMS.

## 8. Voice (summary; full guide in VOICE.md)

Warm, plain, sure. Spoken Bangla, the way a trusted, educated neighbour talks. Short
sentences, specific numbers, no hype, no fear, no English jargon to farmers.

## 9. Files

| Path | What |
|---|---|
| `brand/tokens/brand-tokens.json` | Source of truth for colours, type and shape |
| `brand/tokens/brand-tokens.css` | The same as CSS custom properties (`--b-*`) |
| `brand/assets/logo/` | Logo files, once made (see LOGO-BRIEF.md) |
| `brand/assets/fonts/README.md` | Font sources and licences (all SIL OFL, Google Fonts) |
| `brand/guidelines/index.html` | Visual one-page guide (open in a browser) |
| `brand/NAMES.md` | Name candidates and the collision checks |
| `brand/VOICE.md` | How we speak and write |
| `brand/LOGO-BRIEF.md` | Brief for whoever makes the logo |
