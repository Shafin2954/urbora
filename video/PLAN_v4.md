# উর্বরা Urbora · Round 1 video · plan v4 (prompt and loop engineering before the build)

v3 (1:59.5) was reviewed by Jawat on 2026-09-30. This plan answers every note, then fixes the order of the
build. It replaces PLAN_v2.md §8–§9 where they disagree.

## 1. Notes → fixes

| # | Note | Diagnosis (measured) | Fix |
|---|---|---|---|
| 1 | Voice unclear, not energetic | Narrator lines were 2.4–3.0 words/s, pitch spread 2.6–3.1 st on half the lines; no presence EQ; music ducked only 72% | New narrator voice loop (targets §5); every line gets a voice chain (80 Hz high-pass, +3 dB presence at 3 kHz, 3:1 compression, per-line loudness match) |
| 2 | "স্বপ্ন ফলুক" not audible | L21 speaks four sentences in one breath and the music's last chord lands on it | Split L21. "উর্বরা।" and "স্বপ্ন ফলুক।" are their own takes, slower, with a 0.5 s gap; the music is dipped to near silence under them and the final chord comes *after* the tagline |
| 3 | Line after "bank" unclear, "তেমনি" cut | Speech-to-text of the v3 mix at 37.6 s hears "কৃষি পরামর্শ এখন টেলিফোনেই": the roll-up whoosh and music sit on "তেমনি, হাতের" | No sound effect may overlap a voice line (enforced in the mixer); the roll-up whoosh moves into the gap before L12 |
| 4 | Line-art animation is more engaging than the generated footage | Viewer preference, and the line art is also our most distinctive texture | Five new line-art scenes (§3); live shots capped at about 2.5 s unless they carry the product |
| 5 | Long shots | v3: dry shoot held 7.5 s (N1 + freeze), Tumpa 7 s, rain 6 s, storm 3 s, phone demo 21 s, S14 12 s | Every shot re-timed (§2): dry shoot 3.2 s, Tumpa 3.6 s, rain 4 s, storm cut, phone demo 17.5 s, S14 9.5 s |
| 6 | Rain noise felt off and ran past the clip | A 9 s synthetic rain (filtered white noise) started at 72.5 s and ran to 81.5 s, past the storm shot | Synthetic rain removed. One soft distant thunder only, inside the rain shot, faded out 0.3 s before the cut. Rule for all effects: each lives inside its shot and ends with its shot |
| 7 | Storyboard sequence not followed | v3 inserted L02 (বাপ-দাদার) and dropped S03 and the narrator's land line | Back to FINAL_STORYBOARD order S01→S17 after the hook; L02 deleted entirely |
| 8 | After 50→30, connect smoothly to "এ দেশের মাটি উর্বর" | v3 cut hard from the hook to Mahmud's line | The hook's last image (the storm) dissolves over 0.8 s into the dawn ridge; the piano enters on the dissolve; the narrator starts 0.4 s after it settles |
| 9 | Rice grain shot doesn't look like rice | N4 is a hand pouring white grains that read as milled rice or urea | New keyframe from Jawat's paddy reference: a farmer's hand full of golden, husked paddy (ধান) pouring from a jute sack; Kling 3.0 image-to-video, 5 s |
| 10 | Music was playful; wanted emotional, touching, informative, under the voice | v3 used Vadodora and Carpe Diem (light comedic) | Music only from the five supplied tracks (§4), mixed as a cold bed: at least 18 dB below the voice while it speaks, with the voice's 1–4 kHz band carved out of the music |

## 2. Sequence v4 (storyboard order, hook kept)

Beat grid is loose: cuts land on voice phrase ends, not on a metronome. Durations are targets; the builder fits
them to the measured length of each voice take (a shot never ends before its line).

