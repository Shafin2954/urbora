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

## [02:30] Footage and line-art scenes built (no app screens yet)
**Did:** 16 Kling 3.0 pro clips from the approved keyframes (~192 credits; the potato-field keyframe was redone without bangles, with a sari anchal and a small ring instead). Motion prompts written as DP/editor briefs in `video/storyboard/motion_prompts.md`. Line-art scenes S06, S07, S08, S14, S17 built in `video/build/mg.html` (brag-slim method: each frame is `render(scene, t)`, captured by Playwright and encoded with ffmpeg via `render.js`), using the brand seal, palette v2 and the paddy engraving from `brand/scripts/paddy-engraving.mjs`. Rough-cut edit list in `video/build/assemble.py`. Job IDs in `video/build/jobs.json`.
**Decision:** Clip 01 is used for its first 3.5 s only (later frames grow dark spots that read as a different disease); clip 12 is used for its first 2.3 s (the sari folds oddly after). App screens (S10 left half, S11, the SMS on S12/S13) wait until the website session finishes.
**Why:** The team asked for everything except the app/website shots first, and for economy with credits.
**Rejected:** Re-generating clip 01 now (a trim fixes it for free).
**Impacts:** Rebuild: `cd video/build && npm i && python3 -m http.server 8765 & node render.js S06 S07 S08 S14 S17 && python3 assemble.py`. The Higgsfield clips live in the team's Higgsfield project "Urbora Round 1 video" and are not in git.

## [02:45] Rough cut v0 (silent, 1:59)
**Did:** `python3 assemble.py` joins 23 segments into `video/build/out/urbora_roughcut.mp4` (1920x1080, 30 fps, 1:58.9, ~75 MB; not in git), plus a labelled copy and a 720p review copy. The ffmpeg build here has no drawtext, so the S11 slate and shot labels are drawn with Pillow and overlaid.
**Decision:** S02 plays clip 01's clean first 3.5 s at half speed with frame blending; S03 is a freeze of that frame with a slow digital push-in; S10 is the loudspeaker plate slowed to 16 s until the call replica goes on its left.
**Why:** Keeps the credits for retakes the team actually asks for.
**Rejected:** none.
**Impacts:** Credits left: 532.75 of 747.5 (~215 used: 17 keyframes, 16 clips). Still to do: app screens (S10 replica, S11, SMS on S12/S13, after the website is final), voice-over, music, subtitles, colour grade.
