# LOG4 — GP FutureMakers 2026 round

Single operator on branch `futuremakers`. Append-only. Plan of record:
the approved plan summarized in the first entries below (phases 0–8).

# 2026-09-26

## [23:15] Round opened: scope, branch, rules
**Did:** Branched `futuremakers` off `master`. Rewrote `CLAUDE.md` to v3: single operator, `LOG4.md` is the live log, hackathon-only rules (in-event artifacts, H-hour gates, A/B ownership) replaced; new rules 15 (channels: phone numbers hashed + redacted, USSD never waits on the LLM, template-built numbers) and 16 (marketplace `is_demo` honesty).
**Decision:** Entering GP FutureMakers under **Digital Inclusion & Education**. The submission round is idea/pitch only, so the pitch pack comes first; the build aims for complete working flows, not mockups. Order: finish leftovers → pitch pack → channel core → SMS + Android gateway → USSD → voice → input marketplace → produce marketplace → docs.
**Why:** The new accessibility focus (button phones via USSD / voice / SMS) is what makes this an inclusion project, and the marketplaces are the revenue story the pitch needs.
**Rejected:** Keeping the A/B split (one operator since H10.5; the split only adds relay overhead now).
**Impacts:** PRD §8 lists USSD/SMS inbound and marketplace as non-goals — PRD v4 will reverse that (Phase 8).

## [23:20] Tool selection — adopt existing tools where they integrate cleanly
**Did:** Researched alternatives before building (Sep 2026 sources). No code yet.
**Decision:**
- **Bangla STT → Sarvam `saarika`** (Soniox fallback). A Sep-2026 Bangla benchmark over 1,001 clips (riverbornai/bangla-speech-to-text-benchmark) put Sarvam at 6.9% CER, Soniox 8.1%, and our current `gpt-4o-transcribe` at **28.7%**. Our July test used one synthesized sentence; that was too small a sample. Re-verify on our district-name sentence before switching, since Sarvam is trained on Indian Bengali.
- **Bangla TTS → bake-off**: Azure `bn-BD` (Dhaka accent) vs Sarvam Bulbul vs ElevenLabs, by ear, on farm sentences with numbers.
- **Voice pipeline → Pipecat** (open source, provider-swappable STT/TTS, VAD/turn-taking, local-audio + WebRTC transports). Our `run_turn` becomes a custom processor, so the 16 tools and the no-LLM-math rule stay intact.
- **Real calls → Quectel EC20/EC25 USB 4G modem** (~$15–30) with USB Audio Class voice; AT commands over serial.
- **SMS → SMSGate** (capcom6 android-sms-gateway, Apache-2.0, local-server REST + webhooks) on an Android phone, which also serves as the missed-call trigger via ADB.
- **USSD emulator, marketplace engine → our own code.**
**Why:** An Android phone **cannot** hand call audio to an app: Android hides the in-call audio path and `CAPTURE_AUDIO_OUTPUT` is privileged (not grantable over ADB). AgentCall does it only on one rooted phone model (AGPL); CallPilot (Apache-2.0) proves the Quectel + Windows route but has no hook for a custom agent, so it is a reference, not a dependency.
**Rejected:** LiveKit Agents (its advantage is SIP, which needs a trunk we don't have); textbee/httpSMS (cloud relay + quotas); existing USSD simulators (Africa's Talking/MTN formats, no Bangla, Laravel/Node); Mercur/Medusa for the marketplace (a second Node + Postgres + Redis stack for flows that are SMS/USSD-first and need our Decimal finance engine); rooting a phone.
**Impacts:** New keys will be needed: `SARVAM_API_KEY` (+ Azure Speech if it wins TTS). Hardware to buy for real calls: a Quectel EC20/EC25 USB modem + SIM.