| t (s) | Shot | Texture | Picture | Voice |
|---|---|---|---|---|
| 0.0 | H1 | HF | N1 dry shoot macro, "50 মণ" slam | Mahmud: গতবার পঞ্চাশ মণ ধান পাইছিলাম। |
| 1.25 | H2 | HF (new) | **paddy pouring from a jute sack** | 〃 |
| 2.5 | H3 | HF | N5 sacks against the mud wall, "30 মণ" | Mahmud: এইবার তিরিশ। |
| 3.75 | H4 | HF | N6 storm over the field | (music in) |
| 4.6 | S01 | HF | dissolve to N2 dawn ridge (3.0 s) → c00 dawn walk (3.2 s) | Narrator: এ দেশের মাটি উর্বর। এই মাটিই আমাদের সবচেয়ে বড় উপহার। |
| 11.0 | S02 | HF | c01 hand parts the plants, dry shoot (3.2 s) | Narrator: কিন্তু একই জমিতে এখন আর আগের মতো ধান হয় না। |
| 14.2 | S03 | **line art (new)** | The dry shoot freezes and traces into line art; one "?" draws, then splits into four arrows ending in four sketch icons: bottle, tea glass, phone, sack (3.0 s) | Narrator: প্রশ্ন একটাই। উত্তর অনেক। |
| 17.2 | S04 | HF | c02 shop, c03 tea, c04 phone video, c05 sack; 1.9 s each, each opening on its line-art icon for 4 frames | Seller / neighbour / video / father (4 lines) |
| 24.8 | S05 | **line art (new)** | The four speech bubbles crowd in on kraft paper, overlap and tangle into one scribble (2.6 s) | Mahmud: একেকজন একেক কথা কয়। কার কথা শুনমু? |
| 27.4 | S06 | line art | Far road to the upazila office, sun crosses (5.0 s) | Mahmud: উপজেলা কৃষি অফিস? যাইতেই পুরা দিন। |
| 32.4 | S07 | line art | Bank road rolls up into a phone with ৳ (2.8 s) | Mahmud: টাকা পাঠাইতে তো এখন আর ব্যাংকে যাইতে হয় না। |
| 35.2 | S08 | line art | Field road rolls up into the button phone; seal stamps; name (4.6 s) | Narrator: কৃষি পরামর্শও এখন তেমনি, হাতের ফোনে। … উর্বরা। |
| 39.8 | WEB | real site | The live site in brand fonts (2.6 s) | — |
| 42.4 | S09–S11 | phone plate + real USSD/SMS | The keypad demo, frame by frame (17.5 s; menu steps every 1.25 s) | Narrator: কয়েকটা বাটন চাপেন। উর্বরা নিজেই জিজ্ঞেস করে নেয়। … তারপর উত্তর আসে SMS-এ। কী রোগ, কোন ওষুধ, আর আপনার জমিতে ঠিক কতটুকু। |
| 59.9 | S12 | HF | c09 phone on the counter (2.2 s) → c10 one bottle (2.2 s) | Seller: ও, মাজরা পোকা? তাইলে এইটা নেন। এইটুকুই লাগবে। |
| 64.3 | S13a | **line art (new)** | "১০ দিন পর": a sketched wall calendar tears ten pages off (1.3 s) | — |
| 65.6 | S13b | HF + real SMS | c11 hands untie the sack, phone buzzes, the rain-alert SMS slides up, the sack is tied again (4.0 s) | Mahmud: বৃষ্টির আগেই খবর আইলো। ইউরিয়াটা বাঁচলো। |
| 69.6 | S14 | line art | Ear → calculator → book; then call/keypad/SMS row (9.5 s) | Narrator: বানিয়ে কিছু বলে না। হিসাব আসে পরীক্ষিত কোড থেকে। না জানলে, সোজা বলে দেয়। |
| 79.1 | S15a | **line art (new)** | A smartphone and a button phone draw in side by side; a sun arcs over them and becomes a moon (3.2 s) | Narrator: স্মার্টফোন হোক বা বাটন ফোন। দিন হোক বা রাত। |
| 82.3 | S15b | HF | c12 potato, c13 mustard, c14 pond: 1.1 s each | 〃 (tail) + music lifts |
| 85.6 | S16 | HF | c15 Tumpa on the gold ridge (3.6 s) → N3 drone over gold (2.6 s) | Mahmud: যাক, এইবার বুঝলাম। · Narrator: মাটি আমাদের উপহার। তার যত্নের জ্ঞান, এখন সবার হাতে। |
| 91.8 | S17 | line art | Gold field redraws, the sun rises into the seal (7.5 s) | Narrator: উর্বরা। (gap) স্বপ্ন ফলুক। → final chord |

Total ≈ 99–105 s. Rather than pad, the spare time goes to breathing room around the lines, which is where v3 felt rushed and
unclear. The hard cap stays 2:00.

## 3. New line-art scenes (mg.html, same engraved sepia-on-kraft style as S06–S08)

Rules: every stroke draws on (stroke-dashoffset), nothing pops without a draw; one idea per scene; Bangla
text only when it is the idea itself; motion explains, never decorates (CLAUDE.md frontend rules).

