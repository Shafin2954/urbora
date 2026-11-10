# Task list — GP FutureMakers round

Done items and the reasoning live in `LOG4.md`. This list is what is still open.

## Needs the team (cannot be done from code)

- [ ] **First real call through Phone Link:** pair the phone (Link to Windows ↔ Phone
  Link, Calls on), set Phone Link's output/input to Voicemeeter (README → "Real voice
  calls"), plug the phone in with USB debugging for call state, then run
  `python -m backend.channels.voice.phonelink --test-playback`, `--test-capture`,
  `--auto-answer`.
- [ ] **First real SMS through the Android phone:** SMSGate app Local Server on; copy user /
  password / signing key into `.env.local`, `SMS_PROVIDER=smsgate`; plug in USB and run
  `python -m backend.channels.bridge.phone_up --watch` (README → "Real SMS"). Then text
  "মেনু" from another phone.
- [ ] **Keypad tones on a real call:** `phonelink --test-dtmf`, press keys on the calling
  phone. If none are heard, the hotline stays speech-only (log it).
- [ ] **bdapps account** for real USSD (README → "Real USSD through bdapps").
- [ ] Laptop internet for calls must not come from the phone taking the calls (LOG4 [16:40]).
- [ ] Try the Bangla USSD/SMS menu on a real button phone (Bangla rendering unverified).
- [ ] Agronomist review of the crop-problem table (`backend/kb/triage.py`; stage day-ranges are
  derived, confidence low) and a check of each named pesticide's current DAE registration.
- [ ] Voice quality with real farmers' voices (Sarvam verified only on synthetic speech,
  incl. 8 kHz); pick the TTS voice by ear (Sarvam default today; Azure `bn-BD` needs a key).
- [ ] Answer the concept-note comment: buyer pays the produce fee (assumed) vs split.

## Build next

- [ ] Quectel USB-modem transport (only if a laptop-free setup is wanted; Phone Link
  covers the pilot).
- [ ] Dealer/buyer auth: phone OTP instead of registration tokens.
- [ ] Encrypt the `contacts` table at rest before real farmers' numbers are stored.
- [ ] Voice barge-in (the Phone Link line is half-duplex today).
- [ ] Pest-surveillance view: `store.triage_summary()` by district/week on the monitor page
  (the pitch's "every report is an early-warning signal for DAE").
- [ ] KB gaps for the problem menu: yellowing/deficiency for aman, potato, mustard, lentil;
  pre-harvest intervals; economic thresholds (CHANNELS_RESEARCH.md §4).
