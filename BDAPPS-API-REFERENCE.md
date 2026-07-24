# BDApps API — Working Reference (for Claude Code)

> Robi/BDApps HTTP API for **OTP, Subscription, SMS, USSD, and CAAS (charging)** in Bangladesh.
> Source: `bdapps-API-DGD v1.1.3.pdf` (2019) + the working PHP in `All Backend code/` + confirmed live base URL.
> This file is the single source of truth for the hackathon. Endpoint-first, copy-pasteable.

---

## 0. TL;DR — read this first

- **Base URL (all API calls):** `https://developer.bdapps.com`
  (Docs portal is `dev.bdapps.com`; the *API* host is `developer.bdapps.com`.)
- **Every call is:** `POST`, `Content-Type: application/json`, JSON body, JSON response.
- **Auth is per-request in the body:** `applicationId` + `password` (no headers, no OAuth).
  Get both from the BDApps developer portal → your app. **They are BLANK in every file in this repo — fill them in.**
- **Success = `"statusCode": "S1000"`.** Anything else is an error code (see §8).
- **`subscriberId` / address format is always `tel:88<11-digit-number>`**, e.g. `tel:8801812345678`.
  Normalize `01812345678` → strip/add so it becomes `tel:88` + `01812345678`.
- **Two big hackathon gotchas** (see §9): (1) your server's **IP must be whitelisted** in the app's portal config or every call fails with `E1312`; (2) inbound endpoints (SMS-receive, USSD, subscription-notify) must be **public URLs** registered in the portal.

### Credentials placeholder (fill once, reuse everywhere)
```
BDAPPS_APP_ID   = APP_000xxx        # "Application ID" from portal
BDAPPS_PASSWORD = <32-char hash>    # "Password" / API key from portal
```

---

## 1. Endpoint cheat sheet

| Service | Method + URL | Purpose | Direction |
|---|---|---|---|
| OTP request | `POST /subscription/otp/request` | Send OTP SMS to a number | You → BDApps |
| OTP verify | `POST /subscription/otp/verify` | Verify the code the user typed | You → BDApps |
| Subscribe / Unsubscribe | `POST /subscription/send` | `action:"1"` sub, `"0"` unsub | You → BDApps |
| Subscription status | `POST /subscription/getStatus` | REGISTERED / UNREGISTERED | You → BDApps |
| SMS send (MT) | `POST /sms/send` | Send SMS / broadcast | You → BDApps |
| USSD send (MT) | `POST /ussd/send` | Reply in a USSD session | You → BDApps |
| CAAS balance | `POST /caas/balance/query` | Query subscriber balance | You → BDApps |
| CAAS payment instruments | `POST /caas/list/pi` | List payment instruments | You → BDApps |
| CAAS direct debit | `POST /caas/direct/debit` | Charge the subscriber | You → BDApps |
| **SMS receive (MO)** | *your* URL | BDApps delivers inbound SMS to you | BDApps → You |
| **USSD receive (MO)** | *your* URL | BDApps delivers USSD session events | BDApps → You |
| **Delivery report** | *your* URL | SMS delivery status callback | BDApps → You |
| **Subscription notify** | *your* URL | sub/unsub confirmation callback | BDApps → You |

Inbound (BDApps → You) URLs are configured in the app portal, not called by you.

---

## 2. OTP — phone verification (most common hackathon use)

Flow: **request OTP → user gets SMS → user types code → verify**. Verify returns a **masked `subscriberId`** you use for all later calls.

### 2.1 Request OTP — `POST /subscription/otp/request`
```json
{
  "applicationId": "APP_000xxx",
  "password": "<32-char>",
  "subscriberId": "tel:8801812345678",
  "applicationHash": "App Name",
  "applicationMetaData": {
    "client": "MOBILEAPP",
    "device": "Samsung S10",
    "os": "android 8",
    "appCode": "https://play.google.com/store/apps/details?id=your.app"
  }
}
```
`applicationHash` = 11-char Google SMS-Retriever hash (optional; use app name if not using auto-fill). `client` is `MOBILEAPP` or `WEBAPP`.

**Response** — keep `referenceNo`, you need it to verify:
```json
{ "statusCode": "S1000", "statusDetail": "Success", "referenceNo": "213561321321613", "version": "1.0" }
```

