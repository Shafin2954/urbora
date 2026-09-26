"""Phone number -> stable farm/session ids, without the number in the id.

A farmer who calls, texts and dials USSD from the same SIM is one farmer: the
farm profile, saved plan and alerts all hang off one `farm_id`. That id is a
keyed hash of the number (HMAC-SHA256 with `CHANNEL_ID_SALT`), so ids can sit in
logs, traces and URLs without exposing who the farmer is (CLAUDE.md rule 15).

The number itself is still needed to send an SMS back; it lives only in the
`contacts` table (backend/memory/store.py), never in an id, trace or log line.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import warnings
from datetime import datetime, timezone

from backend.payments.msisdn import InvalidMsisdnError, mask, normalise

__all__ = [
    "InvalidMsisdnError",
    "farm_id_for",
    "mask",
    "normalise",
    "phone_hash",
    "session_id_for",
]

_DEV_SALT = "agrisense-dev-salt-change-me"
_warned = False


def _salt() -> bytes:
    global _warned
    salt = os.environ.get("CHANNEL_ID_SALT", "")
    if not salt:
        if not _warned:
            warnings.warn(
                "CHANNEL_ID_SALT is not set; using the development salt. "
                "Set it in .env before any real farmer's number is stored.",
                stacklevel=3,
            )
            _warned = True
        salt = _DEV_SALT
    return salt.encode("utf-8")


def phone_hash(raw_msisdn: str) -> str:
    """24 hex chars of HMAC-SHA256 over the normalised local number.

    Normalising first means `+8801812345678` and `01812-345678` are the same
    farmer. Raises InvalidMsisdnError for anything that is not a BD mobile.
    """
    local = normalise(raw_msisdn)
    return hmac.new(_salt(), local.encode("ascii"), hashlib.sha256).hexdigest()[:24]


def farm_id_for(raw_msisdn: str) -> str:
    """The farm id every channel uses for this phone."""
    return f"ph-{phone_hash(raw_msisdn)}"


def session_id_for(raw_msisdn: str, channel: str, *, stamp: str | None = None) -> str:
    """Conversation id for one channel conversation.

    SMS and USSD questions share one rolling conversation per phone per day
    (a farmer's SMS thread is one conversation, and a day bounds the history
    the model has to re-read). A voice call is its own conversation: pass the
    call's own `stamp`. Farm memory crosses all of them via `farm_id_for`.
    """
    day = stamp or datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{channel}-{phone_hash(raw_msisdn)}-{day}"
