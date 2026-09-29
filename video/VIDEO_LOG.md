# Video log (Round 1 pitch video)

Kept apart from LOG4.md while other sessions append to it; a one-line summary goes to LOG4
once the team approves the direction.

# 2026-09-30

## [--:--] Storyboards v2: three drawn versions and a copy sheet
**Did:** `video/storyboards-v2.html` (published privately: https://claude.ai/artifact/S1iRgiijfjBJHpTsA526y5).
Three 1:58 storyboards for উর্বরা / Urbora, 33 sketched panels drawn in SVG (paper plus a
light "rough" filter, brand palette v2, and the seal from `brand/assets/logo/concepts/mark-b.svg`):
A "মাটির উপহার" (story film, Higgsfield-heavy), B "কী হয়েছে?" (quick ad, most proof),
C "হাতের মুঠোয়" (engraved line-art film; the road rolls up into a phone as the mobile-banking
image). A copy sheet of 22 line slots, each with 2–3 Bangla options plus "write my own"; picks
redraw the sketches and copy out as text for chat.
**Decision:** Every spoken or on-screen Bangla line is a DRAFT until the user picks it. The
only fixed line is the tagline উর্বরা · স্বপ্ন ফলুক (BRAND-CORE §2). The dose, SMS and call
text in the sketches are placeholders ([real …]) and come from a real system run later.
**Why:** The user must approve every word, because literal Bangla loses tone. No number is typed by hand (CLAUDE.md rule 2).
**Rejected:** Writing final lines myself; screen-recording the app now (the rename and redesign aren't done yet).
**Impacts:** The app session still needs to drop the 16123 footer from the live SMS
(`HOTLINE_LINE`, triage.py) before recording. Recommendation: C's spine with A2, A9 and B6
dropped in. Waiting on the user's version pick and line picks.

## [02:10] Production started: 16 keyframes, real SMS captured, network blockers
**Did:** Higgsfield project "Urbora Round 1 video". 16 keyframe stills (gpt_image_2_5, ~4 credits) for every live-action shot in `video/storyboard/shots.js`, prompts written from the team's Mahmud and Tumpa character sheets (faces never shown). Real diagnosis SMS for Mahmud's case from `backend/kb/triage.py` (boro, 25 days, কাণ্ড/খোল, ডগা শুকানো, 2 bigha): মাজরা পোকা · ভিরতাকো 40WG · হেক্টরে 75 গ্রাম · 2 বিঘায় মোট 20 গ্রাম. The video shows lines 1–5 and leaves out the 16123 footer.
**Decision:** Animate with Kling 3.0 pro, 5 s, sound off (8.75 credits per clip) from approved keyframes; about 140 credits for 16 clips, leaving room for retakes out of 747.5.
**Why:** Stills cost 0.25 each, so fixing a bad frame before animating saves the 8.75 a bad clip would waste.
**Rejected:** Seedance 2.5 1080p (60 credits per clip); uploading the character sheets (the cloud container cannot reach upload.higgsfield.ai).
**Impacts:** The cloud container cannot reach d8j0ntlcm91z4.cloudfront.net / d2ol7oe51mr4n9.cloudfront.net (Higgsfield results), upload.higgsfield.ai, api.open-meteo.com, api.openai.com or api.sarvam.ai. Without them it cannot download clips to edit or fetch a real rain forecast. Potato and mustard are covered crops (S15 is fine).
