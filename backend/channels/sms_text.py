"""SMS length rules and the template-built plan summary.

Two facts drive this module:

1. **Bangla SMS is expensive in characters.** Any character outside the GSM-7
   alphabet switches the whole message to UCS-2, where one segment holds 70
   characters (67 per segment once a message is split), against 160 (153) for
   GSM-7. A Bangla SMS is therefore a few short lines, not a paragraph; this
   module counts segments exactly and trims to a budget.

2. **Numbers in an SMS come from tool data, never from model prose**
   (CLAUDE.md rule 1 and rule 15). `plan_summary_sms` builds the after-call /
   after-USSD summary from the `plan_update` and `finance_update` payloads the
   tools emitted. The model's words are not used for any figure.
"""

from __future__ import annotations

from datetime import date

# GSM 03.38 basic character set plus the extension table (extension chars
# cost two septets). Anything else forces UCS-2.
_GSM_BASIC = set(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
)
_GSM_EXT = set("^{}\\[~]|€")

GSM_SINGLE, GSM_MULTI = 160, 153
UCS2_SINGLE, UCS2_MULTI = 70, 67

# Canonical crop key -> Bangla name, for farmer-facing SMS text. Same five
# crops the scorer ranks (README "Crop coverage").
CROP_BN: dict[str, str] = {
    "boro_rice": "বোরো ধান",
    "aman_rice": "আমন ধান",
    "potato": "আলু",
    "mustard": "সরিষা",
    "lentil": "মসুর",
}


def encoding(text: str) -> str:
    """'gsm7' when every character fits the GSM alphabet, else 'ucs2'."""
    return "gsm7" if all(c in _GSM_BASIC or c in _GSM_EXT for c in text) else "ucs2"


def _units(text: str) -> int:
    """Length in the unit its encoding counts: septets, or UTF-16 code units."""
    if encoding(text) == "gsm7":
        return sum(2 if c in _GSM_EXT else 1 for c in text)
    return len(text.encode("utf-16-le")) // 2


def segments(text: str) -> int:
    """How many SMS segments `text` is billed as (0 for empty text)."""
    n = _units(text)
    if n == 0:
        return 0
    single, multi = (GSM_SINGLE, GSM_MULTI) if encoding(text) == "gsm7" else (UCS2_SINGLE, UCS2_MULTI)
    return 1 if n <= single else -(-n // multi)


def fit(text: str, max_parts: int = 3) -> str:
    """Trim `text` to at most `max_parts` segments, cutting at a line or word
    boundary and marking the cut with '…'. Unchanged if it already fits."""
    text = text.strip()
    if segments(text) <= max_parts:
        return text
    lines = text.split("\n")
    # Drop whole trailing lines first: a summary's later lines are its least
    # important, and a half-line reads worse than a missing one.
    while len(lines) > 1 and segments("\n".join(lines) + "…") > max_parts:
        lines.pop()
    out = "\n".join(lines)
    while out and segments(out + "…") > max_parts:
        cut = out.rfind(" ")
        out = out[:cut] if cut > 0 else out[:-1]
    return out.rstrip() + "…"


def _money(value: float) -> str:
    """৳ with thousands separators, Western digits, whole taka."""
    return f"৳{round(value):,}"


def _short_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day}/{d.month}"


SEASON_BN = {"rabi": "রবি", "kharif1": "খরিপ-১", "kharif2": "খরিপ-২"}


def ranking_summary_sms(brand: str, scorer: dict | None, season: str | None = None,
                        *, max_crops: int = 3, max_parts: int = 3) -> str | None:
    """The crop ranking as an SMS, built only from the crop_scorer result.

    A crop whose costs are incomplete (profit_basis comparable=false) gets the
    ceiling wording on the same line as its number, never a bare "লাভ"."""
    if not scorer or not scorer.get("candidates"):
        return None
    basis = (scorer.get("profit_basis") or {}).get("crops", {})
    ranked = [c for c in scorer["candidates"] if not c.get("excluded") and c.get("composite_score", 0) > 0]
    excluded = [c for c in scorer["candidates"] if c not in ranked]
    if not ranked:
        return None
    head = f"{brand}: " + (f"{SEASON_BN.get(season, season)} মৌসুমে " if season else "") + "ফসলের ক্রম"
    lines = [head]
    for i, c in enumerate(ranked[:max_crops], 1):
        name = CROP_BN.get(c["crop"], c["crop"])
        line = f"{i}. {name} — স্কোর {round(c['composite_score'])}"
        profit = c.get("est_profit_bdt")
        if profit:
            comparable = basis.get(c["crop"], {}).get("comparable", True)
            line += f", লাভ {_money(profit)}" if comparable else f", সর্বোচ্চ লাভ {_money(profit)} (সব খরচ নয়)"
        lines.append(line)
    if excluded:
        lines.append("বাদ: " + ", ".join(CROP_BN.get(c["crop"], c["crop"]) for c in excluded))
    return fit("\n".join(lines), max_parts=max_parts)


def plan_summary_sms(
    brand: str,
    plan: dict | None,
    finance: dict | None,
    crop: str | None = None,
    *,
    cost_complete: bool = True,
    today: date | None = None,
    max_tasks: int = 3,
    max_parts: int = 3,
) -> str | None:
    """The SMS a farmer gets after a call or a USSD request.

    Built only from tool payloads: `plan` is a SeasonPlan dict (plan_update),
    `finance` a FinanceProjection dict (finance_update). Returns None when
    there is nothing sourced to say — the caller then sends the agent's own
    short reply instead of an empty summary.

    `cost_complete=False` (mustard/lentil today: fertiliser-only costs, see
    crop_scorer._profit_basis) swaps the profit label for the ceiling wording,
    on the same line as the number.
    """
    if not plan and not finance:
        return None
    crop_key = (plan or {}).get("crop") or crop
    crop_bn = CROP_BN.get(crop_key or "", crop_key or "")
    lines = [f"{brand}: {crop_bn} পরিকল্পনা" if crop_bn else f"{brand}: পরিকল্পনা"]

    if plan and plan.get("tasks"):
        start = today or date.today()
        upcoming = [t for t in plan["tasks"] if date.fromisoformat(t["date"]) >= start]
        for task in (upcoming or plan["tasks"])[:max_tasks]:
            lines.append(f"{_short_date(task['date'])} {task['task']}")

    if finance:
        base = finance["scenarios"]["base"]
        profit_label = "লাভ" if cost_complete else "সর্বোচ্চ লাভ (সব খরচ ধরা হয়নি)"
        lines.append(f"খরচ {_money(base['total_cost'])}, আয় {_money(base['revenue'])}")
        lines.append(f"{profit_label} {_money(base['net_profit'])}")

    lines.append("বিস্তারিত: আবার কল বা SMS করুন")
    return fit("\n".join(lines), max_parts=max_parts)
