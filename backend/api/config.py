"""API configuration, read from the environment (.env at repo root).

Env names are documented in .env.example. Nothing here has a secret default.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# repo root = backend/api/config.py -> api -> backend -> root
REPO_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(REPO_ROOT / ".env")


def _csv(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))

# Dev normally needs no CORS at all: the Vite dev server proxies /api to this
# process, so the browser sees a single origin. These origins only matter when
# something hits the API port directly (curl, a phone on the LAN, a judge
# poking at :8000). Keeping both is deliberate belt-and-braces — NOTES.md #13
# lists SSE+CORS friction as an hour-eater, so it dies at H0, not at H14.
CORS_ORIGINS = _csv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)

# Seconds between heartbeat comments on an idle SSE stream. Keeps proxies and
# phone radios from closing a quiet connection mid-plan.
SSE_HEARTBEAT_SECONDS = float(os.getenv("SSE_HEARTBEAT_SECONDS", "15"))
