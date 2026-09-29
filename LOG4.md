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

## [03:10] USSD menus, browser phone emulator, voice line (Phases 4–5)
**Did:**
- `backend/channels/ussd.py` — pure `step(state, input, ctx)` state machine: main menu (নতুন পরামর্শ / আমার প্ল্যান / আবহাওয়া সতর্কতা / উপকরণ কিনুন / ফসল বিক্রি / প্রশ্ন করুন / শেষ উত্তর); intake by division → district (7 per page, "8. আরও") → বিঘা → soil → water → season → budget → confirm; a returning farmer is offered their saved profile; Bangla keypad digits accepted; "0" = back. Screens ≤182 chars (tested). Confirm/question return an **action** the runtime runs in the background → SMS. Profile from USSD is saved to `farms` (shared with every channel). Marketplace sub-menus plug in via `backend/market/ussd_menus.py::SUBMENUS`.
- Routes: `POST /api/channels/emulator/ussd` (JSON), `POST /api/channels/ussd/bdapps` (`mo-init`/`mo-cont` in; `/ussd/send` out, encoding 16; in simulator mode the exact MT body is returned with the password masked, not sent).
- `backend/channels/voice/speech.py` — STT: Sarvam (`saaras:v3` default; v4 sends crop/district `keyterms`) when `SARVAM_API_KEY` is set, else OpenAI `gpt-4o-transcribe`; TTS: Sarvam Bulbul / Azure `bn-BD` / OpenAI. Plain httpx, no SDKs.
- `backend/channels/voice/turn.py` — clip → STT → `run_turn(channel="voice", session per call)` → spoken reply (menus read as "দোআঁশ হলে 1 বলুন") → TTS; hang-up texts the template summary of the call's plan/finance. Routes `POST /api/channels/emulator/voice/turn|hangup`, `GET /api/channels/voice/status`.
- `backend/api/transcribe.py` — web dictation uses Sarvam for Bangla when the key exists; unchanged otherwise.
- Frontend: `#/phone` (`pages/PhonePage.jsx`, `VoiceCall.jsx`, `phone.css`) — a button phone: keypad, USSD dial, SMS inbox + compose, missed call, push-to-talk call; labelled সিমুলেটর. `#/monitor` + `components/ChannelMonitor.jsx` — phone conversations with masked numbers, replayed into `GraphPanel`. Hash routing in `Root.jsx`. Pinned `@supabase/supabase-js` exactly (was `^`).
- Tests: `test_channels_ussd.py` (18, incl. the USSD-built agent message round-tripping through `extract_known_fields` to all six canonical fields), `test_channels_voice.py` (10). **Suite: 528 passed.**
**Seen working in a browser (headless Edge):** dial `*3700#` → full Rajshahi intake → confirm → agent runs in background → answer arrives in the SMS inbox (a Bangla apology here, because this machine has no OpenAI key) → monitor shows the USSD session. Missed call → 2-segment welcome SMS. A second dial offered the saved profile (cross-channel memory).
**Decision:** The browser call is half-duplex push-to-talk with plain HTTP turns — **Pipecat is not used for it.** Pipecat's value (VAD, barge-in, streaming) matters for the full-duplex modem line; the modem driver (`backend/channels/voice/modem.py`, Quectel AT + UAC audio) is deferred until the hardware is in hand, per the plan.
**Why:** Fewer moving parts in the demo path; the same `voice_turn` serves both transports.
**Rejected:** Pipecat SmallWebRTC for the browser (aiortc dependency, a server-side WebRTC stack, for a push-to-talk demo); writing the modem driver blind.
**Impacts:** Voice quality is unverified: needs `SARVAM_API_KEY` (and/or Azure) and an ear test on district names + numbers before claiming it in the README. The rejected July `whisper-1` lesson applies: verify before shipping.

