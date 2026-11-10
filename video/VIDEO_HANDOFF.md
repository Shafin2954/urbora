# Video session handoff (Round 1, 2-minute pitch)

For a second Claude Code session that works only on the video. The app/website work happens
in the first session; do not edit `frontend/` or `backend/` from the video session.

## Paste this as the first message of the new session

> You are working on the Round 1 pitch video for our FutureMakers 2026 entry (repo
> D:\Projects\TeamFixeth_AgriSense, branch futuremakers). Read CLAUDE.md, video/VIDEO_HANDOFF.md
> (all of it), docs/product/FIELD_INSIGHTS.md (a real farmer interview: build the story on it),
> brand/BRAND-CORE.md (name উর্বরা / Urbora, tagline স্বপ্ন ফলুক, story, colours, type;
> it overrides older brand files), brand/VOICE.md, docs/archive/round1/FUTUREMAKERS_BRIEF.md and docs/archive/round1/ROUND1_FORM.md
> first. Another session is rebuilding
> the website at the same time — do not touch frontend/ or backend/; your files go in
> `video/`. Step 1: draw storyboard v2 as a published artifact page (sketch panels, one per
> shot, timecodes, Bangla lines, on-screen text, which tool makes each shot) and wait for
> my approval. Do not generate any footage before I approve. Ask me whatever you need
> (logo files, voice, music).

## What the video must say

**Updated 2026-09-30: brand/BRAND-CORE.md §3 is the story.** In short: Bangladesh's
fertile soil is its gift; yields are falling on the same land; the farmer can't tell which
disease or nutrient gap is the cause and gets different advice from everyone; the expert
help exists but the agriculture office is far. Mobile banking brought the bank to people's
hands; উর্বরা brings the agriculture expert to the farmer's phone. It is forward-looking,
not "getting the old days back". The points below still hold where they don't conflict.

- **The problem.** A farmer's advice today comes from the person selling him the medicine or
  fertiliser. The seller pushes what earns him the most, or a product that does not match
  the problem. Expert, data-backed advice, the kind city people already get on a
  smartphone, does not reach the farmer.
- **What we give.** Expert advice that works the numbers out for his own land, from cited data.
  Any time of day. No social barrier: no need to know an officer or feel awkward asking.
  Works on any phone (call, keypad, SMS). Built to scale to every farmer.
- **Why it counts as digital inclusion.** Rural people get the same AI advantage city people
  already have. We start with agriculture because that is where it matters most.

## Hard rules

- **Never mention the 16123 hotline**, government call centres or "human experts", not even
  as a comparison. We are building for people, not against anyone.
- **No drama.** No night-time despair and no rescue story. The tone is warm, everyday and
  hopeful, like a Bangladeshi ad (bKash, Grameenphone "চলো বহুদূর"). Calm, pleasant music.
- **Bangla that sounds spoken, not written.** Dialogue sounds like real people talking.
  - The seller does not deliver slogans. Realistic: "ভাই, এইটা নিয়া যান, এইবার সবাই
    এইটাই নিতেছে।"
  - Avoid formal or bookish Bangla ("ঐ", "এক্ষেত্রে", "প্রদান করা হবে") and avoid
    over-poetic lines.
  - Offer 2–3 options for each important line and let the team pick.
- **Numbers.** Statistics carry a small on-screen source. The dose and date in the product
  shots come from the real system output. Nothing is typed by hand.
- **Labels.** Mahmud is a fictional example. AI-generated (Higgsfield) footage and simulated
  screens are disclosed in the credits line; the USSD screen is labelled "simulator".
- **Limits.** 2:00 or less, MP4, 300 MB or less. Bangla voice with English subtitles.

## The character

**Mahmud bhai**: a boro farmer on 2 bigha, with a button phone; his son reads SMS for him.
The problem he finds is **dead centre shoots (মাজরা পোকা / stem borer)**. The system has a
rule and a land-scaled dose for this (`backend/kb/triage.py`). Do NOT use "brown spots on
boro leaves": there is no rule for it.

## Tools and who makes what

| Part | Tool | Who |
|---|---|---|
| Village and farmer shots (field, tea stall, shop, home) | Higgsfield (the team's subscription), using street-view or reference images the team provides | Team member, prompts from this session |
| Motion graphics (problem cards, numbers, how it works, end card) | HyperFrames through the brag plugin, directed by Opus 5.5 | This session |
| Real product recordings (phone emulator call, keypad menu, SMS, website) | brag screen capture of the running app (`npm run dev` at repo root, pages `#/phone`, `#/market`) | This session, after the website session finishes the redesign |
| Voice-over | Team member's voice (preferred) or Sarvam Bangla TTS | Team |
| Final edit | FFmpeg at `D:\tools\ffmpeg-9.0.2-full_build\bin` plus the team's editor | Team + this session |

## Suggested story direction (starting point for v2, not final)

Built on the real interview in docs/product/FIELD_INSIGHTS.md (a farmer in Dinajpur).

1. Mahmud bhai at the field: the centre shoots are drying. Light and everyday, not tragic.
2. **Many voices.** The seller: "ভাই, এইটা নিয়া যান, এইবার সবাই এইটাই নিতেছে।" A
   neighbour: "আমি তো পটাশ দিছিলাম।" His memory: "আব্বা সবসময় এইটাই দিত।" He cannot
   even say clearly what is wrong. Everyone is confused; the real farmer said exactly this.
3. **He asks** (by voice on his phone; in this farmer's village almost everyone has a
   smartphone, and a button phone works too). It asks him simple questions step by step, then
   gives one clear answer for his own 2 bigha: what it is, how much, and when. The SMS copy
   goes to the shop.
4. **Before the rain.** "Hold the urea, rain on Thursday": an action, not just news. The farmer
   said a plain storm warning does not help big fields; an instruction does.
5. The contrast line: city people get expert advice on their phones; now so does Mahmud bhai.
6. **Trust.** Nobody pays to be recommended; numbers come from tested code and cited data; it
   says when it does not know.
7. **Close.** Relief: "এবার বুঝলাম।" Then the seal logo, **উর্বরা**, the tagline
   **স্বপ্ন ফলুক** (hand-lettered), over the engraved paddy pattern on kraft, with calm music.

## Still open (ask the user)

Name and tagline are final: **উর্বরা / Urbora · স্বপ্ন ফলুক**. The logo is the seal
(sun, furrows, sprout); final files land in `brand/assets/logo/`, and until then use
`brand/assets/logo/concepts/mark-b.svg`. Still open: voice artist and music.

## Brand colours and type

Use brand/BRAND-CORE.md §5 (palette v2). The old v0.1 values (Shyamol #0F5C3B, Akash blue,
Dhani gold, Tiro Bangla) are retired:
- Deep Shyamol `#0D3B2E` for dark grounds, titles and the end card
- Turmeric Sun `#F2A231` for the sun in the logo and one highlight per scene
- Kraft `#EBD9B4` with Sepia `#6B4A1E` line art for pattern backgrounds
- Straw `#FAF5EA` as the light ground; Young Paddy `#A8D65C` for "healthy again" moments
- Noto Serif Bengali for titles, Noto Sans Bengali for subtitles, Galada for the tagline only

No gradients and no "AI" visuals (robots, circuit brains). Real light and real people,
shown as capable, never pitiable. Grain in any footage or illustration must be rice paddy,
never wheat.