- **S03 "প্রশ্ন একটাই, উত্তর অনেক" (3.0 s).** 0–0.6 s: last frame of c01 cross-fades into a traced sepia
  version (edge-detected still, drawn in). 0.6–1.4 s: a single hand-drawn "?" writes itself centre frame.
  1.4–2.6 s: the "?" tail forks into four arrows that draw outward to four corner icons: bottle, tea glass,
  phone, sack. Pencil-scratch per arrow. 2.6–3.0 s: push toward the bottle to cut into c02.
- **S05 "কার কথা শুনমু?" (2.6 s).** Four speech bubbles with the four quoted answers ("এইটা নিয়া যান",
  "পটাশ দিছিলাম", "এইটা দিলেই হয়", "আব্বা এইটাই দিত") draw in from the four edges, overlap, and their
  outlines tangle into one scribble knot in the centre. Last 0.4 s: the knot unrolls into the road of S06
  (so S05→S06 is one continuous line).
- **S13a "১০ দিন পর" (1.3 s).** A sketched wall calendar; ten pages flick off one by one; the words
  "১০ দিন পর" are hand-lettered underneath.
- **S15a "স্মার্টফোন হোক বা বাটন ফোন। দিন হোক বা রাত।" (3.2 s).** Smartphone (left) and button phone (right) draw
  in on the two phrases; a sun draws on a dotted arc over them, sinks, and the arc continues as a crescent
  moon while the paper tint dims slightly.
- **S17 re-timed (7.5 s).** "উর্বরা" lands with the seal at 1.2 s; "স্বপ্ন ফলুক" writes in Galada exactly
  under the spoken tagline; credits fade in only after the tagline finishes.

## 4. Music map (only the five supplied tracks; all measured 2026-09-30)

| Track | Measured | Role |
|---|---|---|
| nastelbom *emotional piano* (80 s, 89 BPM, B♭ major) | Almost no energy in the 1–4 kHz speech band; flat, soft dynamics | **Land and problem** (0–27 s): tender, nostalgic, stays out of the voice's way |
| andriig *acoustic* (118 s, 123 BPM, B major) | About 1% speech-band energy; gentle 2-bar guitar pulse | **Product and proof** (35–85 s): warm and informative, a half-step lift from the piano's key at the name reveal |
| *tape echo background* (81 s) | Soft lo-fi first 26 s, about 2% speech band | **The turn** (27–35 s, line art road/bank): thoughtful, lighter texture for the style switch |
| the_mountain *upbeat emotional* (112 s, A minor) | 10–30% speech band, a steady build | **Lift and end** (85 s to the end), using its build and final resolve; carved and ducked hard under the voice |
| alex-morgan *motivational rise* (173 s) | Bright, 5–15% speech band, dense | Not used: too busy under Bangla speech. Kept as a fallback for the end swell |

Psychology of the arc: tender (the land) → a drop to near-silence at the confusion knot (S05: silence makes
the question land) → a lighter pulse on the road → a warm, confident bed while the product talks → a
lift on the other fields and the child → the voice alone on the tagline → the chord resolves after it (the
peak-end rule: the last feeling is resolution, heard clearly).

Mix rules: music under voice ≤ −18 dB relative to the voice (short-term loudness); a 1–4 kHz dip of 4 dB in the
music, applied only while a voice speaks; music never above −22 LUFS short-term when a voice is present;
master to −14 LUFS integrated, −1 dBTP.

## 5. Voice loop v4

Targets (measured per take with speech-to-text, pitch tracking, pause detection):

- **Narrator.** Clear and energetic GP style. Median F0 100–125 Hz. Pitch spread ≥ 3.5 st (lively, not flat).
  Speed 2.9–3.4 words/s inside a phrase, with a clear pause at each full stop. Speech-to-text similarity ≥ 0.97.
- **Mahmud.** Lively and conversational. Spread ≥ 3.3 st. Speed 3.0–3.6 words/s. Similarity ≥ 0.95.
- **Tagline takes ("উর্বরা।", "স্বপ্ন ফলুক।").** Similarity 1.0 on the isolated take. Duration 0.7–1.3 s each (unhurried).
- **In-mix check (new).** The final mix is transcribed line by line. Every line must score ≥ 0.9
  similarity *in the mix*. This test catches the masking that hid "তেমনি" in v3. A line that fails gets its
  music and effects pulled back, then the check is re-run.

Loop: audition 6 narrator speakers × pace {1.1, 1.2} × temperature {0.9, 1.1} on three test lines → rank by
the targets → Jawat hears the top two → generate all lines, best of 3.