## [23:30] Leftovers from July closed
**Did:**
- `python-multipart==0.0.32` pinned in `backend/api/requirements-api.txt`. **Bug:** `api/transcribe.py` and `api/diagnose.py` use `UploadFile`, but the package was never pinned, so a fresh install could not import the API at all (`test_chat_seam.py` failed at collection). After the fix: **458 passed**.
- Created the `tier0-stable` tag on `7d9ec44`. LOG3 [15:35] recorded it as tagged, but it existed neither locally nor on origin. Local only until the next push.
- `frontend/node_modules` was stale against `package.json` (missing `@supabase/supabase-js`, so the build failed). `npm ci` fixed it; `npm run build` + `npm run lint` clean.
- Deleted the 0-byte decoy `data/agristats.db` (LOG2 [08:35] flagged it; nothing reads it) and the unreachable `NodeInspector.jsx` / `TracePanel.jsx`; fixed the comments and README lines that referenced them.
- README: the Payments section said checkout "does not ship" while the Tier 2 table said it does. The table was right (LOG2 [07:12]); the section now matches.
**Decision:** none beyond the above.
**Why:** Loose ends a judge or a fresh clone would hit first.
**Rejected:** none.
**Impacts:** A fresh `pip install -r backend/requirements.txt` now works.

## [23:35] Brand name moved behind one constant (name not final)
**Did:** New `backend/branding.py` (`BRAND_NAME`, env-overridable) and `frontend/src/branding.js` (`VITE_BRAND_NAME`). The agent's system prompt, the SMS receipt, the API title, the header, the login screen, the document title and the PWA manifest all read it.
**Decision:** Default stays "AgriSense" until the team picks the new name; after that the rename is one env var or one line.
**Why:** The team is renaming for FutureMakers. Checked the candidates: **"AgriBase" is taken** (Play Store app `app.agribase.mobile`, AgriBase Commodities in South Africa, agribase.co.za), and "Krishak Sathi" / "KrishiSathi" are both on the Play Store already.
**Rejected:** Inventing a name ourselves (it's the team's call); renaming Python packages/repo (no user sees them; the repo/remote rename is left to the humans).
**Impacts:** Internal provenance titles ("AgriSense crop scorer") still say AgriSense; they change with the final name in one sweep.

