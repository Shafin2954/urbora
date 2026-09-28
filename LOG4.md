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