## 6. Build order

1. Voice loop and the music bed audition (sent to Jawat).
2. Paddy keyframe from Jawat's reference image, then image-to-video (needs the image).
3. New line-art scenes S03, S05, S13a, S15a; S17 re-timed.
4. EDL v4 in final.py, fitted to the measured voice takes; phone demo re-timed to 1.25 s per step.
5. audio.py v4: new beds, effect rules (no effect overlaps a voice; each effect ends with its shot), voice chain.
6. Render → in-mix speech-to-text check → contact sheet review → fix → final render → upload.

## 7. Dynamic subtitles on the emphasis beats (added from Jawat's note, 2026-09-30)

The small English subtitle line stays for every spoken line (for the judges). On the lines that carry the
argument, a **Bangla kinetic caption** also appears. The words arrive in sync with the voice, and the key word lands bigger in
sun-gold with a hand-drawn underline swipe. It is timed from word timestamps of the actual take (Whisper word
timings; if the word count doesn't match the script, timing is spread across the detected speech by character
length).

Style: Noto Sans Bengali 600, straw-white with a 3 px dark outline on footage; shyamol green on kraft line art.
Each word rises 12 px and fades in over 5 frames. The emphasis word scales 1.0→1.22 with a slight overshoot,
turns sun-gold, and a sepia underline draws under it in 6 frames. The caption leaves by fading out over 6
frames, 0.3 s after the line ends. At most 7 words on screen, one line, lower third, never over a face or a
phone screen.

| Line | Kinetic caption (emphasis in **bold**) |
|---|---|
| L01 | ৫০ মণ → **৩০** (the existing number slams stay; the "30" gets the underline) |
| Land | এ দেশের মাটি **উর্বর** · সবচেয়ে বড় **উপহার** |
| S02 | আগের মতো ধান **হয় না** |
| S03 | প্রশ্ন **একটাই** · উত্তর **অনেক** (drawn inside the line art) |
| S05 | কার কথা **শুনমু?** |
| S06 | যাইতেই **পুরা দিন** |
| S08 | কৃষি পরামর্শও **তেমনি** · **হাতের ফোনে** |
| L13 | উর্বরা নিজেই **জিজ্ঞেস** করে নেয় |
| L15 | কী রোগ · কোন ওষুধ · ঠিক **কতটুকু** |
| L17 | বৃষ্টির **আগেই** খবর |
| L18 | বানিয়ে **কিছু বলে না** · না জানলে, **সোজা বলে দেয়** |
| L19 | **স্মার্টফোন** হোক বা **বাটন ফোন** · **দিন** হোক বা **রাত** |
| End | **স্বপ্ন ফলুক** is the Galada lettering of the end card itself, written on in sync with the voice |

## 8. Paddy shot (H2): prompt engineering

Reference: Jawat's photo (assets/paddy_ref.jpg, not committed; third-party photo used only as a look reference).
It shows unhusked paddy: elongated golden-tan hulls, ridged, pointed tips, harvested panicles behind, jute cloth
and a wooden scoop.

Why the v3 shot failed: the model defaulted to "rice", which it renders as white milled grains. The prompt must name
the hull colour and shape, and it must forbid white or polished grain outright.

**Keyframe (gpt_image_2_5, 16:9, reference image attached):**
> Macro photograph, eye level. A Bangladeshi farmer's weathered, sun-darkened hand with a thin copper ring
> holds a heaped handful of freshly harvested unhusked paddy (dhan): elongated golden-tan hulls with fine
> ridges and pointed tips, exactly like the reference photo, a few grains spilling from between the fingers
> onto a large heap of the same paddy on jute cloth. Behind, out of focus, bundles of harvested golden rice
> panicles with a few green leaves. Low warm evening sidelight from the left, dust motes, shallow depth of field,
> 35mm film look, true colours. No white rice, no polished or milled grain, no text, no logos.

**Motion (Kling 3.0 pro, 5 s, sound off):**
> The hand slowly tilts and a steady stream of golden paddy grains pours from the palm onto the heap below,
> individual hulls tumbling and bouncing; the camera pushes in very slowly. Natural physics, no morphing, the
> grains keep their golden hull colour throughout.

Loop: generate 2 keyframes → check that the grains read as paddy (hull shape, colour) and the hand has 5 fingers
→ animate the best → check frames at 0, 2.5 and 5 s for morphing or whitening → re-roll once if needed.