## [23:55] First visual pass of the UI (never done in July) — one farmer-facing bug fixed
**Did:** Drove the dev UI in headless Edge (Playwright from a scratch venv, not an app dependency) at 390×844 and 1440×900: login, guest mode, new chat, send, tabs. Fixed: a failed agent turn printed the raw developer exception to the farmer in English ("agent turn failed: OpenAIError: Missing credentials…"). `ChatPanel.jsx` now shows a Bangla apology (`chat.failed` in `i18n.js`, English variant too) with the raw text folded under "কারিগরি তথ্য" for debugging; styles in `App.css` (44px summary target).
**Decision:** Keep the raw error reachable rather than hiding it — it's how we debug a live demo.
**Why:** The farmer is the reader of that line; an English stack message reads as "the app is broken" and gives them nothing to do.
**Rejected:** Mapping each backend exception to its own Bangla message (the farmer's action is the same for all of them: try again later).
**Impacts:** Seen and fine: guest mode, the chat layout at both widths, the docked graph on laptop, the tab switch on phone. **Not yet seen with live data** (graph filled, plan/finance tabs, checkout): this machine has no `.env`/`backend/.env`, so there is no OpenAI key or Supabase config here. Needs the keys from whoever holds them.

# 2026-09-27

## [00:40] Pitch pack published (Phase 1)
**Did:** Concept note for the FutureMakers judges as a shared doc: https://claude.ai/code/artifact/05d405ed-5f54-4166-a3fe-2162909d0a87 — problem (sourced), solution (one agent, four doors), why AI / where AI is kept out, vs ChatGPT and 16123, built vs this round, architecture diagram, business model, roadmap, metrics and risks, sources.
**Decision:** Every figure in it was opened at its source page: 16.8M farming households (Agriculture Census 2019), 26% rural smartphone ownership (GSMA SOMIC 2024), GP 86.3M subscribers with data penetration just above 60% (Q2 2026 call), 92,094 calls to 16123 in FY2025-26 (BSS), producers' share 27–45% (ADB, 2020). No invented market sizes or revenue projections; commission/fee rates are listed as "to set in the pilot".
**Why:** The submission round is idea/pitch only; judges will check numbers.
**Rejected:** Revenue projections with assumed rates (would be invented data under rule 2).
**Impacts:** Open question left as a doc comment: buyer pays the produce fee (assumed) vs split.

## [01:30] Channel core + SMS channel (Phases 2–3)
**Did:**
- `backend/channels/identity.py` — phone -> `ph-<HMAC-SHA256>` farm id (salted with `CHANNEL_ID_SALT`); SMS/USSD session per phone per day, voice per call.
- `backend/channels/adapter.py` — drains `run_turn` into a `ChannelReply` (text, numbered `Menu` from `ask_farmer` chips, plan/finance, redacted events); a digit reply ("2") maps back to the option's Bangla label, same as the web widget; failures become a Bangla apology.
- `backend/agent/loop.py` — `run_turn(..., channel=)` + `CHANNEL_NOTES` (sms/ussd/voice style: ≤3 lines or ≤4 spoken sentences, no markdown, no title marker, numbers only from tools, say টাকা not ৳ on voice).
- `backend/channels/sms_text.py` — exact GSM-7/UCS-2 segment counting (Bangla = 70/67 chars), `fit()` to a part budget, and `plan_summary_sms()` built only from plan/finance payloads (ceiling label for fertiliser-only crops via the catalog's `cost_basis`).
- `backend/channels/sms.py` — providers: `smsgate` (Android phone, `POST /message`, Basic auth), `bdapps` (existing client, encoding 16), `simulator` (default). `send_sms(farm_id, …)` trims, sends, logs.
- `backend/channels/flows.py` — inbound SMS -> agent -> reply SMS + summary SMS; missed call -> welcome SMS; marketplace keyword hook (`backend/market/sms_commands.py`, empty until Phase 6/7).
- `backend/channels/alerts_job.py` — proactive rain alerts by SMS from `check_plan_conflicts`, each alert texted once (`alert_sms` table), template text with the forecast mm from provenance. Loop opt-in via `ALERT_SMS_ENABLED`; manual `POST /api/channels/alerts/scan`.
- `backend/channels/bridge/adb.py` — laptop process polling the phone's call log over ADB for new missed calls -> `POST /api/channels/bridge/missed-call` (needs `BRIDGE_TOKEN`).
- `backend/api/channels.py` — SMSGate webhook (HMAC verified when `SMSGATE_SIGNING_KEY` set; answers 200 immediately, agent runs in background), bdapps MO, emulator SMS/missed-call/inbox (only in simulator mode — reading an inbox by number must never work on real traffic), status, and the monitor's session list/trace (masked numbers only).
- `backend/memory/store.py` — tables `contacts` (the only place a number is stored), `channel_turns`, `sms_log`, `ussd_sessions`, `alert_sms`.
- `backend/api/main.py` — lifespan handler for the alert loop (replaces deprecated `on_event`).
- Tests: `test_channels_core.py` (26), `test_channels_sms.py` (16). Suite: **500 passed**. `test_loop_integration` signature pin updated for `channel`.
**Decision:** No `ChatRequest` schema change: the web route stays `channel="web"`; channels call `run_turn` directly.
**Why:** Rule 15 in practice — hashed ids everywhere, the raw number in one table, redacted traces, template numbers.
**Rejected:** Keeping raw numbers out of the DB entirely (impossible — an SMS reply needs the number); encrypting the contacts table now (new dependency; noted for production).
**Impacts:** New env vars in `.env.example` (SMS_PROVIDER, SMSGATE_*, CHANNEL_ID_SALT, BRIDGE_TOKEN, ALERT_SMS_*). Not yet verified against a real phone: SMSGate send/webhook and the ADB call-log query are written to the documented shapes and unit-tested with fakes; first live run needs the Android phone.
