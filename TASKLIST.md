# Task list — GP FutureMakers round

Done items and the reasoning live in `LOG4.md`. This list is what is still open.

## Needs the team (cannot be done from code)

- [ ] **Pick the final name.** "AgriBase" and "Krishak Sathi / KrishiSathi" are already
  taken on the Play Store (LOG4 [23:35]). Set `BRAND_NAME` / `VITE_BRAND_NAME`, then
  sweep internal provenance titles ("AgriSense crop scorer").
- [ ] **Keys on this machine:** `backend/.env` (`OPENAI_API_KEY`) and root `.env`
  (Supabase, `CHANNEL_ID_SALT`). No live agent turn has run on this machine yet.
- [ ] **`SARVAM_API_KEY`** (and/or Azure Speech) — then re-run the district-name STT
  test and a TTS listening test before claiming voice quality.
- [ ] **Android phone** with SMSGate + USB debugging — first real SMS round trip and
  missed-call bridge run.
- [ ] **Quectel EC20/EC25 USB modem + SIM** for real voice calls (driver waits for it).
- [ ] Answer the concept-note comment: buyer pays the produce fee (assumed) vs split.
- [ ] Push `futuremakers` and the `tier0-stable` tag to origin.

## Build, once the above lands

- [ ] Modem voice transport (`backend/channels/voice/modem.py`): AT call control +
  USB-audio, VAD, spoken filler cues from `tool_call` events (Pipecat here).
- [ ] Live verification: one full SMS plan, one USSD plan, one voice call, with the
  real agent; update README statuses from "simulator" to "verified".
- [ ] Dealer/buyer auth: phone OTP instead of registration tokens.
- [ ] Encrypt the `contacts` table at rest before real farmers' numbers are stored.
