"""Load environment files once, in one order, for every entry point.

Precedence (first wins; python-dotenv never overrides a variable already set):
1. real environment variables
2. `<repo>/.env.local`   — each developer's own keys (gitignored)
3. `<repo>/backend/.env` — the July agent config location
4. `<repo>/.env`         — shared non-secret defaults

Imported by backend/agent/config.py and backend/api/config.py, so the agent,
the API and one-off scripts all see the same values.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
_loaded = False


def load() -> None:
    global _loaded
    if _loaded:
        return
    for path in (REPO_ROOT / ".env.local", REPO_ROOT / "backend" / ".env", REPO_ROOT / ".env"):
        if path.is_file():
            load_dotenv(path, override=False)
    _loaded = True