### 2.2 Verify OTP — `POST /subscription/otp/verify`
```json
{
  "applicationId": "APP_000xxx",
  "password": "<32-char>",
  "referenceNo": "213561321321613",
  "otp": "123564"
}
```
**Response:**
```json
{
  "statusCode": "S1000",
  "statusDetail": "Success",
  "subscriptionStatus": "REGISTERED",
  "version": "1.0",
  "subscriberId": "tel:sdfasdf...masked...asf"
}
```
- OTP errors: `E1850` invalid OTP, `E1851` OTP expired, `E1852` max attempts reached.
- The returned `subscriberId` is **masked** — store it and use it for subsequent SMS/charging to that user.

---

## 3. Subscription

### 3.1 Subscribe / Unsubscribe — `POST /subscription/send`
```json
{
  "applicationId": "APP_000xxx",
  "password": "<32-char>",
  "subscriberId": "tel:8801812345678",
  "version": "1.0",
  "action": "1"
}
```
`action`: **`"1"` = subscribe, `"0"` = unsubscribe.** Response includes `statusCode` (`S1000`) and `subscriptionStatus`.

### 3.2 Get status — `POST /subscription/getStatus`
```json
{ "applicationId": "APP_000xxx", "password": "<32-char>", "subscriberId": "tel:8801812345678", "version": "1.0" }
```
**Response:**
```json
{ "subscriptionStatus": "REGISTERED", "statusCode": "S1000", "statusDetail": "...", "version": "1.0" }
```
`subscriptionStatus` is **`REGISTERED`** or **`UNREGISTERED`**. (Repo `check_subscription.php` treats `REGISTERED` as subscribed.)

### 3.3 Subscription notification (BDApps → your listener)
BDApps POSTs to your configured URL when sub/unsub is confirmed:
```json
{ "timeStamp": "...", "status": "REGISTERED", "applicationId": "APP_000xxx", "subscriberId": "tel:...masked...", "frequency": "..." }
```
Just log it and reply `{"statusCode":"S1000","statusDetail":"Success"}`. See `subscription_listener.php`.

---

## 4. SMS

### 4.1 Send / broadcast — `POST /sms/send`
```json
{
  "applicationId": "APP_000xxx",
  "password": "<32-char>",
  "message": "Sample Message",
  "destinationAddresses": ["tel:8801812345678"],
  "version": "1.0",
  "sourceAddress": "<shortcode_or_alias>",
  "deliveryStatusRequest": "0",
  "encoding": "0"
}
```
- `destinationAddresses` is an **array**. Use `["tel:all"]` to **broadcast to your whole subscriber base**.
- `encoding`: **`0`=Text, `16`=Bengali, `240`=Flash SMS, `245`=Binary**.
- `deliveryStatusRequest`: `0`=no report, `1`=want delivery report callback.
- `sourceAddress` optional; must be a provisioned alias or omit it. Sending a non-allowed one → `E1331`.
- `chargingAmount` (string, 2dp) only for variable-charge apps. `binaryHeader` (hex) required if encoding is Flash/Binary.

**Response:**
```json
{
  "statusCode": "S1000",
  "requestId": "101307311144070043",
  "statusDetail": "Request was successfully processed",
  "destinationResponses": [
    { "statusCode": "S1000", "timeStamp": "20130731114407", "address": "tel:8801812345677",
      "statusDetail": "...", "messageId": "101307311144070043" }
  ],
  "version": "1.0"
}
```

### 4.2 Receive SMS (MO) — BDApps → your URL
Body BDApps sends you:
```json
{ "message":"Test Message", "requestId":"...", "applicationId":"APP_000xxx",
  "sourceAddress":"tel:8801832160987", "version":"1.0", "encoding":"16" }
```
Reply `{"statusCode":"S1000","statusDetail":"Success"}`. See `sms.php` + `SMSReceiver` in `sdk_file.php`.

### 4.3 Delivery report (MO) — BDApps → your URL
```json
{ "destinationAddress":"tel:8801832160987", "timeStamp":"20120113082110", "requestId":"...", "deliveryStatus":"DELIVERED" }
```
`deliveryStatus` ∈ DELIVERED, EXPIRED, DELETED, UNDELIVERABLE, ACCEPTED, UNKNOWN, REJECTED. Reply `S1000`.

---

## 5. USSD

USSD is session-based. BDApps sends you a **receive** event (`mo-init` when the user dials, `mo-cont` on each reply); you answer with **send** (`mt-cont` to keep the menu open, `mt-fin` to end).

### 5.1 Send / reply — `POST /ussd/send`
```json
{
  "applicationId": "APP_000xxx",
  "password": "<32-char>",
  "message": "1. Option one\n2. Option two\n3. Exit",
  "sessionId": "1330929317043",
  "ussdOperation": "mt-cont",
  "destinationAddress": "tel:8801812345678",
  "version": "1.0",
  "encoding": "440"
}
```
- `ussdOperation`: `mt-cont` = show menu & keep session open; `mt-fin` = final message, ends session.
- `encoding`: **`440`=Plain ASCII, `16`=Bengali** (note: different set from SMS).
- Keep the **same `sessionId`** for the whole session.

