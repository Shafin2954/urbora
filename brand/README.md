# Brand kit (v0.1 draft)

Start with `BRAND.md`. Open `guidelines/index.html` in a browser for the visual one-pager.

| File | What |
|---|---|
| `BRAND.md` | Purpose, audience, trust psychology, colour, type, shape, imagery |
| `VOICE.md` | How we speak; word list; sample lines; tagline options |
| `NAMES.md` | 10 checked name candidates + rejected names and why |
| `LOGO-BRIEF.md` | Logo concepts, colours, deliverables, prompt starter |
| `tokens/brand-tokens.json` | Source of truth for colours, fonts, shape |
| `tokens/brand-tokens.css` | Same as CSS variables (`--b-*`) |
| `assets/logo/` | Logo files once made |
| `assets/fonts/README.md` | Font sources (all free, SIL OFL) |
| `guidelines/index.html` | Visual brand guide |

The website maps these tokens in `frontend/src/index.css`. The product name in code comes
from `backend/branding.py` and `frontend/src/branding.js` (one-line rename).
