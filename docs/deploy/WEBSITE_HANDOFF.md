# Website session handoff

For a Claude Code session that redesigns and ships the web app. The video session works in
`video/` only; do not touch it.

## Paste this as the first message of the new session

> You are the lead product designer and front-end engineer for our FutureMakers 2026 entry
> (repo D:\Projects\TeamFixeth_AgriSense, branch futuremakers). Read CLAUDE.md,
> docs/deploy/WEBSITE_HANDOFF.md (all of it), brand/BRAND.md, brand/VOICE.md, docs/product/FIELD_INSIGHTS.md, then the
> latest LOG4.md entries and docs/MAP.md. The goal: make the whole site feel professional,
> calm and trustworthy, like a serious national service people feel close to (GP or bKash
> level of polish), using the brand kit in brand/. Start with a written plan of screens and
> changes and show me before large edits. Run `npm run dev` from the repo root and verify
> every change in the browser at 375px and desktop. Ask me for anything missing (final name,
> logo files, API keys: never paste keys in chat, they go in .env.local or Replit Secrets).

## Where things stand (2026-09-29)

- **Run.** `npm run dev` at the repo root starts the API on :8000 and Vite on :5000.
  `npm run app` builds and serves everything on :8000, the same way Replit deploys.
- **Brand tokens are applied.** `frontend/src/index.css` maps brand/tokens:
  - `--brand` = Shyamol green (primary)
  - `--sky` = Akash blue (phone and links)
  - `--gold` = Dhani gold (rare accent)
  - `--bg` = Poli ivory
  - fonts: Tiro Bangla for display, Hind Siliguri for text
- **Home page** (`src/pages/HomePage.jsx` + `home.css`) is redone and on-brand. It is the
  default route.
- **Not redesigned yet**, and still looking like the hackathon build in new colours:
  - the advisor at `#/app` (`App.jsx`, `App.css`, `ChatPanel`, `GraphPanel`, the finance and
    plan panels)
  - the phone emulator `#/phone` (`PhonePage.jsx`, `phone.css`)
  - the market `#/market`, `#/dealer` and `#/buyer` (`MarketPage.jsx`, `PartnerPages.jsx`,
    `market.css`)
  - the sign-in screen (`AuthScreen.jsx`)
- **Logo.** `components/BrandMark.jsx` and `public/icon*.svg` are placeholders until the team
  delivers files into `brand/assets/logo/` (brief: `brand/LOGO-BRIEF.md`).
- **Name.** Not final. Candidates are in `brand/NAMES.md`. Change it in
  `frontend/src/branding.js` and `backend/branding.py` only.

## Priorities (in order)

1. **Advisor `#/app`**, the screen judges use most.
   - Calm layout with one clear action.
   - Chat on the left, the provenance graph as a quiet side panel.
   - Finance and plan numbers in Tiro Bangla with the source visible.
   - Replace the "অতিথি হিসেবে দেখুন" floating button with a proper choice on the sign-in
     screen.
2. **Phone emulator `#/phone`.** This is where the video's product shots come from, so make it
   beautiful: a realistic phone frame, a clear "simulator" label, big keys.
3. **Market pages.** Tidy tables and cards; "ডেমো" labels stay visible (CLAUDE.md rule 16).
4. **Everywhere.**
   - Remove leftover English UI strings from farmer screens.
   - Check the Bangla copy against brand/VOICE.md.
   - No hotline (16123) mention anywhere in the UI copy.
5. **Deploy to Replit** (the team re-hosts from their own account).
   - `.replit` already builds `frontend` and serves it from uvicorn on :5000.
   - Secrets needed: OPENAI_API_KEY, SUPABASE and VITE_SUPABASE_* keys, and optionally the
     SARVAM key. Ask the user to set them; never commit them.

## Rules that still bind (CLAUDE.md)

- No gradients, glassmorphism or decorative shadows.
- Touch targets of at least 44px.
- Every number reaching the UI carries provenance.
- Demo and simulator content is labelled.
- `npm run build` must pass, and the test suite
  (`.venv/Scripts/python -m pytest backend/tests -q`) must stay green before merging to
  master.
- Log every unit of work in LOG4.md and update docs/MAP.md.

## Open product decision (ask the team)

The real crop-problem SMS ends with "কৃষি কল সেন্টার: 16123" (`HOTLINE_LINE` in
`backend/kb/triage.py`). The team does not want the hotline in the pitch. Removing it from
the SMS needs the team's yes (it is a safety referral); keep the SAAO line either way.
