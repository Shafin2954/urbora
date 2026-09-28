# Channels research — verified facts behind the phone channels (2026-09-28)

Collected by three research passes (LOG4 [17:30]). Every claim had a source when it was
written; "unverified" means we looked and found none. Re-check before quoting to judges.

## 1. USSD limits and timing

- One USSD screen carries **160 octets**: 182 chars in GSM-7, **80 in UCS-2 (Bangla)**
  (3GPP TS 23.038; emnify USSD intro). Bangla vowel signs and hasanta are separate code
  points, so Python `len()` = UCS-2 units. **Our budget: ≤75 units per Bangla screen**,
  182 for ASCII screens.
- Session timing (Kenyan operators, used as a proxy; BD operator figures unverified):
  ~180 s per session, 30–60 s per screen, the app must answer within ~15 s.
  **Ours: answer each request in <1 s, no LLM and no outbound HTTP inside a request;
  plan 4–5 screens per session; save state so a dropped session resumes on redial.**
- bdapps: developer registration free; subscribers are charged ~Tk 1–2 per USSD menu
  (dev.bdapps.com/pricing.php); apps are reviewed before going live; `*213#` is the
  simulator service code; Robi/Airtel only (production code format unverified).
  Outbound calls need a whitelisted IP; Replit autoscale has no static IP.
- BTRC: Bangla keypad mandatory on handsets imported since Feb 2012; Bangla SMS must be in
  Bangla script (2018). Bangla rendering in USSD popups: **unverified** — keep an ASCII
  fallback and test on a real feature phone.
- DTMF: in GSM the handset sends key presses as signalling; the MSC regenerates the tone
  in-band toward the far end (TS 23.014), so on mobile-to-mobile calls the tone usually
  reaches the callee as (AMR-distorted) audio. Through Phone Link/HFP: **unverified** —
  speech stays the primary input, keypad is an extra.

## 2. Krishi Call Center 16123 and rural context

- 92,094 calls Jul 2025–Jun 2026 (BSS); topics named: pest/disease, fertiliser, weather;
  no percentage breakdown published.
- Cost: 25 paisa/min (AIS; Dhaka Tribune 2016); FAO lists it toll-free — sources conflict.
- Rural smartphone ownership 69% vs urban 81% (BBS Q1 FY26); literacy 74.66% national,
  rural 71.56% (Census 2022).

## 3. SMS Gateway for Android (capcom6, `me.capcom.smsgateway`), app v1.76

- Local Server: port 8080, Basic auth. `POST /message` (or `/messages`) body
  `{"textMessage":{"text":…},"phoneNumbers":["+880…"],"withDeliveryReport":true,
  "ttl":3600,"simNumber":1}` → `{"id","state":"Pending"}`. Long/Unicode split automatically.
- Webhooks: `POST /webhooks {"id","url","event"}`, one per event. Envelope
  `{deviceId,event,id,webhookId,payload:{messageId,message,sender,recipient,simNumber,receivedAt}}`.
  `X-Signature` = hex HMAC-SHA256(key, raw body + `X-Timestamp`); accept ±5 min.
  HTTPS required **except `http://127.0.0.1`** → use `adb reverse`. 2xx within 30 s or it
  retries 14× over ~2 days → dedupe on `id`. `sms:delivered` fires per part.
- `adb forward tcp:8080 tcp:8080` works (Ktor binds all interfaces; inferred from source).
- Samsung kills the server unless battery is Unrestricted. Forwards vanish on reconnect.
- The app does not do calls or USSD. Companion CallGate (port 8084) is "not production ready".
- Implemented in `backend/channels/bridge/phone_up.py` and the webhook in `backend/api/channels.py`.

## 4. Crop-problem triage tree (agronomy spec, KB-bounded)

Rule: the leaf → candidate lookup is a **deterministic table**; the LLM never picks the
diagnosis. A leaf not listed = `NO_KB` → fixed SMS "তথ্য যথেষ্ট নয় … SAAO বা 16123".
Stage boundaries are **derived from `season_plan` / `pest_risk` offsets, not stated by a
source → confidence low**; they travel as ranges. Rice = days after *transplanting*
("রোপণের"), never "বপনের".

Screens: [S0 saved-plan shortcut] → S1 crop → S2 stage → S3 organ → S4 symptom →
S5 extent (অল্প / অর্ধেক / প্রায় সব) → S6 last 7 days (বৃষ্টি/কুয়াশা / সার দিয়েছি / দুটোই / না).

Stage → days (rice: after transplanting):