### 5.2 Receive (MO) — BDApps → your URL
```json
{ "message":"010", "ussdOperation":"mo-init", "requestId":"...", "sessionId":"1209992331266121",
  "encoding":"16", "applicationId":"APP_000xxx", "sourceAddress":"tel:8801812345678", "version":"1.0" }
```
`ussdOperation` incoming: `mo-init` (session start / dial), `mo-cont` (subsequent inputs). See `ussd.php` for a full subscribe-on-dial flow.

---

## 6. CAAS — charging as a service

### 6.1 Query balance — `POST /caas/balance/query`
```json
{ "applicationId":"APP_000xxx", "password":"<32-char>", "subscriberId":"tel:8801812345678",
  "paymentInstrumentName":"Mobile Account", "currency":"BDT" }
```
→ `{ "statusCode":"S1000", "chargeableBalance":"100", "accountStatus":"0", "accountType":"PREPAID", "statusDetail":"..." }`

### 6.2 Payment instruments — `POST /caas/list/pi`
```json
{ "applicationId":"APP_000xxx", "password":"<32-char>", "subscriberId":"tel:8801812345678", "type":"all" }
```
→ `{ "statusCode":"S1000", "paymentInstrumentList":[{"name":"Mobile Account","type":"sync"}], "statusDetail":"Success" }`
`type` ∈ `sync` | `async` | `all` (default all).

### 6.3 Direct debit (charge) — `POST /caas/direct/debit`
```json
{ "externalTrxId":"25609", "amount":"5", "applicationId":"APP_000xxx", "password":"<32-char>",
  "subscriberId":"tel:8801812345678", "paymentInstrumentName":"Mobile Account", "currency":"BDT" }
```
- `externalTrxId` = **your** unique id per charge (dedupe/mapping). `amount` string, 2dp, BDT only.
→ `{ "statusCode":"S1000", "timeStamp":"2013-08-01T08:43:34.344+05:30", "externalTrxId":"25609", "internalTrxId":"913080108430074", "statusDetail":"..." }`
- Charge failures: `E1601` permanent charging error (e.g. insufficient balance), `E1602` insufficient balance (retry-able), `E1328` charging op not allowed.

---

## 7. Node.js quickstart (this is the stack for tomorrow)

### 7.1 Minimal client — `bdapps.js`
```js
// Node 18+ (global fetch). No deps.
const BASE = "https://developer.bdapps.com";
const APP_ID = process.env.BDAPPS_APP_ID;      // "APP_000xxx"
const PASSWORD = process.env.BDAPPS_PASSWORD;  // 32-char key

async function call(path, body) {
  const res = await fetch(BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ applicationId: APP_ID, password: PASSWORD, ...body }),
  });
  const text = await res.text();
  let data; try { data = JSON.parse(text); } catch { throw new Error("Non-JSON from BDApps: " + text.slice(0, 300)); }
  return data;
}

// tel:88 + 11-digit local number. Accepts 018..., 88018..., +88018...
function toSubscriberId(raw) {
  let d = String(raw).replace(/\D+/g, "");
  if (d.length === 13 && d.startsWith("880")) d = "0" + d.slice(3);
  else if (d.length === 12 && d.startsWith("88")) d = "0" + d.slice(2);
  if (!/^01[3-9]\d{8}$/.test(d)) throw new Error("Invalid BD mobile: " + raw);
  return "tel:88" + d;
}

export const bdapps = {
  requestOtp: (mobile) => call("/subscription/otp/request", {
    subscriberId: toSubscriberId(mobile),
    applicationHash: "App Name",
    applicationMetaData: { client: "WEBAPP", device: "web", os: "web", appCode: "web" },
  }),
  verifyOtp: (referenceNo, otp) => call("/subscription/otp/verify", { referenceNo, otp }),
  subscribe:   (mobile) => call("/subscription/send", { subscriberId: toSubscriberId(mobile), version: "1.0", action: "1" }),
  unsubscribe: (mobile) => call("/subscription/send", { subscriberId: toSubscriberId(mobile), version: "1.0", action: "0" }),
  getStatus:   (mobile) => call("/subscription/getStatus", { subscriberId: toSubscriberId(mobile), version: "1.0" }),
  sendSms: (mobile, message) => call("/sms/send", {
    destinationAddresses: [toSubscriberId(mobile)], message, version: "1.0", encoding: "0",
  }),
  broadcast: (message) => call("/sms/send", { destinationAddresses: ["tel:all"], message, version: "1.0", encoding: "0" }),
  balance: (mobile) => call("/caas/balance/query", { subscriberId: toSubscriberId(mobile), paymentInstrumentName: "Mobile Account", currency: "BDT" }),
  charge: (mobile, amount, externalTrxId) => call("/caas/direct/debit", {
    subscriberId: toSubscriberId(mobile), amount: String(amount), externalTrxId,
    paymentInstrumentName: "Mobile Account", currency: "BDT",
  }),
};
export const isSuccess = (r) => r && r.statusCode === "S1000";
export { toSubscriberId };
```

