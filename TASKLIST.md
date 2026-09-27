# Task list — GP FutureMakers round

Done items and the reasoning live in `LOG4.md`. This list is what is still open.

## Needs the team (cannot be done from code)

- [ ] **First real call through Phone Link:** pair the phone (Link to Windows ↔ Phone
  Link, Calls on), set Phone Link's output/input to Voicemeeter (README → "Real voice
  calls"), plug the phone in with USB debugging for call state, then run
  `python -m backend.channels.voice.phonelink --test-playback`, `--test-capture`,
  `--auto-answer`.
- [ ] **First real SMS through the Android phone:** SMSGate from its official GitHub
  releases (package `me.capcom.smsgateway`), Local Server on, then set `SMS_PROVIDER`,
  `SMSGATE_*` and the `sms:received` webhook (README → "Real SMS").
- [ ] Voice quality with real farmers' voices (Sarvam verified only on synthetic speech,
  incl. 8 kHz); pick the TTS voice by ear (Sarvam default today; Azure `bn-BD` needs a key).
- [ ] Answer the concept-note comment: buyer pays the produce fee (assumed) vs split.
- [ ] Name check: "Agrosfera" is also a Ukrainian agrochemical company with a Play Store
  app (`ua.agrosfera.app`) — decide whether that matters for the pitch.

## Build next

- [ ] Quectel USB-modem transport (only if a laptop-free setup is wanted; Phone Link
  covers the pilot).
- [ ] Dealer/buyer auth: phone OTP instead of registration tokens.
- [ ] Encrypt the `contacts` table at rest before real farmers' numbers are stored.
- [ ] Voice barge-in (the Phone Link line is half-duplex today).
