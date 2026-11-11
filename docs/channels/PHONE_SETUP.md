# Phone setup: real SMS, USSD and voice calls

How to put the phone channels on a real phone and SIM, and how to test them without one.
Background and verified telecom facts: `docs/channels/CHANNELS_RESEARCH.md`.

## Test without a phone (simulator)

Start the `backend-sim` server from `.claude/launch.json` (port 8020, `SMS_PROVIDER=simulator`,
emulator routes on), or set those two variables yourself. Then drive it with
`POST /api/channels/emulator/{sms,ussd,missed-call}` and read replies from
`GET /api/channels/emulator/inbox?msisdn=…`. The voice loop can be tested without a phone through
`/api/channels/bridge/voice/say` (make a Bangla clip) and `/bridge/voice/turn` (send it as a caller),
with the `X-Bridge-Token` header. Use obviously fake numbers (e.g. `01799999901`).

## Checklist that worked on 2026-11-10 (Motorola Edge 50, Windows 11)

1. Phone: USB debugging on and the laptop's key allowed ("Always allow"); `adb devices` shows `device`.
2. Phone: Link to Windows; laptop: Phone Link (Microsoft Store), paired, **Calls** set up.
   On the phone, Bluetooth settings for the laptop: **Phone calls** on.
3. Laptop: Voicemeeter **Standard**, then restart. Windows Sound (`mmsys.cpl`): Speakers = default
   playback; Stereo Mix enabled; **Voicemeeter Out B1 = default recording device**.
4. Voicemeeter: A1 = `MME: Speakers`; VAIO strip B only; hardware strips without B.
5. Laptop internet must not come from the phone that takes the calls.
6. `.venv/Scripts/python -m pip install -r backend/requirements-voice-bridge.txt`, backend running, then
   `python -m backend.channels.voice.phonelink --capture "Stereo Mix" --playback "Voicemeeter Input"`.
7. Afterwards, set the laptop's normal microphone back as the Windows default.

## Demo dealers and the live monitor

```bash
python -m backend.market.seed_demo      # demo dealers + buyers (once; --reset removes them)
```

Then open `http://localhost:5000/#/monitor` (live phone conversations) and `#/market`.
With the default `SMS_PROVIDER=simulator` nothing leaves the machine; the emulator API
(`/api/channels/emulator/*`) still takes SMS/USSD/voice turns from scripts and tests.

## Real SMS through an Android phone

Pilot, USB only, no Wi-Fi needed.

1. Install **SMS Gateway for Android** (SMSGate, `me.capcom.smsgateway`) from its
   [GitHub releases](https://github.com/capcom6/android-sms-gateway/releases). In the app:
   turn on *Local Server*, tap *Offline* so it shows *Online*, and note the username and
   password. Samsung: set the app's battery use to *Unrestricted*.
2. In `.env.local`: `SMS_PROVIDER=smsgate`, `SMSGATE_USER`, `SMSGATE_PASSWORD`, and the
   app's Settings → Webhooks → Signing Key as `SMSGATE_SIGNING_KEY`. `SMSGATE_URL`
   defaults to `http://127.0.0.1:8080`. Optional `SMSGATE_SIM=1|2` on a dual-SIM phone.
3. Start the backend, plug the phone in with USB debugging on, then run
   `python -m backend.channels.bridge.phone_up --watch`. It exempts the app from battery
   optimisation, opens `adb forward tcp:8080` (laptop → phone API) and `adb reverse
   tcp:8000` (phone → backend), and registers the `sms:received/sent/delivered/failed`
   webhooks at `http://127.0.0.1:8000/api/channels/sms/smsgate` — the only plain-HTTP
   webhook address SMSGate accepts. `--watch` re-applies the tunnels after a reconnect.
4. Missed calls: set `BRIDGE_TOKEN` on both sides and run
   `python -m backend.channels.bridge.adb --backend http://127.0.0.1:8000`.

The webhook is idempotent: SMSGate retries a failed delivery for ~2 days, so each event
id is handled once, signatures older than 5 minutes are refused, and an SMS older than
15 minutes is recorded but not answered.

## Real USSD through bdapps

Robi/Airtel SIMs; free developer account.

1. Register at [dev.bdapps.com](https://dev.bdapps.com) and create an app with **USSD** (and
   SMS) enabled. Registration is free; bdapps charges subscribers per menu (~Tk 1–2), so ask
   for a free/test tariff for the pilot. The service code (`*213*…#`) is assigned on approval.
2. bdapps must reach the backend at a public **HTTPS** URL, and its outbound `/ussd/send`
   only accepts calls from a whitelisted IP. Replit autoscale changes IP on every deploy, so
   run the backend on the laptop and expose it with a free Cloudflare quick tunnel:
   `cloudflared tunnel --url http://localhost:8000` → portal USSD URL
   `https://<name>.trycloudflare.com/api/channels/ussd/bdapps`, SMS-MO URL
   `…/api/channels/sms/bdapps`. (A quick-tunnel URL changes on restart; a free named tunnel
   keeps it.)
3. Portal **Allowed Host List** = the laptop's public IP (`curl ifconfig.me`; re-check on a
   new network — `docs/channels/BDAPPS-PREFLIGHT-CHECKLIST.md`).