### 7.2 Express backend + inbound listeners
```js
import express from "express";
import { bdapps, isSuccess } from "./bdapps.js";
const app = express();
app.use(express.json());

// --- OTP flow (frontend calls these) ---
app.post("/api/otp/request", async (req, res) => {
  try {
    const r = await bdapps.requestOtp(req.body.mobile);
    if (!isSuccess(r)) return res.status(400).json({ ok: false, detail: r.statusDetail, code: r.statusCode });
    res.json({ ok: true, referenceNo: r.referenceNo }); // keep referenceNo client-side for verify
  } catch (e) { res.status(500).json({ ok: false, error: e.message }); }
});

app.post("/api/otp/verify", async (req, res) => {
  const { referenceNo, otp } = req.body;
  const r = await bdapps.verifyOtp(referenceNo, otp);
  res.json({ ok: isSuccess(r), status: r.subscriptionStatus, subscriberId: r.subscriberId, detail: r.statusDetail });
});

// --- Inbound (register these URLs in the BDApps portal) ---
app.post("/bdapps/sms", (req, res) => { console.log("MO SMS", req.body); res.json({ statusCode: "S1000", statusDetail: "Success" }); });
app.post("/bdapps/ussd", async (req, res) => {
  const { sessionId, sourceAddress, ussdOperation, message } = req.body;
  // TODO: build your menu; reply via /ussd/send with mt-cont (keep open) or mt-fin (end).
  res.json({ statusCode: "S1000", statusDetail: "Success" });
});
app.post("/bdapps/subscription", (req, res) => { console.log("SUB NOTIFY", req.body); res.json({ statusCode: "S1000", statusDetail: "Success" }); });

app.listen(3000, () => console.log("bdapps backend on :3000"));
```

### 7.3 curl (language-agnostic smoke tests)
```bash
# Request OTP
curl -sX POST https://developer.bdapps.com/subscription/otp/request \
  -H 'Content-Type: application/json' \
  -d '{"applicationId":"APP_000xxx","password":"<32-char>","subscriberId":"tel:8801812345678","applicationHash":"App Name","applicationMetaData":{"client":"WEBAPP","device":"web","os":"web","appCode":"web"}}'

# Verify OTP
curl -sX POST https://developer.bdapps.com/subscription/otp/verify \
  -H 'Content-Type: application/json' \
  -d '{"applicationId":"APP_000xxx","password":"<32-char>","referenceNo":"2135613...","otp":"123456"}'

# Subscription status
curl -sX POST https://developer.bdapps.com/subscription/getStatus \
  -H 'Content-Type: application/json' \
  -d '{"applicationId":"APP_000xxx","password":"<32-char>","subscriberId":"tel:8801812345678","version":"1.0"}'
```

### 7.4 Frontend OTP snippet
```js
// Step 1: request
const { referenceNo } = await (await fetch("/api/otp/request", {
  method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ mobile: "01812345678" }),
})).json();

// Step 2: user types code → verify
const result = await (await fetch("/api/otp/verify", {
  method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ referenceNo, otp: userTypedCode }),
})).json();
// result.ok === true, result.subscriberId is the masked id to store
```

---

## 8. Status & error codes (Appendix A)

**Success:** `S1000` — completed successfully.

