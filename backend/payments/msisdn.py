"""Bangladeshi mobile number normalisation for bdapps.

BDAPPS-API-REFERENCE.md gotcha #4: the address format is strict — `tel:88`
followed by an 11-digit `01[3-9]xxxxxxxx`. Getting it wrong returns `E1325`
(bad address format), which at a demo looks exactly like "the payment is
broken" rather than "the phone number had a space in it".

Farmers type numbers every way there is: `01812-345678`, `+8801812345678`,
`8801812345678`, with spaces. All of those are the same person, so all of them
normalise here rather than at each call site.
"""

import re

# Operator prefixes in use in Bangladesh: 013 GP, 014 Banglalink, 015 Teletalk,
# 016 Airtel, 017 GP, 018 Robi, 019 Banglalink. bdapps is Robi, but a farmer
# may well type any of them, and rejecting a valid number is worse than letting
# bdapps decline it with its own error.
_LOCAL_RE = re.compile(r"^01[3-9]\d{8}$")


class InvalidMsisdnError(ValueError):
    """Raised for a number that cannot be a Bangladeshi mobile.

    Loud on purpose: silently "fixing" a number could charge a stranger.
    """


def normalise(raw: str) -> str:
    """Return the bare 11-digit local form, e.g. '01812345678'.

    Accepts +880…, 880…, 0…, and any punctuation or spacing around them.
    """
    if not isinstance(raw, str):
        raise InvalidMsisdnError(f"Mobile number must be a string, got {type(raw).__name__}")

    digits = re.sub(r"\D", "", raw)

    # Strip the country code in whichever form it arrived.
    if digits.startswith("880"):
        digits = digits[3:]
    elif digits.startswith("88") and len(digits) == 13:
        digits = digits[2:]

    # '1812345678' — the leading zero is commonly dropped after +880.
    if len(digits) == 10 and digits.startswith("1"):
        digits = "0" + digits

    if not _LOCAL_RE.match(digits):
        raise InvalidMsisdnError(
            f"Not a valid Bangladeshi mobile number: {raw!r} "
            "(expected 11 digits starting 013–019)"
        )
    return digits


def to_subscriber_id(raw: str) -> str:
    """Return the bdapps address form: 'tel:8801812345678'."""
    return f"tel:88{normalise(raw)}"


def mask(raw: str) -> str:
    """Last 3 digits only — the display/log form (NOTES.md #19).

    Note this is for OUR display of a number we already hold. Numbers coming
    *back* from bdapps are separately masked by them (gotcha #5) and must be
    stored and reused as-is, never reconstructed.
    """
    try:
        return f"***{normalise(raw)[-3:]}"
    except InvalidMsisdnError:
        return "***"