4. `.env.local`: `BDAPPS_APP_ID`, `BDAPPS_PASSWORD`, `BDAPPS_MODE=live`. Test in the bdapps
   web simulator first, then from a Robi SIM. Every screen already fits one Bangla USSD page.

## SMS menu mode

No short code needed: text **মেনু** (or `menu`) to the gateway phone and
the same USSD menu arrives by SMS; reply with digits. Free text leaves the menu and goes to
the agent. An unfinished USSD walk from the last 30 minutes is offered back.

## Real voice calls through Windows Phone Link

Pilot, no root, no modem.

1. `python -m pip install -r backend/requirements-voice-bridge.txt`; install
   [Voicemeeter](https://vb-audio.com/Voicemeeter/) (free) and adb (Android platform-tools;
   the bridge also finds the Android SDK copy on its own).
2. Phone: install **Link to Windows**; PC: **Phone Link** → Calls → pair over Bluetooth.
   Make a test call from the PC to confirm call audio plays on the laptop.
3. Audio route (verified on a real call with **Voicemeeter Standard**, LOG.md [16:40]):
   caller → Phone Link → **Speakers** → **Stereo Mix** (enable it under Sound → Recording)
   → bridge; bridge → **Voicemeeter Input** (VAIO strip → **B1** only) → **Voicemeeter
   Out B1**, set as the Windows default microphone → Phone Link. Set Voicemeeter's A1 to
   the speakers so its engine runs, **choosing the `MME:` entry**: a `WDM:` A1 takes the speakers
   exclusively and silences every other app, Phone Link included. Run the bridge with
   `--capture "Stereo Mix" --playback "Voicemeeter Input"`. (With Voicemeeter Potato the
   AUX → B2 route in the bridge's defaults works instead.)
   **The laptop must not take its internet from the phone that answers calls** — Android
   drops mobile data during a non-VoLTE call, and STT/agent/TTS need the network.
4. `BRIDGE_TOKEN` in `.env.local` (same value the backend reads), backend running, then:
   `python -m backend.channels.voice.phonelink --test-playback` (you hear the Bangla
   greeting when a call is up), `--test-capture` (speak on a call; the meter moves), and
   finally `python -m backend.channels.voice.phonelink --capture "Stereo Mix" --playback "Voicemeeter Input" --auto-answer`.
   **Motorola Edge 50 (and maybe other phones):** answering over ADB keeps the call audio on the
   handset; Phone Link carries audio only for calls it answered itself. Drop `--auto-answer` and
   click Answer in the Phone Link pop-up; the bridge notices the call and takes over. (The Samsung
   A55 auto-answered fine.) Unattended answering is open work (LOG.md 2026-11-10 [15:45]).
5. **Keypad:** during a call the caller may press keys instead of speaking — the USSD menu is
   read aloud ("ফসল পরামর্শ, 1 চাপুন"), numbers end with # or a pause, * repeats. A
   crop-problem answer is spoken on the call and sent by SMS. Check first that key tones
   survive your phone network: `--test-dtmf`, then press keys on the calling phone.
6. The caller's number comes from ADB when Android reveals it; if yours hides it, pass
   `--caller <number>` for testing. One call at a time.

A personal SIM is for a pilot only; production runs on the operator's IVR, USSD short
code and bulk-SMS channels. `ALERT_SMS_ENABLED=true` turns on the proactive rain-alert
texts.

## Payments

Ships in **simulator mode** — see the Tier 2 table above. The `কেনাকাটা` tab appears when
the finance projection has purchasable input lines, and runs quote → confirmation → charge
→ Bangla SMS receipt through `POST /api/checkout/quote` and `POST /api/checkout`. The
confirmation gate is enforced server-side (409 without a matching, unexpired quote).
No real money moves; the mode badge reads `GET /api/checkout/mode`.