| Code | Meaning | Retry? |
|---|---|---|
| `E1313` | **Auth failed** — bad/inactive `applicationId` or wrong `password` | no |
| `E1312` | **Your IP is not provisioned** to call this app (whitelist it) | no |
| `E1303` | Request invalid — missing/bad mandatory field | no |
| `E1309` | SMS service not allowed for this app | no |
| `E1311` | MT SMS not enabled — check NCS config in provisioning | no |
| `E1315` | Requested SMS service not found / not active | no |
| `E1317` | `<MSISDN>` invalid or not allowed | no |
| `E1325` | **Bad address format** — expected `tel:8801812345678` | no |
| `E1331` | `sourceAddress` not allowed — use a provisioned alias or omit | no |
| `E1334` | Request failed for all destinations | no |
| `E1335` | SMS too long | no |
| `E1341` | Duplicate request | no |
| `E1342` | MSISDN blacklisted | no |
| `E1343` | MSISDN not whitelisted (only whitelist allowed in this state) | no |
| `E1601` | Permanent charging error (e.g. insufficient balance) | no |
| `E1318` | Per-second transaction limit exceeded — throttle | **yes** |
| `E1319` | Daily transaction limit exceeded | yes (tomorrow) |
| `E1326` | Insufficient balance | **yes** |
| `E1602` | Message delivery failed — retry | **yes** |
| `E1603` | Temporary system error | **yes** |
| `E1850` | **Invalid OTP** | — |
| `E1851` | **OTP request expired** | — |
| `E1852` | **Max OTP attempts reached** | — |

Always branch on `statusCode === "S1000"`; surface `statusDetail` to the user/logs otherwise.

---

## 9. Gotchas that cost hackathon hours

1. **IP whitelisting (`E1312`).** BDApps only accepts API calls from IPs provisioned for your app in the portal. Add your server's public IP *before* the event. Localhost won't work for outbound unless your egress IP is whitelisted.
2. **Inbound URLs must be public.** SMS-receive, USSD, delivery-report, subscription-notify are **called by BDApps into your server** — register HTTPS URLs in the portal and use a tunnel (ngrok/cloudflared) if running locally.
3. **Credentials are blank in this repo.** Every PHP file has `applicationId=""` / `password=""`. Fill from portal. Don't commit real keys.
4. **Number format is strict.** Must be `tel:88` + 11-digit (`01[3-9]xxxxxxxx`). Use `toSubscriberId()`.
5. **Numbers come back masked.** For privacy-type apps, `subscriberId` in responses/callbacks is a masked token (e.g. base64…:robi), not the real MSISDN. Store and reuse the masked value; never assume you can reconstruct the phone number.
6. **USSD vs SMS encodings differ.** USSD ASCII = `440`; SMS text = `0`; Bengali = `16` in both.
7. **`action` is a string** (`"1"`/`"0"`), and most numeric-looking fields (amount, encoding, version) are **strings** in the JSON.
8. **CORS on your own PHP/Node.** The repo PHP already sets `Access-Control-Allow-Origin: *` and handles `OPTIONS` — keep that if a browser frontend calls your backend directly.
9. **Non-JSON responses happen.** On errors BDApps (or a proxy) may return HTML. The repo code checks for `<html`/`<!DOCTYPE`; the Node client throws on non-JSON — keep that guard.

---

## 10. Map of the existing repo code

Path: `All Backend code/All Backend code/` (ignore the `__MACOSX` folder — junk metadata).

| File | What it does | Reuse for |
|---|---|---|
| `sdk_file.php` | Core SDK: `Core`, `SMSSender/SMSReceiver`, `UssdSender/UssdReceiver`, `Subscription`, `DirectDebitSender`, `WebApi`, exceptions, `Logger` | Reference for exact JSON each class builds |
| `send_otp.php` | `POST /subscription/otp/request` wrapper (returns `referenceNo`) | OTP step 1 |
| `verify_otp.php` | `POST /subscription/otp/verify` wrapper | OTP step 2 |
| `check_subscription.php` | `POST /subscription/getStatus`, maps `REGISTERED`→subscribed | status check |
| `unsubscribe.php` | `POST /subscription/send` with `action:"0"` | unsubscribe |
| `sms.php` | Receives MO SMS + broadcasts via `SMSSender` | SMS in/out |
| `ussd.php` | Full USSD session: on dial, check status, subscribe, reply menu | USSD flow |
| `subscription_listener.php` | Logs subscription-notify callbacks | inbound callback |

> Note: `sdk_file.php`'s `WebApi` class uses a hardcoded `serviceProviderAppId` (`DSAPP_000003`) and a SHA-256 `requestSignature` for `/subscription/activate` — that's a signed-activation variant specific to one prior app; **not needed** for the standard OTP/subscription flow above. Ignore unless you specifically need signed activation.

---

## 11. Sources
- `bdapps-API-DGD v1.1.3.pdf` (this repo, 51 pp, 2019) — canonical field tables & codes.
- Working PHP in `All Backend code/` — real request shapes actually used against `developer.bdapps.com`.
- [BDApps developer portal & docs](https://dev.bdapps.com/) · [BDApps TAP API doc](https://dev.bdapps.com/API_Documentation/bdapps_tap_api.html) — confirms base host & service list.
