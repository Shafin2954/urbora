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
