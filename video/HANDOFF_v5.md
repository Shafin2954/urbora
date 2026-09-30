# Video v5 handoff (cloud session → regular session, 2026-09-30)

## Get the files
1. `git clone https://github.com/Shafin2954/TeamFixeth_AgriSense && cd TeamFixeth_AgriSense && git checkout futuremakers`
   (the branch `claude/pensive-turing-ajerhu` is identical).
2. Download everything that is not in git (482 MB):
   https://d2ol7oe51mr4n9.cloudfront.net/user_3J84uH1NssozkNIdmEg62WfHVMV/0bc7b6e5-e7e9-4b51-b723-5dcccdebfe70.zip
3. Unzip and place:
   - `clips/` → `video/build/clips/` (Higgsfield clips N1–N8, c00–c15, P1 paddy)
   - `assets/*.png` → `video/build/assets/` (phone4k, smart = smartphone photo with green screen, home2, kf*)
   - `web/` → `video/build/web/` (real website captures: `check/` crop check, `chat_rain/` AI chat)
   - `build_out/S*.mp4` → `video/build/out/` (rendered line-art scenes, incl. the six new v5 plates)
   - `recordings/My_Voice.m4a`: Jawat's recording of every line in RECORDING_SHEET_v5.md (one person, all roles)
   - `music5/`: the four Pixabay tracks for v5 (PaulYudin emotional piano, AtlasAudio documentary, leberch inspiring piano trailer, Tunetank hopeful cinematic)
   - `vo_v4/`, `music4/`, `urbora_final_v4.mp4`: the previous cut, for reference
4. Put `.env.local` (OpenAI, Sarvam keys) at the repo root. It is never committed.

## Prompt for the new session
```
Continue the Urbora (উর্বরা · "স্বপ্ন ফলুক" · Team Uplift) Round 1 video for GP FutureMakers 2026. Branch futuremakers.
Read first: CLAUDE.md, video/HANDOFF_v5.md, video/PLAN_v5.md (the plan to build), video/RECORDING_SHEET_v5.md (the script),
the last LOG4.md entries ([05:30] v4 cut, [10:05] v5 prep), video/build/timeline.py and final.py/audio.py/mg.html/smart.py.
The asset bundle from HANDOFF_v5.md is unzipped into place.

Build v5 exactly as PLAN_v5.md says, ≤2:00:
1. Voice: recordings/My_Voice.m4a has Jawat speaking every line twice (one person, all roles, natural Bangladeshi
   accent). Split by silence, transcribe (gpt-4o-transcribe, language bn), match takes to the script IDs (N1–N17,
   M1–M6, C1–C4), keep the best take per line. Narrator = Jawat's own voice, cleaned and polished to sound like a
   GP ad voiceover (denoise, 80 Hz high-pass, presence EQ, gentle compression, warmth), or a speech-to-speech
   conversion to a deeper warm voice IF it keeps his pronunciation exactly. Mahmud and the other characters
   (shopkeeper, neighbour, phone video) must sound like different people: use speech-to-speech voice conversion
   (e.g. ElevenLabs STS or Higgsfield voice_change) or at least pitch/formant shifts, keeping his accent and timing.
   Check every converted line still transcribes as well as the source.
2. Music: the four tracks in music5 per PLAN_v5 §4; cut the edit to their section boundaries and downbeats;
   music audible (about −11 dB under the voice, fuller in gaps), never masking words.
3. Picture: the v5 sequence (22 scenes) with the new plates S06c, S07q, S08h, S12q, S14b, S16h; S08 re-timed so
   "কৃষি পরামর্শ, এখন হাতের ফোনে" writes on with the voice and then "উর্বরা" lands; storm shot cut; faster keypad
   demo (0.7 s steps); smartphone demo via smart.py (whip-pan, crop check → 20 গ্রাম card, AI chat rain answer)
   with large readable callouts beside the phone; reach shots cut on the exact words; kinetic captions on the
   emphasis lines; English subtitles.
4. Timeline fitted to the measured voice takes (timeline.py), then audio.py → qa_mix.py → final.py base/frames → mux.
Show me stills and a 720p preview as you go; log each unit of work in LOG4.md; commit and push to futuremakers.
Standing rules: hands and objects only, no faces; no 16123; every on-screen number is real system output;
credits line on the end card (update the music credit to the four Pixabay artists).
```

## Environment notes
- Python: numpy, librosa, soundfile, scipy, pillow (with raqm), imageio-ffmpeg, openai, httpx, python-dotenv.
- Node: Playwright with Chromium (for `render.js`, which renders `mg.html` scenes; serve `video/build` with
  `python3 -m http.server 8765`).
- The website (for new captures) runs from the repo: backend `python -m uvicorn backend.api.main:app --port 8000`,
  frontend `cd frontend && npm run dev -- --port 5000`; crop check at `/#/check`, AI chat at `/#/app` (guest).
