# BDApps Pre-Flight Checklist

> Run through this **on the hackathon morning, on the actual network you'll use**, before writing any feature code.
> Goal: prove one real API call returns `"statusCode": "S1000"` so you know auth + IP whitelisting work.
> Companion to `BDAPPS-API-REFERENCE.md`.

---

## Two mental models (don't mix them up)

```
[Your laptop/server]  ──OUTBOUND──►  developer.bdapps.com
        ▲                             guard: ALLOWED HOST LIST  = your PUBLIC IP
        │
        └──INBOUND (USSD / MO SMS / sub-notify)── developer.bdapps.com
                                      guard: CALLBACK URL       = a PUBLIC https URL
```

- **Allowed Host List** = which machine may *call* BDApps → put your **public IP**. Skipping this = `E1312` on every call.
- **Callback URL** = where BDApps *sends data into you* → put a **public https URL** (tunnel or deploy). Only needed for USSD / receiving SMS / subscription notifications.

---

## A. One-time setup (do the night before)

- [ ] **Portal login works** — you can open your app in the BDApps developer portal.
- [ ] **Grab credentials** from the app page:
  - `applicationId` = `APP_000xxx`
  - `password` = 32-char key
- [ ] **Put them in a `.env`** (never hardcode / commit):
  ```
  BDAPPS_APP_ID=APP_000xxx
  BDAPPS_PASSWORD=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  ```
- [ ] **(If using ngrok) reserve a static domain** so your callback URL doesn't change all day.

---

## B. Morning-of, on the venue network (critical — do in order)

### 1. Get your PUBLIC IP (from the machine that runs the API calls)
```bash
curl ifconfig.me
# fallback:
curl https://api.ipify.org
```
- [ ] Copied the printed IP (e.g. `103.x.x.x`).
- ⚠️ **This changes** between home/venue/hotspot. Whatever you set last night is probably wrong now — re-check here.

### 2. Whitelist that IP in the portal
- [ ] Paste the IP into your app's **Allowed Host List** and save.
- [ ] Wait a minute or two for it to take effect (whitelisting isn't always instant).

### 3. Smoke-test one OUTBOUND call → expect `S1000`
Fill in creds and a real Robi/BDApps test number:
```bash
curl -sX POST https://developer.bdapps.com/subscription/getStatus \
  -H 'Content-Type: application/json' \
  -d '{"applicationId":"APP_000xxx","password":"<32-char>","subscriberId":"tel:8801812345678","version":"1.0"}'
```
- [ ] Response is JSON containing `"statusCode":"S1000"` (or a valid `subscriptionStatus`).
- ❌ Got `E1312`? → IP not whitelisted / wrong IP / not propagated yet → back to step 1.
- ❌ Got `E1313`? → wrong `applicationId` or `password` → recheck creds.
- ❌ Got HTML instead of JSON? → wrong URL or a proxy error → recheck the endpoint.

### 4. (Only if you need INBOUND: USSD, receiving SMS, sub-notify)
- [ ] Local server running: `node server.js` (listening on `:3000`).
- [ ] Tunnel up:
  ```bash
  ngrok http 3000                         # → https://xxx.ngrok-free.app
  # or
  cloudflared tunnel --url http://localhost:3000
  ```
- [ ] Registered the public URL(s) in the portal:
  - USSD URL → `https://xxx.ngrok-free.app/bdapps/ussd`
  - SMS URL → `https://xxx.ngrok-free.app/bdapps/sms`
  - Subscription notify → `https://xxx.ngrok-free.app/bdapps/subscription`
- [ ] Dial your USSD code / send a test SMS → your server logs the incoming JSON.
- ⚠️ Tunnel URL changes on restart (unless static domain) → re-register in portal if you restart it.

---

## C. Green light ✅

You're clear to build features once **all** of these are true:

- [ ] `curl ifconfig.me` IP == the IP saved in Allowed Host List.
- [ ] The step-3 curl returned `S1000`.
- [ ] `.env` loaded by your app (creds not hardcoded).
- [ ] (If inbound needed) tunnel URL registered and a test event reached your server.

---

## D. When something breaks mid-hackathon

| Symptom | Most likely cause | Fix |
|---|---|---|
| Everything suddenly fails with `E1312` | Your public IP changed (ISP lease / switched WiFi↔hotspot) | Re-run step 1 + 2 |
| `E1313` | Wrong / swapped `applicationId` / `password` | Recheck against portal |
| `E1325` | Bad number format | Must be `tel:88` + 11 digits (`01[3-9]xxxxxxxx`) |
| `E1850 / E1851 / E1852` | Invalid / expired OTP / too many attempts | Request a fresh OTP, new `referenceNo` |
| `E1318 / E1319` | Rate / daily limit hit | Throttle; `E1319` resets tomorrow |
| Response is HTML, not JSON | Wrong endpoint or upstream error page | Verify URL; your client should guard for non-JSON |
| USSD/SMS callbacks never arrive | Tunnel down, URL changed, or not registered | Restart tunnel, re-register URL in portal |
| Calls work at home, fail at venue | Venue network = different public IP | Re-whitelist the venue IP |

---

## E. 30-second summary to tell a teammate

1. `curl ifconfig.me` → paste into **Allowed Host List** in the portal.
2. Test: the `getStatus` curl must return **`S1000`**.
3. Only if you're doing **USSD or receiving SMS**: run a tunnel and paste its `https` URL as the app's **callback URL**.
4. If it worked last night but fails now → your **IP changed**, re-whitelist.

*Sources: `bdapps-API-DGD v1.1.3.pdf` (E-code table), portal behavior for host provisioning & callback URLs. See `BDAPPS-API-REFERENCE.md` for full endpoint details.*