## [05:20] Input + produce marketplaces (Phases 6–7)
**Did:**
- `backend/finance/market.py` — the only marketplace arithmetic, Decimal: `order_totals` (farmer pays Σ packs×price; **dealer** pays the commission, so the farmer's total never moves with the rate), `packs_needed`/`cost_for_quantity` (whole packs, rounded up), `unit_price`, `deal_totals` (farmer receives qty×price in full; **buyer** pays the platform fee on top). Rates `MARKET_COMMISSION_PCT` (5) / `PRODUCE_FEE_PCT` (2) are pilot parameters, bounded 0–50. Tests: `tests/test_market_finance.py` (14).
- `backend/market/` — `db.py` (tables in the same SQLite file: dealers, products, orders, buyers, produce_listings, offers; every row `is_demo`), `catalog.py` (generic inputs incl. the 7 crop-protection chemicals the KB corpus names), `ranking.py` (price 40 / distance 30 / stock 15 / trust 15, components returned, no paid term, >80 km dropped, deterministic tie-break), `inputs.py` (`find_inputs` agent tool with `source_type: listing` provenance naming dealer + date and `[DEMO]`; orders with a strict state machine; cancel restores stock; SMS to dealer and farmer), `produce.py` (listings with a **price guide** from the cited farm-gate row + BBS wholesale pattern; offers; accept → other offers rejected, listing sold, contacts exchanged by SMS; buyers never see the farmer before acceptance), `sms_commands.py` (farmer `বিক্রি আলু 500 কেজি 22 টাকা [জেলা]`, `গ্রহণ/বাতিল <id>`; dealer `হ্যাঁ/না/প্রস্তুত/দেওয়া <id>`; Bangla digits), `ussd_menus.py` (menu 4 buy: product → ranked dealers → packs → confirm; menu 5 sell: crop → kg → price with the guide → confirm), `seed_demo.py` (5 demo dealers around Rajshahi, 3 demo buyers).
- `backend/schemas.py` — `SourceType` += `"listing"` (additive contract change; documented in the Provenance docstring).
- `backend/agent/tools_spec.py` + `prompts.py` — `find_inputs` registered (17 tools); narration rules: quote offers exactly, say ডেমো দোকান, never rank or total, ordering happens in app/USSD/SMS; pest treatment: a dealer listing is the only spray price the agent may quote.
- `backend/api/market.py` — farmer routes (by phone number so SMS reach them, or farm id), dealer routes (`X-Dealer-Token`), buyer routes (`X-Buyer-Token`), districts + catalog.
- Frontend: `#/market` (`MarketPage.jsx`: buy with a confirmation step "৳X দোকানে নগদে — নিশ্চিত?", sell with the price guide, my orders/listings with accept/reject), `#/dealer` and `#/buyer` (`PartnerPages.jsx`: self-registration → token; dealer edits prices/stock and moves orders; buyer sees nearby listings and offers), `market.css`; header links বাজার / বাটন ফোন.
- Tests: `backend/tests/test_market.py` (19). **Suite: 562 passed.**
**Bugs found and fixed:**
- `lookup_district("")` returned the first district (an empty string is "contained" in every name) — a farmer with no saved district would have had their harvest listed in an arbitrary district. Fixed at the source in `backend/tools/districts.py` (also guards the geocoder fallback and plan checks); test added.
- Accepting an offer by SMS would have fallen through to the agent as chat; now returns a confirmation.
**Decision:** Demo accounts have made-up numbers, so with a LIVE SMS provider their messages are logged `skipped_demo`, never sent — a made-up number may belong to a stranger. Demo fertiliser listings use the cited government-notified price (৳27/kg Urea/TSP, ৳20/kg MoP; data/prices.md); demo spray prices are invented and marked `demo value — not a real quote` + `[DEMO]`.
**Seen working in a browser:** order urea with the confirmation step → SMS to farmer and dealer; list 500 kg potato with the cited guide (খামার-দাম ৳7/কেজি, 2026-04-03) → demo buyer offers ৳21/kg on the buyer page → farmer sees "আপনি পাবেন ৳10,500" → accept → contact-exchange SMS (demo number flagged "আসল নম্বর নয়") — all visible in the button-phone emulator's inbox. Dealer page confirms the order; product table fits a phone.
**Rejected:** a paid-placement ranking term (breaks the trust story); escrow (out of scope, stated); letting the model compute totals or pick a dealer.
**Impacts:** New env: `MARKET_COMMISSION_PCT`, `PRODUCE_FEE_PCT`. Run `python -m backend.market.seed_demo` once for demo data (`--reset` removes it). Dealer/buyer auth is a registration token — pilot-grade, stated; production moves to phone OTP.

## [06:10] Docs for the round (Phase 8)
**Did:** README — new intro (any phone, marketplaces, both events), a "New in the FutureMakers round" section (door-by-door status, marketplaces, what never changed, tool choices with the benchmark evidence), real-vs-demo rows for dealers/buyers, price guide, commission/fee, emulator transport, voice quality; setup for the emulator, SMSGate, the ADB bridge and alerts; tools table (17); architecture; test count 562. PRD — v4 addendum at the top (scope reversal of the July non-goals; still out of scope: escrow, logistics, disputes, a real short code/IVR). TASKLIST — rewritten as what is still open, split into "needs the team" and "build next". repograph — a FutureMakers section mapping every new file. Concept note — the four "this round" rows now say what is built and where it runs; test count updated.
**Decision:** Statuses say "simulator" / "not yet verified" wherever a real device or key has not been used. Nothing is marked verified that was only unit-tested.
**Why:** The README's real-vs-mock table is what judges read to decide whether to trust everything else.
**Rejected:** none.
**Impacts:** The branch and the `tier0-stable` tag are committed locally but NOT pushed — pushing is left to the team.

# 2026-09-28

## [11:40] Name, local keys, hermetic tests
**Did:** Product renamed to **Agrosfera** (অ্যাগ্রোস্ফেরা): `backend/branding.py`, `frontend/src/branding.js`, `vite.config.js`, provenance titles in `cropdb.py` / `geocode.py` / `crop_scorer.py` now read `BRAND_NAME`; docstrings, `.env.example`, README title, the concept note (title + body). New `backend/env.py` loads `.env.local` > `backend/.env` > `.env` for both configs. New `backend/tests/conftest.py` (+ root) clears provider env vars in every test. Generated `BRIDGE_TOKEN` and `CHANNEL_ID_SALT` appended to the gitignored `.env.local`.
**Decision:** Agrosfera, the team's choice. Checked: "AgrooSphere"/"Agrosphere" are close to an existing Play Store crop-doctor app and a funded US company; "Agrosfera" is also a Ukrainian agrochemical company with an ordering app (`ua.agrosfera.app`). Flagged, not blocking.
**Why:** With real keys present, 9 transcription tests would have sent test audio to Sarvam; tests must not depend on whose laptop runs them.
**Rejected:** Renaming the repo / Python package (no user sees them).
**Impacts:** Local test farms created before the salt was set are orphaned (dev data only).

## [12:30] First live runs on this machine: Sarvam verified, agent verified, one real bug fixed
**Did:**
- Sarvam: TTS → STT of the July district-name sentence came back exact, also after resampling to 8 kHz telephone band (TTS 2.2 s, STT 1.2 s). Synthetic speech only — real voices still to test.
- Live agent through the SMS emulator (OpenAI key): ranking from stated facts; then "আলু, 15 নভেম্বর" → `finance_projection` + `season_plan` → the template summary SMS with real figures (খরচ ৳42,156, আয় ৳48,846, লাভ ৳6,691).
- **Bug (rule 2):** a garbled SMS ("???? …", from a curl encoding slip in my test) still produced `crop_scorer(district=Dinajpur, soil=loam, water=irrigated, season=rabi)` — every field invented — and a confident ranking. New `backend/agent/intake_guard.py`, called in `loop.py` before any planning tool: district/soil/water/season must appear in the farmer's messages (same deterministic extractor + district-name scan) or saved profile, else a traced tool error tells the agent to ask. Re-run live: the garbled SMS now gets "আপনার জেলা কোনটি?". Tests: `test_intake_guard.py` (7), built on the real failure.
- Rule 15 tightened: SMS/USSD prose now carries **no figures** (`_SMS_NO_FIGURES` in `CHANNEL_NOTES`); new `sms_text.ranking_summary_sms` sends the ranking as a template SMS (score, profit, ceiling label for fertiliser-only crops, excluded crops named); `flows.send_summary` and the voice hang-up fall back to it. Live re-run: prose had no numbers, ranking SMS exact. SMS reply budget cut to 2 sentences (<130 chars) after replies were being trimmed at 3 parts.
- Agent now names crops only in Bangla (it wrote "লেন্টিল" once). Duplicate question on SMS ("জেলা কোনটি?" twice) removed in `ChannelReply.display_text`.
**Decision:** Voice keeps quoting tool figures in speech (a spoken plan with no numbers is useless); the SMS after the call is the authoritative record.
**Why:** The prompt said "ask, don't guess" and the model guessed anyway — same lesson as the digit filter: guarantees go in code.
**Rejected:** Rejecting any message with "?" runs (treats a symptom); checking numeric fields (false refusals on numbers typed differently outweigh the risk).
**Impacts:** Suite 583. Cost of the live runs: ~$0.04 per SMS turn with gpt-4o.

## [13:30] Real phone calls through Windows Phone Link (built; first real call pending)
**Did:** `backend/channels/voice/audio.py` (pure: resample, WAV, webrtcvad segmenter with pre-roll/silence/max, ADB call-state parser), `backend/channels/voice/phonelink.py` (the bridge: ADB call state + optional auto-answer, greeting, VAD turns, "একটু অপেক্ষা করুন" filler while the agent thinks, reply played into Phone Link's mic, SMS summary on hang-up; `--list-devices`, `--test-capture`, `--test-playback`), token-protected `/api/channels/bridge/voice/{turn,hangup,say}` returning WAV, `speech.synthesize(..., wav=True)`, `find_adb()` (Android SDK copy found automatically). Deps: `numpy==2.5.3` in requirements; `sounddevice==0.5.6`, `webrtcvad-wheels==2.0.14` in optional `backend/requirements-voice-bridge.txt`. Tests: `test_channels_phonelink.py` (10).
**Verified on this laptop:** Voicemeeter Potato is installed; the bridge finds "Voicemeeter Out B1" / "Voicemeeter AUX Input"; `--test-playback` fetched the Sarvam greeting through the backend and played it into AUX. adb found in the Android SDK; no phone attached yet.
**Decision:** Routing: Phone Link output → Voicemeeter Input (VAIO) → B1 → bridge; bridge → AUX Input → B2 → Phone Link mic. Half-duplex (no barge-in) for the pilot. The Quectel modem becomes optional.
**Why:** The team chose Phone Link (free, no root, no card, works for any caller on a normal local call).
**Rejected:** Twilio trial (5 verified numbers, `<Stream>` blocked on trial), Vapi (US numbers only), Tasker/MacroDroid for audio (same Android restriction; fine as triggers).
**Impacts:** Needs a person at the laptop with the phone paired for the first real call; README → "Real voice calls" has the steps.

## [15:22] Name is now Agrosfeer
**Did:** Renamed Agrosfera → **Agrosfeer** (Bangla অ্যাগ্রোস্ফিয়ার): `backend/branding.py`, `frontend/src/branding.js`, `vite.config.js` fallback, `.env.example`, README title/intro, docstrings/comments (`backend/__init__.py`, `api/__init__.py`, `api/main.py`, `agent/prompts.py`, `agent/llm_client.py`, `schemas.py` header only — no contract change, `index.html`, `index.css`), `requirements.txt` header, repograph, the ranking-SMS prefix assertion in `test_channels_core.py`. TASKLIST: dropped the "Agrosfera = Ukrainian agrochemical app" name-check item (no longer applies). Suite 583 passed; frontend lint clean, build OK.
**Decision:** Agrosfeer, the team's choice.
**Why:** "Agrosfera" collided with an existing agrochemical company and its ordering app. Name search for Agrosfeer: near neighbours AgroSfer, AgriSfeer; no exact match found.
**Rejected:** none.
**Impacts:** The concept note doc is updated in the next step. Anyone with `BRAND_NAME`/`VITE_BRAND_NAME` set in their own `.env`/`.env.local` or Replit secrets must change it there too, or the old name wins.

## [15:28] Live chat turn verified; futuremakers merged into master
**Did:**
- Stopped a stale backend left on :8000 since 03:26 (no `--reload`, so it predated the intake guard and the rename) and started a fresh one plus the Vite dev server.
- One live web chat turn through the Vite `/api` proxy (the browser's path): "রাজশাহী, ২ বিঘা দোআঁশ, সেচ আছে, রবি" → `rag_query` ×2 → `crop_scorer(Rajshahi, loam, irrigated, rabi, 2 bigha)` → Bangla reply quoting the scorer's figures unchanged (বোরো 83.22, মসুর 52.4, আলু 51.48, সরিষা 43.76; lentil/mustard carry the "সব খরচ ধরা হয়নি" ceiling label). 22 s, 27,937 in / 714 out tokens, $0.059.
- `origin/master` had 11 commits the Repl pushed itself (`.replit`, `start.sh`, `pyproject.toml`/`uv.lock`, `replit.md`, stub `main.py`/`package.json`, icons, static-dist serving in `api/main.py`, Vite port 5000 + `allowedHosts`). Dry-run merge clean; merged in a scratch worktree, **suite 583 passed on the merged tree**, pushed `master` = `956c3bd`. Fast-forwarded `futuremakers` to it.
**Decision:** Merge, not rebase or force: master's Replit commits stay as they are.
**Why:** CLAUDE.md §3 gate (suite green + one live turn) met; the Repl deploys from master.
**Rejected:** Adding numpy to the Repl's `pyproject.toml` from here — the deployed server never imports numpy (only the laptop bridge `voice/audio.py`/`phonelink.py` and their tests do), and `uv.lock` should be regenerated by `uv` in the Repl, not hand-edited. python-multipart is already in `pyproject.toml`.
**Impacts:** Local dev: Vite now serves on **:5000** (Replit's setting), not 5173 — README still says 5173 in places. Replit installs from `pyproject.toml`, not `backend/requirements.txt`: any new server dependency must be added in both. Concept note rename NOT done: this session has no Claude Docs connector (same failure as last session) — needs a hand edit or a session with the connector.

## [16:40] First real calls through Phone Link: answered, then no internet
**Did:**
- Laptop audio as found: only **Voicemeeter Standard** 1.1.2.2 is installed (no `voicemeeter8x64.exe`); the Potato-named devices (AUX, B2, B3) are drivers with no engine. The [13:30] "Potato is installed" was wrong — the documented AUX→B2 route cannot exist here. Standard's A1 pointed at unplugged "Headphones", so its engine was idle (sample rate 0) and nothing moved.
- Working route with Standard (both legs measured at 85% peak): **caller → Phone Link → Speakers → `Stereo Mix` → bridge**; **bridge → `Voicemeeter Input` (VAIO strip → B1 only) → `Voicemeeter Out B1` = Windows default mic → Phone Link**. A1 set to Speakers only to clock the engine; no strip routes to A1. Set via `VoicemeeterRemote64.dll` (ctypes) and the IPolicyConfig default-endpoint call. Run: `phonelink --capture "Stereo Mix" --playback "Voicemeeter Input" --auto-answer`.
- Phone: Samsung A55 (SM-A556E), dual SIM, ADB authorised. **ADB reveals the caller's number while ringing** (telephony.registry), blanks it once answered.
- Bugs found on the real phone and fixed in `backend/channels/voice/phonelink.py`: (1) `adb` output decoded as cp1252 → `UnicodeDecodeError` in the reader thread → `None` → crash mid-ring; now UTF-8 with replacement. (2) `KEYCODE_CALL` does not answer on Samsung; `KEYCODE_HEADSETHOOK` answered on the first try; answering now retries every 3 s alternating the two. (3) The number was read after answering (blank) → call filed under the `--caller` fallback; now the number seen while ringing is kept. (4) A failed TTS fetch raised and killed the bridge; now logged and skipped, and greeting/filler/sorry are cached at startup (`warm_up`).
- Call 2 answered, then `/bridge/voice/say` → 500: `getaddrinfo failed`. **The laptop's internet is this same phone's hotspot (SSID "Jawat", `swlan0` tethered), and the phone drops mobile data during a voice call** (call falls back off LTE — VoLTE likely off/unsupported on that SIM). Internet returned when the call ended.
**Decision:** The laptop must not get its internet from the phone that takes the calls (or VoLTE must keep data up during calls).
**Why:** STT, the agent and TTS all need the network mid-call.
**Rejected:** Pre-recording every reply (the replies are generated).
**Impacts:** ~40 min so far. README's Voicemeeter Potato steps need a Standard variant (this one). Windows default mic is Voicemeeter Out B1 during testing — old default (Microphone Array) saved; restore after.

## [17:30] Plan for the channel push: real phone first, USSD hardened, three new features
**Did:** Reviewed the state of every channel; committed the afternoon's Phone Link fixes (`8833326`). No new code yet.
**Decision:** (team's answers)
- Calls: the laptop gets internet from other Wi-Fi or a second phone; the Samsung only takes calls.
- New features approved: **crop-problem triage menu** (USSD + IVR, digits only, answer by SMS from the KB), **keypad digits on the hotline** (DTMF detected in the call audio, beside speech), **SMS menu mode** (the USSD menu over plain SMS — works on any real phone with no short code).
- Not approved now: missed-call callback.
- Real USSD: team will create a bdapps account; emulator until it is approved. I write the portal steps.
- Bug to fix first: USSD screens are tested at ≤182 chars, which is the GSM-7 limit; Bangla goes as UCS-2, where one screen holds ~80 code units (160 octets / 2). Most Bangla screens would be cut on a real network.
**Why:** Button-phone farmers cannot type Bangla free text, so the "প্রশ্ন করুন" menu does not work for them; most 16123 calls are pest/disease questions, which the triage menu covers.
**Rejected:** Twilio or any paid telephony (no budget); rooting the phone.
**Impacts:** Order: SMS over USB (adb forward/reverse) → USSD screen budget + resume → triage → SMS menu → DTMF → docs/merge.

## [18:05] SMS gateway hardened and set up over USB only
**Did:**
- `backend/channels/bridge/phone_up.py` (new): one command brings the phone up as the SMS gateway — waits for ADB, exempts `me.capcom.smsgateway` from battery optimisation, `adb forward tcp:8080` (laptop → phone API) + `adb reverse tcp:8000` (phone → backend), checks both ends, registers the 4 webhooks with fixed ids (re-run replaces, never duplicates), prints a checklist with the fix for each failure. `--watch` re-applies after a USB reconnect.
- `backend/api/channels.py` webhook: signed webhooks must carry a timestamp within ±5 min; each event `id` handled once (`webhook_seen` table in `store.py`); an `sms:received` older than 15 min is recorded but not answered; `sms:cancelled` handled.
- `store.update_sms_status` only moves forward (queued < sent < failed/cancelled < delivered) — delivery events arrive per part and out of order.
- `sms.py`: `withDeliveryReport`, `ttl: 3600`, optional `SMSGATE_SIM`; `SMSGATE_URL` defaults to `http://127.0.0.1:8080`.
- `bridge/adb.py`: UTF-8 decoding (same cp1252 crash as the call bridge).
- README "Real SMS" rewritten for the USB route; "Real voice calls" now documents the Voicemeeter Standard route that worked, and the internet rule. `.env.example` updated.
- `CHANNELS_RESEARCH.md` (new): the three research reports — USSD limits/timing, 16123 + rural context, SMSGate API facts, the KB-bounded crop-problem tree.
- Tests: 6 new in `test_channels_sms.py`. Suite **588 passed**.
**Decision:** Everything phone-side goes over USB (adb forward/reverse). No Wi-Fi, no tunnel, no TLS certificate.
**Why:** SMSGate refuses plain-HTTP webhooks except to `http://127.0.0.1`, and the phone's hotspot is unreliable (drops during calls). USB is the one link that is always there when the phone is plugged in. SMSGate retries webhooks for ~2 days, so without the id check a backend restart could send a farmer a second answer, days late.
**Rejected:** cloudflared/ngrok tunnel for webhooks (another moving part and an internet dependency); the phone's Wi-Fi IP (changes, and the laptop may not share its network).
**Impacts:** Not yet run against the real phone (it was unplugged). First run: `python -m backend.channels.bridge.phone_up --watch` with SMSGATE_USER/PASSWORD in `.env.local`.

## [19:20] USSD screens fit a real Bangla screen; crop-problem menu built
**Did:**
- **Bug:** a walk over every reachable USSD screen found **35 of 87 over 80 UCS-2 units** — including the first screen (118) — though the test passed them at ≤182 (the GSM-7 limit). Bangla USSD holds 80 units (160 octets / 2; CHANNELS_RESEARCH.md §1). `backend/channels/ussd.py` rewritten around a shared pager (`paginate`/`paged`/`pick_paged`): options split to fit, **9 = আরও, 0 = পিছনে on every screen**, error screens swap the title for "ভুল!" so an error variant is never longer. Main menu is two pages (1 ফসল পরামর্শ, 2 ফসলের সমস্যা, 3 আমার প্ল্যান, 4 আবহাওয়া | 5 সার-বালাইনাশক কিনুন, 6 ফসল বিক্রি, 7 শেষ উত্তর, 8 প্রশ্ন লিখুন); keys work from either page. Profile line compacted; alerts screen is short and the full template alert goes by SMS (action `sms`). `backend/market/ussd_menus.py` moved onto the same pager (menus now 5 and 6; short price-guide line on screen, dated guide by SMS).
- **Resume:** sessions time out (~180 s) and the intake is ~9 screens, so an unfinished intake or problem walk is saved per farm and offered on the next dial within 30 min ("আগের কাজ অসমাপ্ত। 1. চালিয়ে যান"); offered once (`store.latest_ussd_state`, `close_other_ussd_states`); a finished screen closes the walk. Requests slower than 1 s are logged.
- **Crop-problem menu (USSD 2):** `backend/kb/triage.py` — deterministic table from the agronomy review (CHANNELS_RESEARCH.md §4): crop → stage (day ranges, rice = after transplanting) → organ → symptom → extent [→ weather, only when a rule needs it: boro cold injury]. Candidates cite corpus passages with coverage S/W/P; SMS answer by template: likely causes, advice, a dose **only** for a single described (S) cause and not for a whole-field outbreak, scaled to the farmer's bigha by new `units.scale_rate` (incl. spray water), spray-safety lines only for sprays, SAAO + 16123. No KB coverage → fixed referral text. Carbofuran withheld (highly hazardous). `backend/channels/triage_menu.py` — screens (saved-plan shortcut "আলু, বপনের 31 দিন?"), `run_problem_action` (SMS up to 5 parts, `triage_reports` table, traced `crop_triage` tool_call/result for the monitor).
- Follow-up context: `run_turn(..., context_note=)` (additive, defaulted); `adapter._triage_context` attaches a problem report from the last 48 h to SMS/USSD turns, so "কোন দোকানে পাব?" is read against it.
- `store.triage_summary(since)`: counts by district × crop × cause, no farm ids — the pest-surveillance signal for the pitch.
- Tests: `test_channels_ussd.py` rewritten (BFS over every reachable screen incl. market and problem menus asserts ≤80; resume; stale walk not offered), new `test_triage.py` (19: every dose/advice number must appear in its cited passage, only S causes carry doses, carbofuran never quoted, rule ↔ menu consistency, weather gating, scaling, menu walk, action + trace, context). **Suite 615 passed.**
**Decision:** The problem answer is a template from the table, not an agent turn: instant, no LLM cost, and nothing the KB does not say. The agent handles the follow-up questions, with the report as context.
**Why:** Farmers on button phones cannot type Bangla questions; most 16123 calls are pest/disease. And a model picking a diagnosis would break rule 1's spirit.
**Rejected:** Letting the agent diagnose from the menu answers (unbounded, slow, costs per report); an ASCII/Banglish menu fallback now (unverified need — BD feature phones have had Bangla since 2012; test on a real feature phone first, noted in CHANNELS_RESEARCH.md).
**Impacts:** Menu numbers changed (market 4→5, 5→6; ask 6→8; plan 2→3; alerts 3→4) — README updated. The integrity test caught two real errors while building: the cold-injury advice cited the wrong passage (fixed with `advice_kb`), and a Bangla numeral in "বারি মসুর-৮" (rule 10).

## [20:30] SMS menu mode, keypad on the hotline, bdapps steps; verified in the browser
**Did:**
- `backend/channels/sms_menu.py` (new): text "মেনু"/"menu" → the USSD menu by SMS (`ussd.step` unchanged); digit replies continue an open walk (idle limit 15 min); free text leaves the menu and goes to the agent; the question screen takes free text; an unfinished USSD walk (30 min) is offered back. `flows.handle_inbound_sms` checks it first, then marketplace keywords, then the agent (one agent path). Welcome SMS mentions "মেনু". `store.get_ussd_state_at`.
- Keypad on the hotline: `voice/audio.py` — `dtmf_key` (Goertzel on the 7 row/col tones; dominance, twist ≤8 dB, tones must carry ≥60% of frame energy), `DtmfDetector` (2-frame hold, one report per press), `dtmf_tone`. Synthetic check: all 12 keys through noise and an 8 kHz round trip; no false keys on a harmonic voice-like signal or noise; ~0.4 ms/frame. `voice/ivr.py` (new): keys drive `ussd.step`, screens spoken ("ফসল পরামর্শ, 1 চাপুন", "# চাপুন" for numbers, * repeats the last screen); a crop-problem answer is spoken on the call **and** sent by SMS (for farmers who cannot read). Routes `POST /api/channels/{emulator,bridge}/voice/keys`. `phonelink.py`: detector runs on the same 30 ms frames as VAD, a tone resets the partial utterance, number entry buffered until # or a 3 s pause, speech within 1.5 s of a key ignored, greeting mentions the keypad, `--test-dtmf` diagnostic.
- Browser emulator: the phone keypad sends keys during a call (`PhonePage.onKey` → `VoiceCall pressed`), with the real DTMF tone as feedback; number entry in a ref (a state-updater side effect would double-send under StrictMode).
- bdapps USSD route: live mode acknowledges the MO at once and sends the screen in the background (no outbound call inside the gateway's request); simulator unchanged.
- README: Real USSD through bdapps (free account; laptop backend + Cloudflare quick tunnel because outbound `/ussd/send` needs a whitelisted IP and Replit's changes per deploy), SMS menu mode, keypad steps, status rows. TASKLIST: the team's device checks, bdapps, agronomist review, surveillance view, KB gaps.
- `.claude/launch.json` (backend :8000 with reload, frontend :5000). The backend left running since 15:35 had stopped reloading (new routes missing, USSD 500); restarted.
- Tests: `test_sms_menu.py` (7), `test_channels_ivr.py` (10). **Suite 632 passed**; frontend lint + build clean.
**Seen working in the browser (built-in pane, live backend):** dial `*3700#` → 2 → lentil → flowering → pod → holes → half → answer SMS in the inbox (5 parts), USSD session with the traced `crop_triage` in the monitor; a call → key 2 → the problem menu spoken (Sarvam TTS, no error) → * repeated it; SMS "মেনু" → menu by SMS (offered the call's unfinished walk back — cross-channel resume working).
**Decision:** One menu engine, four transports (USSD, SMS, keypad-on-call, emulator). Speech stays the primary voice input; keys are an extra until a real call proves tones survive AMR + Bluetooth.
**Why:** A farmer who cannot read or type gets the same menu by ear; one engine means one set of tests and one screen budget.
**Rejected:** A separate IVR menu tree (would drift from USSD); sending bdapps screens from Replit (no static IP).
**Impacts:** Needs the team: real-call `--test-dtmf`, real SMS via `phone_up`, bdapps account, a real button phone for Bangla rendering.

# 2026-09-29

## [00:55] First real SMS through the phone; an SMS loop found and closed
**Did:**
- Phone (SM-A556E, dual SIM: test "farmer" SIM …766, service SIM …884) on USB; `phone_up` all green after three setup fixes: (1) Android's restricted-settings block on the sideloaded app — the team allowed restricted settings + SMS permission; (2) `SMSGATE_SIGNING_KEY` in `.env.local` held a 49-char value that was not the app's (8-char) webhook key → every webhook 401; replaced with the app's key; (3) the app's **Cloud server** switch was on — turned off so farmers' SMS never leave the phone. Turning the SMS permission off/on left **SEND_SMS** ungranted (gateway error `uid … does not have android.permission.SEND_SMS`), then left the app's SMS receiver detached; a force-stop + START SERVICE fixed receiving.
- Verified on real SIMs: "Hello" and "মেনু" received by webhook over `adb reverse`; the menu SMS **Delivered** (gateway state); "2" → the crop menu sent.
- **Bug — SMS loop:** the service SIM (…884, the phone's default sender) texted the test SIM in the same phone; after the app restart, the bot's own menu came back as an incoming "farmer" message from …884 and the bot answered itself three times (#40–45) before the backend was stopped. **Fix:** `flows.loop_reason` — never answer (a) `CHANNEL_OWN_NUMBERS`, (b) text matching an SMS we sent in the last 15 min, (c) >8 messages per phone per 5 min. Ignored messages are logged with the reason. `CHANNEL_OWN_NUMBERS=…884` set locally; `.env.example` documents it.
- **Bug — internal text leaked to a farmer:** fed its own menu, the model copied the `ask_farmer` tool note ("The question is now on the farmer's screen with a widget. End your turn…") into an SMS. `ask.ASK_NOTE` constant; `adapter.scrub_internal` drops any sentence carrying a tool-note fragment from every phone reply.
- Diagnostics kept: a refused webhook logs why (missing header / mismatch / clock skew, never the key); a failed send logs the gateway's reason.
- Tests: 4 new in `test_sms_menu.py`. **Suite 636 passed.**
- `FUTUREMAKERS_BRIEF.md` (new): the competition's Round 1 requirements, 7 judging criteria, IP terms, from the site's FAQ.
**Decision:** Loop protection lives in the flow, not in the provider, so every SMS transport gets it.
**Why:** An auto-responder that can hear itself will eventually talk to itself — dual-SIM testing just made it happen first.
**Rejected:** Relying on the own-number list alone (a test SIM in the same phone, or an operator echo, still loops).
**Impacts:** For demos, a second phone as the farmer avoids dual-SIM confusion. ~50 min.

## [01:05] Real SMS menu walk verified on real SIMs
**Did:** From the test SIM: মেনু → 2 → 5 → 3 → 4 → 2 → 2 — each menu screen and the lentil pod-borer diagnosis arrived by real SMS within seconds (triage report `covered`, `pod_borer`). The loop guard held in real traffic: five of our own replies that landed back on the phone were logged `ignored: own number`. Cleanup: SMS menu mode no longer sends "উত্তর কয়েক মিনিটে SMS-এ আসবে" before an instant template answer (crop problem, alert) — it cost an SMS and preceded the answer by 0 s; kept for agent answers. Suite 636.
**Decision:** SMS channel status in the README moves from "simulator" to "verified on real SIMs".
**Why:** First live proof of a button-phone flow end to end.
**Rejected:** none.
**Impacts:** Still unverified live: voice call (needs a second phone), keypad tones, bdapps USSD.

## [01:20] Plan: farmer profiles and return-visit personalization (proposal, not built)
**Did:** Wrote `PROFILE_PLAN.md` from the team's brief: profile per phone in three layers (who / land / season) with source + date on every fact and freshness rules; episode memory with follow-ups; a deterministic return briefing (days since last contact, stage computed from the sowing date, due tasks, open follow-ups, stale facts); gap buckets decided in code (same day / 1–7 d / 8–45 d / harvest / new season / >12 months) that set what the agent leads with; outcome capture (yield, price) as the impact metric; consent, "তথ্য মুছুন", shared-phone handling. Build order ≈1.5 days in three steps.
**Decision:** Build on the existing farm id, `farms` table and fresh-session injection; the briefing replaces the raw profile dump. Dates and stages are computed in code, never by the model.
**Why:** The team wants a farmer to never repeat himself, and the next question to depend on how long he has been away.
**Rejected:** Letting the model infer "how long since" or the crop stage from history (rule 1); storing free-text LLM summaries with figures (rule 15).
**Impacts:** Next session is the Round 1 docs (team's call); this plan is ready for the docs' "solution" section and for a later build.

## [01:55] Round 1 form answers v2: the problem is the farmer's, not ours
**Did:** `ROUND1_FORM.md` (new): rewrite of Shafin Bhai's form draft. Every section is under its word limit (counted with a script). Checked the facts against sources. The AIS 16123 page says 8 am to 8 pm, closed Fri/Sat/government holidays, 25 paisa/min. BSS says "around 200 calls daily" (Aug 2024 to Mar 2025). Rahaman et al. 2018 (120 rice farmers, 3 districts): 69.16% get pesticide advice from dealers, 7.5% from extension workers. Tools = 17 (tools_spec.py), default model gpt-4o, tests 636.
**Decision:** Lead with one farmer problem: when something goes wrong in the field, the reachable adviser is the pesticide seller. Order of jobs: crop problem → this week's tasks/alerts → what to grow and its profit. The marketplace is reduced to one paragraph as the funding model. "Digital inclusion" is how the solution fits the category, not the headline problem.
**Why:** A senior reviewer asked "what one problem do you solve for a farmer?" and "consultancy by an AI agent" is a solution, not a problem. The crop-problem menu matches most 16123 calls and works without reading, but v1 never mentioned it.
**Rejected:** Pitching "access to AI" as the problem (farmers do not ask for AI; judges have heard "digital divide" often). Claiming a digital-literacy training effect (we have no mechanism or evidence). Dropping 16123 as a competitor (we pitch it as a partner and handover target).
**Impacts:** Before submitting, reconcile GSMA 26% (rural adults who own a smartphone) with BBS 69% (almost certainly rural household access). Open the second dealer source before quoting it. The video storyboard should follow this problem framing.

## [02:45] Video tooling: FFmpeg on D:, brag plugin installed
**Did:** FFmpeg 9.0.2 (gyan.dev full build) unpacked to `D:\tools\ffmpeg-9.0.2-full_build\bin` and added to the user PATH. Brag plugin 0.4.0 (latent-spaces/brag, a HyperFrames launch-video skill) installed at user scope from its HTTPS URL. Deleted the two failed FFmpeg downloads in the WinGet temp folder.
**Decision:** Use HyperFrames (through brag) as the video renderer, not Remotion. Direct it with our own storyboard; plain one-command `/brag` output is off-genre for a problem/impact pitch.
**Why:** The winget package for Gyan 9.0.2 is broken (its manifest expects an `ffplay.exe` the zip does not have), but the zip itself passed winget's hash check. The BtbN 8.1 download failed its hash check, so it was not used. The SSH clone of the marketplace failed because github.com is not in known_hosts; HTTPS works.
**Rejected:** Skipping the hash check (security). Running two renderers.
**Impacts:** Brag's voiceover (Kokoro) has no Bangla voice; use Sarvam or a human voice. Brag has no hooks; its inspect step skips .env/keys.

## [11:42] Round 1 form answers v3: the idea and the plan, not the gaps
**Did:** Rewrote `ROUND1_FORM.md`. Removed "Current status" and "Limitations and risks". Added a farmer's journey (Rahima, a made-up example) and "Responsible by design" (read-back, keypad fallback, hashed numbers, handover). Unbuilt parts (handover, speech tuning on farmers' voices) now sit in the Year 1 plan. Every section is under its word limit (script count: 267/472/287/297/296/187).
**Decision:** Round 1 answers describe the idea, how AI enables it and the 2–3 year plan. They do not list what the prototype lacks.
**Why:** Round 1 asks for an idea; a prototype is not required. Listing gaps spent words on things the judges did not ask about.
**Rejected:** Dropping the prior-work mention (the FAQ requires disclosing prior development; it stays as one positive sentence in Feasibility). Dropping risks entirely ("Responsible & ethical AI use" is a judging criterion; kept as safeguards).
**Impacts:** What really works today (SMS real, USSD simulator, voice via the Android bridge, demo marketplace rows) is in the team notes for Q&A. Answer honestly if judges ask. The video is next, in a separate session.

## [12:08] Video storyboards: Mahmud, three versions; the form's crop problem has no rule
**Did:** Wrote `VIDEO_STORYBOARDS.md`: three ~1:55 storyboards (A: a story film of one Friday night; B: a proof demo with voice, keypad and SMS side by side; C: a split screen of the same night with and without the service), a comparison, and shared rules.
**Decision:** The farmer is **Mahmud** (male, 2 bigha boro, button phone), replacing Rahima, as the team asked. His problem is **stem borer / deadheart** (boro, 20–54 days; Virtako 40WG 75 g/ha scaled to his land by code), not brown leaf spots. Recommended cut: C's split-screen structure, with every "with the service" beat a real recording (call, SMS, rain alert).
**Why:** `backend/kb/triage.py` has no rule for boro + leaf + spots, so the form's journey shows an answer our own system cannot give. The rain alert's real wording is "do it on the next dry day", not "wait two days".
**Rejected:** Illustrative ৳ loss counters in version C (rule 2: invented numbers). Kokoro TTS for the narration (no Bangla voice).
**Impacts:** `ROUND1_FORM.md` still tells the Rahima / brown-spot story. It should change to match the video before submission (waiting on the team). Before shooting, run Mahmud's case through the real system and use its exact text and gram figure.

## [13:10] Drawn storyboards for the three video versions
**Did:** Drew all three storyboards (A 11 shots, B 11, C 9) as sketch panels on one page, with timecodes, shot types, Bangla voice-over, honesty labels and an edit timeline per version. Published as a private artifact (https://claude.ai/artifact/XHgd7nBEVBPdda1sTY7ynm). The source HTML lives in the session scratchpad, not the repo.
**Decision:** No new decisions; the drawings follow `VIDEO_STORYBOARDS.md`. Where the system gives a figure (the gram dose, the rain date), the panels leave a "__" blank to fill from real output.
**Why:** The team wanted to see the shots, not just read about them.
**Rejected:** AI-generated images per shot (30 frames that don't match each other, and fake-looking farmers).
**Impacts:** The team has to share the artifact from its Share menu before others can open it.

## [13:40] Team direction: new problem framing and tone for the video; the build works here
**Did:** Took the team's feedback on the storyboards. Ran `npm run build`: it passes (3 s, only a chunk-size warning). The dev server (:5000) and the built app served by the backend (:8000) both open the sign-in screen on this machine.
**Decision:** 16123 is not mentioned anywhere in the video. We do not compete with it. The problem is that a rural farmer's advice comes from whoever sells the inputs, while expert, data-backed advice (the kind city people get through smartphones and AI) does not reach him. What we offer: it works out the numbers, answers any time, scales, and has no social barrier. Digital inclusion means rural people get the same digital advantage. Tone: warm, everyday Bangla in the style of a Bangladeshi ad (bKash as a reference), not dramatic and not formal. Brand colours should echo Grameenphone, with a green tone.
**Why:** Farmers can call a hotline the next morning, so "it is closed at night" is not the real problem. The old copy sounded machine-written.
**Rejected:** The 16123-closed storyline; the dramatic night-rescue tone.
**Impacts:** The storyboards get redone (v2) after the team answers the palette, logo and footage questions. "Build does not work" needs the team's exact symptom, because the build passes here.

## [14:40] Root npm scripts; website redesign, first pass (home page + GP-blue palette)
**Did:** The team's "npm run dev fails" was `npm run dev` run in the repo root, whose Replit-made `package.json` had no dev script. Added `scripts/dev.mjs` plus root scripts: `npm run dev` starts the API (:8000) and Vite (:5000) together; `npm run app` builds and serves the site from the API on :8000, as Replit does; `npm run build`. Redesign: new tokens in `frontend/src/index.css` (telecom blue `--brand*` #0071bc for actions and identity, paddy green `--paddy*` for crop facts; `--green*` renamed to `--brand*` everywhere), Baloo Da 2 headings and Hind Siliguri body from Google Fonts, `components/BrandMark.jsx` placeholder mark (paddy stalk over a signal arc) and new `public/icon*.svg`, and a new `pages/HomePage.jsx` + `home.css` as the front door. The chat advisor moved to `#/app`.
**Decision:** The home page links every working part (button-phone emulator, web advisor as guest, market, live monitor, dealer and buyer pages). Every statistic shows its source. The phone mock shows the system's real SMS for Mahmud's case (boro, deadheart, 2 bigha → "ভিরতাকো 40WG … মোট 20 গ্রাম"), shortened only by leaving lines out.
**Why:** The team wants a brand people feel close to, like GP or bKash, and judges need to reach the whole system, not only the chat.
**Rejected:** A full-viewport hero or gradients (CLAUDE.md frontend rules). Committing on the team's behalf (they did not ask).
**Impacts:** The live SMS still ends with "কৃষি কল সেন্টার: 16123" (`HOTLINE_LINE`, triage.py); the video must not show it, so the team has to decide whether to drop it. Name and logo are open: `BrandMark.jsx` and `public/icon.svg` are placeholders. Verified: build passes; home, #/app?guest, #/phone and #/market render; no horizontal overflow at 375 px.

## [16:30] Farmer interview, brand kit v0.1, name candidates, handoffs for the next sessions
**Did:**
- Turned Shafin Bhai's call with his uncle (Parhail, Dinajpur) into `FIELD_INSIGHTS.md`.
- Built `brand/`, laid out like the team's WaffleUp brand kit: `BRAND.md`, `VOICE.md`, `NAMES.md`, `LOGO-BRIEF.md`, `tokens/brand-tokens.{json,css}`, `assets/{logo,fonts}/README.md`, `guidelines/index.html`.
- Mapped the brand into `frontend/src/index.css`: Shyamol green `#0F5C3B` primary, Akash blue `#1570B8` for phone and links, Dhani gold `#E3A92F` as the accent, Poli ivory `#F6F4EC` as the ground, Tiro Bangla display and Hind Siliguri text. Restyled `home.css`, the icons and the PWA theme colour.
- Wrote `WEBSITE_HANDOFF.md` and updated `VIDEO_HANDOFF.md`.

**Decision:**
- The brand's role is "the one calm voice that knows" (Sage with a Caregiver's heart). Green leads; blue is kept for phone and channel moments (the GP echo); gold is rare.
- Recommended name: জিগাই (Jigai). Tagline: জেনে বুঝে চাষ.
- Ten names came back with no existing organisation found by web search (not a legal clearance).

**Why:**
- The interview shows the pain is confusion and having no one to trust ("every seller says something different"), plus losses from fertiliser amounts and timing. Weather warnings only help when they say what to do. His village is mostly on smartphones.
- The team found the all-blue look casual.

**Rejected:**
- Agrosfeer: AgroSpheres is a US pesticide-delivery firm working with BASF and Bayer.
- Names already in use: Shufola, Folon, Fosholi, Krishi Bondhu, Abad, Nidan, Thikthak, Thaor, Shalik, Jiggasha, Shoja Kotha, Nishchinto (Agro).
- Dosor: it means "accomplice" in current politics.
- Baloo Da 2: too playful.

**Impacts:**
- Name and logo are still open. Rename only in `branding.py` and `branding.js`; logo files go to `brand/assets/logo/`.
- iFarmer's Folon already has an AI voice agent, and DAE's BAMIS has AI disease detection. Both are competitors the docs should know about.
- The contrast ratios in BRAND.md were computed by hand: re-check them with a tool.
- The web search tool failed for about 20 minutes this session. If a later session sees "classifier gave no verdict", wait and retry.

## [18:30] Name is Sudin (সুদিন); brand direction v1 with a new palette and four logo concepts
**Did:** Wrote `brand/guidelines/sudin-brand-v1.html` (published privately: https://claude.ai/artifact/6xE7GtKaMbxuR32vcNLQFt). It holds the brand essence, a new palette with the colour-psychology reasoning, WCAG contrast figures computed by script, four vector logo concepts (A sunrise with a sprout, B leaf, C rising grains, D leaves holding the sun) shown in context, and five tagline options. Code is not renamed yet.
**Decision:** The name is সুদিন / Sudin (team decision). The problem framing moves to diagnosis and falling yield: farmers are trying, but they can't tell what disease or nutrient gap is hurting the crop, the expert help at the agriculture office is far away, and yields are falling ("50 মণ to 30 মণ", one farmer's figures). Sudin brings that expertise to the phone, the way mobile banking brought banking to the hand. Never say the hotline fails. Palette v2 is one scene with one light: Deep Shyamol #0D3B2E, Turmeric Sun #F2A231, Leaf #1B7048, Young Paddy #A8D65C, Straw #FAF5EA, Soil Ink #11201A, and Terracotta #B8472A for warnings only. Akash blue is dropped. My recommendation is logo A and tagline T1, "ফলন ফিরুক, সুদিন ফিরুক".
**Why:** The team said v0.1 felt detached, sloppy and like a government portal, and that the "সোজা বলে" line described our tone instead of the farmer's problem.
**Rejected:** AI image-model logos, because they produce raster output that is hard to edit or keep consistent. The flag green #006A4E, because it reads as a government portal. Blue as a brand colour, because it made the palette feel detached.
**Impacts:** The team must pick a logo (A–D) and a tagline (T1–T5). After that: export the logo set to `brand/assets/logo/`, rename in `branding.py` and `branding.js`, replace the tokens, then redesign the UI. `brand/BRAND.md` and `brand/tokens/` still describe v0.1 until then.

## [23:05] Round 1 form v4: rebuilt on the farmer interview, 16123 removed
**Did:** Rewrote `ROUND1_FORM.md` as v4 and kept the old version as `ROUND1_FORM_v3.md`. Added "Part 0", a table that maps each thing the Dinajpur farmer said to a feature. All six answers are within the form's word limits (Problem 294/300, Solution 495/500, AI 288, Impact 290, Feasibility 285, Differentiation 170). Updated repograph.md.
**Decision:** The name is Sudin (সুদিন), from the branding session. The problem is confusion, with no one to trust, plus not being able to describe the crop problem, plus losses from fertiliser amount and timing. The seller's profit motive is the opening fact. 16123 and the extension office are gone from the form; hard cases go to "a human agronomist". Smartphone and button phone are presented as equals, and the photo check is described for smartphones. The farmer is Mahmud (boro, stem borer, 2 bigha), as in the storyboards. The marketplace is one paragraph. Technical detail is turned into plain words.
**Why:** The team asked for the form to follow the farmer's view and the social good, not the technology. v3 still used the 16123 and Rahima story, which the team dropped.
**Rejected:** Button-phone-first framing (the interview says smartphones are common in his village); marketplace as a full pillar (dilutes the advice story).
**Impacts:** The photo check and the agronomist handover are in the idea but not live in the phone flows (see the team notes). The live SMS still ends with the 16123 line. The team will rewrite the prose in their own words.

## [18:55] Brand line: two words for the long run; "ফলন ফিরুক, সুদিন ফিরুক" dropped
**Did:** Replaced the tagline section of `brand/guidelines/sudin-brand-v1.html` (artifact v2) with five two-word brand lines. The masthead now shows the recommended one.
**Decision:** Recommended brand line: **স্বপ্ন ফলুক** ("may your dreams bear fruit"). ফলা means both "to grow a harvest" and "to come true", so one word covers the field and the family's future. Other options: সোনা ফলাও, আসছে সুদিন, জেনে ফলাও, নতুন ভোর. The team picks. Problem-led lines stay as ad headlines, not as the brand line.
**Why:** The team wants a line that lasts for years, like GP's "চলো বহুদূর", that looks to a better future instead of "getting good days back".
**Rejected:** "ফলন ফিরুক, সুদিন ফিরুক": it looks backward and it is a sentence, not a line. A web search found no brand already using স্বপ্ন ফলুক or সোনা ফলাও. That was a quick check, not a trademark clearance.
**Impacts:** Once the team picks, the line goes under the logo, on video end cards and as the SMS sign-off.

# 2026-09-30
## [01:10] Name is now উর্বর / Urbor; brand v1 built in Figma (three marks, fonts, engraved paddy pattern)
**Did:**
- Made the Figma file "উর্বর Urbor · Brand v1" (https://www.figma.com/design/GxcGtl0gc4w8QSVzmCNn9m) with five frames: cover, three logo concepts, colour, type, pattern.
- Added `brand/scripts/marks.mjs`, which writes the three marks to `brand/assets/logo/concepts/`: A the bowing ear, B fertile-land seal, C alpana of grain.
- Added `brand/scripts/paddy-engraving.mjs`, a seeded engraved-paddy line-art generator. It writes `brand/assets/pattern/paddy-hero.svg`, and the Figma board runs the same function.

**Decision:**
- Name: উর্বর / Urbor (team: "সুদিন" has a bad homophone). Tagline: স্বপ্ন ফলুক.
- Story: fertile soil is Bangladesh's gift, it is being lost, and expert diagnosis is how we protect it.
- Palette v2 is kept.
- Brand fonts:
  - Noto Serif Bengali: Bangla display and wordmark.
  - Noto Sans Bengali: Bangla text; it ships on most Android phones.
  - Fraunces: Latin display.
  - Instrument Sans: Latin text.
  - Galada: tagline only, as a hand-signed note.
- The pattern is rice, not wheat: the team's reference images were wheat. My recommendation is mark A.

**Why:**
- The team found the earlier fonts unnatural and asked for elegance built on engraved grain patterns.
- Handwritten type raises perceived human presence (Schroll et al., JCR 2018).
- Familiar textbook-style Bangla reads as trustworthy.

**Rejected:**
- Tiro Bangla: felt stiff.
- Anek, Atma, Mina, Baloo: too techy or too playful.
- Raster AI illustration for the pattern: it can't be recoloured or kept consistent, and it is heavy on cheap phones.
- Hand-pasting SVG path data into Figma: too big for one call, so the generator runs inside Figma instead.

**Impacts:**
- **Name risk:** Crunchbase lists "Urbor", a Dhaka agri-fintech for farmers (finance, market data, guidance). Its site urbor.io did not resolve on 30 Sep. urbor.net is an organic shop. The team must decide before the code is renamed.
- `branding.py`/`branding.js` still say Agrosfeer.
- The website redesign waits on the logo choice.

## [01:40] Name final: উর্বরা / Urbora; seal logo, engraved grain, website v1 with a web crop-problem check
**Did:**
- Docs now use উর্বরা: `brand/BRAND-CORE.md`, `VIDEO_HANDOFF.md`, `ROUND1_FORM.md`, and notes in `BRAND.md` and `NAMES.md`.
- The logo is a seal. Canva AI made a study of it; `frontend/src/lib/seal.js` is the vector master. `brand/scripts/seal.mjs` writes it to `brand/assets/logo/`, and `export-logos.ps1` writes the PNGs and lockups.
- The grain pattern is redrawn in the style of the team's references. The source is `frontend/src/lib/engraving.js`; `brand/scripts/build-web-assets.mjs` writes `frontend/public/{icon*,pattern/*}`.
- Website:
  - palette v2 and brand fonts, via the tokens in `index.css`
  - new `BrandMark` and `Lockup` components
  - home page rebuilt around the brand story
  - new `CropCheck` component with `/api/triage/{options,check}` (`backend/api/triage.py`), running the deterministic keypad-menu table
  - dose scaled by `units.scale_rate`, with provenance
- Farmer-facing SMS and USSD text now uses the Bangla name (same length as "Urbora", so segment budgets are unchanged).
- Dev ports can be changed: `VITE_PORT` / `API_PROXY_TARGET`, plus `backend-alt`/`frontend-alt` in launch.json.

**Decision:** The web crop check never shows the 16123 line; it keeps the SAAO and safety lines.

**Why:** Diagnosis is the farmer's first pain (FIELD_INSIGHTS), and the team asked for richer features.

**Rejected:** A raster AI logo as the final mark: it can't scale to a favicon or be recoloured.

**Impacts:**
- Tests: 646 green (5 new).
- Build passes.
- Verified in the browser at about 800px and 1366px: the crop check runs end to end and shows boro deadheart, 2 bigha, 20 g.
- Not yet restyled or checked on the new brand: `#/app`, `#/phone`, `#/market`. They inherit the tokens.
- The Figma board still shows the old marks.
- Nothing is committed.

# 2026-09-30

## [02:30] Home page: consultancy message, real-looking photos, interactive phones
**Did:** `frontend/src/pages/HomePage.jsx` + `home.css` rewritten around the promise "one farm advisor for every question across the season", not just crop disease. New hero on a sunrise paddy photo. New `#services` section: eight kinds of help (what to grow, soil and fertiliser, pest and disease, irrigation, weather, cost and profit, buying inputs, selling harvest); clicking one shows an example chat on a photo of a real budget Android (HTML laid over the blank screen; auto-rotates until the visitor clicks). `#how` now shows a button-phone photo with the real USSD main menu (`backend/channels/ussd.py` MAIN_ITEMS; tap turns the page). Field photo above the story, sunrise closing band with the tagline, engraved wheat pattern in the market band. Gentle motion: sections fade in once, hero photo drifts slower than the page; all off under `prefers-reduced-motion`. Five images in `frontend/public/img/` (WebP, 1200 px copies for phones). `brand/IMAGE_PROMPTS.md` records the prompts.
**Decision:** Images are AI-generated on the team's Higgsfield account (GPT Image 2.5), because stock-photo hosts are blocked from the build container and the team asked for it. Every one is labelled "প্রতীকী ছবি" on the page and in the footer, so none can pass as a real farmer (rule: no fake content). Example chats carry numbers only where they are real: the pest dose is the system's real triage reply, ৳27/kg urea is the cited government price, the sell line is the real SMS command; the rest are worded without figures. Screens are labelled "উদাহরণ কথোপকথন" except the real one.
**Why:** The team said the site read as a disease checker, and the drawn phone looked fake.
**Rejected:** a drawn/CSS phone (the old one); stock photos (hosts blocked; licence checks); 15 images (team asked for a few); a video hero (weight on cheap phones).
**Impacts:** Build passes, lint clean. Checked at 1440 px and 390 px in Chromium: topic clicks, USSD page turn and fade-ins work. Google Fonts are blocked in the build container, so screenshots used fallback Bangla fonts; check on a normal connection. The crop check needs the backend running.
