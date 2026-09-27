"""Product name, in one place.

The product is Agrosfera (renamed from the hackathon's working name AgriSense
for GP FutureMakers 2026, LOG4). Every farmer-facing string reads it from here,
so a future rename is a one-line change or an env override.

`BRAND_NAME` / `BRAND_NAME_BN` in the environment win over the defaults. The
frontend has its own copy in `frontend/src/branding.js` (VITE_BRAND_NAME),
because the browser cannot import Python.
"""

from __future__ import annotations

import os

BRAND_NAME: str = os.environ.get("BRAND_NAME", "Agrosfera")
BRAND_NAME_BN: str = os.environ.get("BRAND_NAME_BN", "অ্যাগ্রোস্ফেরা")
