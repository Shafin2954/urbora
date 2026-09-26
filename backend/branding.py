"""Product name, in one place.

The product is being renamed for GP FutureMakers 2026 (LOG4). Until the team
locks a name, every farmer-facing string reads it from here so the rename is a
one-line change (or an env override, no code change at all).

`BRAND_NAME` / `BRAND_NAME_BN` in the environment win over the defaults. The
frontend has its own copy in `frontend/src/branding.js` (VITE_BRAND_NAME),
because the browser cannot import Python.
"""

from __future__ import annotations

import os

BRAND_NAME: str = os.environ.get("BRAND_NAME", "AgriSense")
BRAND_NAME_BN: str = os.environ.get("BRAND_NAME_BN", BRAND_NAME)
