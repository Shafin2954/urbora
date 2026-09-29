"""Product name, in one place.

The product is উর্বরা / Urbora (renamed from the hackathon's AgriSense, then
Agrosfeer; final name 2026-09-30, LOG4 and brand/BRAND-CORE.md). Every farmer-facing string reads it from here,
so a future rename is a one-line change or an env override.

`BRAND_NAME` / `BRAND_NAME_BN` in the environment win over the defaults. The
frontend has its own copy in `frontend/src/branding.js` (VITE_BRAND_NAME),
because the browser cannot import Python.
"""

from __future__ import annotations

import os

BRAND_NAME: str = os.environ.get("BRAND_NAME", "Urbora")
BRAND_NAME_BN: str = os.environ.get("BRAND_NAME_BN", "উর্বরা")
BRAND_TAGLINE_BN: str = "স্বপ্ন ফলুক"