| Crop | চারা | কুশি/বাড়ন্ত | থোড় / আলু ধরছে / ফুল | ফুল / শুঁটি | দানা / পাকা |
|---|---|---|---|---|---|
| aman_rice | 0–17 | 18–59 | থোড় 60–74 | ফুল 75–89 | 90–120 |
| boro_rice | 0–19 | 20–54 | থোড় 55–74 | ফুল 75–94 | 95–125 |
| potato | 0–24 | 25–44 | আলু ধরছে 45–79 | — | 80–100 |
| mustard | 0–20 | 21–34 | ফুল 35–59 | শুঁটি 60–79 | 80–90 |
| lentil | 0–29 | 30–49 | ফুল 50–69 | শুঁটি 70–99 | 100–120 |

Coverage: **S** symptom described in the repo; **W** organism + window + treatment in KB
but symptom not described ("হতে পারে"); **P** organism named in a survey only, no treatment.

| Crop | Days | Organ → symptom | Candidate | Source | Cov |
|---|---|---|---|---|---|
| aman | 18–59 | stem → dead heart | yellow stem borer | pest_risk `yellow_stem_borer`; `aman_pest_ysb` | S |
| aman | 18–74 | leaf → insects/eggs | YSB egg masses | season_plan aman +25 | S |
| aman | 60–120 | panicle → white/empty head | YSB white head | `aman_pest_ysb` | S |
| aman | 30–89 | leaf → spots | blast | pest_risk `blast`; `aman_disease_blast` | W |
| aman | 40–120 | sheath → sheath spots | sheath blight (no dose; AWD only) | pest_risk `sheath_blight`; `aman_disease_sheathblight` | W |
| aman | any | whole → burnt look | BPH hopperburn (boro passage only) | `boro_pest_bph` | P |
| boro | 20–54 | stem → dead heart | stem borer | pest_risk `stem_borer`; `boro_pest_stemborer`; `aman_pest_ysb` | S |
| boro | 55–125 | panicle → white/empty head | stem borer white head | `aman_pest_ysb` | S |
| boro | 55–125 | panicle → white/empty head + fog | cold injury (keep 5–7 cm water) | `boro_critical_temp`; `boro_irrigation_awd` | W |
| boro | ≥45 | whole → burnt/wilting; stem → insects | brown planthopper (no chemical dose) | pest_risk `bph`; `boro_pest_bph` | S |
| boro | any | leaf/whole → yellow | sulphur deficiency (+8 kg gypsum/bigha) | `boro_nutrient_topdress` | S |
| boro | any | whole → stunted | zinc deficiency (+1.5 kg ZnSO4/bigha); BPH-borne virus | `boro_nutrient_topdress`; `boro_pest_bph` | S/W |
| potato | 30–75 | leaf → spots / burnt | late blight (no dose); early blight | pest_risk `late_blight`; `potato_disease_blight`; `potato_disease_biocontrol` | S/W |
| potato | 25–70 | leaf → insects | aphid (no dose); leaf miner, leafhopper | pest_risk `aphid`; `potato_pest_aphid`; `potato_pest_survey` | W/P |
| potato | any | stem → cut | cutworm | `potato_pest_survey` | P |
| potato | any | tuber → holes/insects | tuber moth, mole cricket | `potato_pest_survey` | P |
| potato | any | whole → stunted | aphid-borne virus (PVY), no cure in KB | `potato_pest_aphid` | W |
| mustard | 35–75 | leaf → spots | alternaria (no number) | pest_risk `alternaria`; `mustard_disease_alternaria` | S |
| mustard | 45–85 | pod/leaf → insects | aphid: Malathion 57EC 2 ml/L | pest_risk `aphid`; `mustard_pest_aphid` | S |
| lentil | 40–80 | leaf → spots / burnt | stemphylium/blight; rust | pest_risk `stemphylium`; `lentil_disease_stemphylium`; `lentil_disease_rust_blight` | W |
| lentil | 55–95 | pod → holes / insects | pod borer | pest_risk `pod_borer`; `lentil_pest_podborer` | S |
| lentil | ≥50 | pod/leaf → insects | aphid (no dose) | season_plan lentil +50 | W |
| lentil | any | root → rot; whole → wilting | root rot (BARI Masur-8 next season) | `lentil_disease_stemphylium` | W |

Gaps in our sources: no yellowing/deficiency passage for aman, potato, mustard, lentil;
**no pre-harvest interval, no protective-gear guidance, no economic thresholds** anywhere;
carbofuran (`aman_pest_ysb`) is highly hazardous — check current DAE registration before
any SMS quotes it.

SMS safety: dose only as the KB passage states it, area math via `units.py`; several W/P
candidates or extent "প্রায় সব" → no dose, referral; one treatment per SMS; no PHI
number ever; fixed template lines (not model prose) for gear + "স্প্রের আগে SAAO-কে
দেখান" + 16123.
