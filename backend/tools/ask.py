"""`ask_farmer` — the tool that puts an intake widget on screen.

PRD §8 Tier0.1 makes hybrid intake a *judged* behaviour: the agent detects a
gap, asks one targeted Bangla question, and that question "ships with an
`input_request` widget". The five widgets have existed in the UI since H2 and
the event has been in the frozen contract since H1 — but nothing ever emitted
one, so in the real flow they were unreachable. This tool is the missing half.

Why a tool rather than parsing the model's prose for a question: the widget
needs a field name, an input kind, and typed options. Asking the model to call
a function with those arguments makes them explicit and validatable. Inferring
them from Bangla free text would be a guess, in the one place PRD is explicit
that at most one question may be open at a time.

The tool renders nothing itself — it returns a validated `input_request` payload
which `agent/loop.py` turns into the SSE event. Keeping the shaping here means
an invalid widget is caught before it reaches the wire, and the model gets told
what it got wrong.
"""

from __future__ import annotations

from .districts import DISTRICTS

VALID_KINDS: tuple[str, ...] = ("chips", "dropdown", "number", "number_unit", "text")

# Local units the intake edge accepts (units.py converts; see LocalAreaUnit).
AREA_UNITS = ["bigha", "katha", "decimal", "acre", "hectare"]

# Bangla names for the 64 districts. Transliteration of a proper noun, not an
# agronomic claim — a farmer should not have to read Latin script to find their
# own district. Anything missing falls back to the English name rather than
# being guessed at in the moment.
DISTRICT_BN: dict[str, str] = {
    "Bagerhat": "বাগেরহাট", "Bandarban": "বান্দরবান", "Barguna": "বরগুনা",
    "Barishal": "বরিশাল", "Bhola": "ভোলা", "Bogura": "বগুড়া",
    "Brahmanbaria": "ব্রাহ্মণবাড়িয়া", "Chandpur": "চাঁদপুর",
    "Chapainawabganj": "চাঁপাইনবাবগঞ্জ", "Chattogram": "চট্টগ্রাম",
    "Chuadanga": "চুয়াডাঙ্গা", "Cox's Bazar": "কক্সবাজার", "Cumilla": "কুমিল্লা",
    "Dhaka": "ঢাকা", "Dinajpur": "দিনাজপুর", "Faridpur": "ফরিদপুর",
    "Feni": "ফেনী", "Gaibandha": "গাইবান্ধা", "Gazipur": "গাজীপুর",
    "Gopalganj": "গোপালগঞ্জ", "Habiganj": "হবিগঞ্জ", "Jamalpur": "জামালপুর",
    "Jashore": "যশোর", "Jhalokati": "ঝালকাঠি", "Jhenaidah": "ঝিনাইদহ",
    "Joypurhat": "জয়পুরহাট", "Khagrachhari": "খাগড়াছড়ি", "Khulna": "খুলনা",
    "Kishoreganj": "কিশোরগঞ্জ", "Kurigram": "কুড়িগ্রাম", "Kushtia": "কুষ্টিয়া",
    "Lakshmipur": "লক্ষ্মীপুর", "Lalmonirhat": "লালমনিরহাট", "Madaripur": "মাদারীপুর",
    "Magura": "মাগুরা", "Manikganj": "মানিকগঞ্জ", "Meherpur": "মেহেরপুর",
    "Moulvibazar": "মৌলভীবাজার", "Munshiganj": "মুন্সিগঞ্জ", "Mymensingh": "ময়মনসিংহ",
    "Naogaon": "নওগাঁ", "Narail": "নড়াইল", "Narayanganj": "নারায়ণগঞ্জ",
    "Narsingdi": "নরসিংদী", "Natore": "নাটোর", "Netrokona": "নেত্রকোণা",
    "Nilphamari": "নীলফামারী", "Noakhali": "নোয়াখালী", "Pabna": "পাবনা",
    "Panchagarh": "পঞ্চগড়", "Patuakhali": "পটুয়াখালী", "Pirojpur": "পিরোজপুর",
    "Rajbari": "রাজবাড়ী", "Rajshahi": "রাজশাহী", "Rangamati": "রাঙ্গামাটি",
    "Rangpur": "রংপুর", "Satkhira": "সাতক্ষীরা", "Shariatpur": "শরীয়তপুর",
    "Sherpur": "শেরপুর", "Sirajganj": "সিরাজগঞ্জ", "Sunamganj": "সুনামগঞ্জ",
    "Sylhet": "সিলেট", "Tangail": "টাঙ্গাইল", "Thakurgaon": "ঠাকুরগাঁও",
}


def district_options() -> list[dict[str, str]]:
    """All 64 districts, Bangla-labelled. The UI's dropdown filters as you type."""
    return [
        {"value": name, "label_bn": DISTRICT_BN.get(name, name)}
        for name in sorted(DISTRICTS)
    ]


def ask_farmer(
    field: str,
    prompt_bn: str,
    input_kind: str,
    options: list[dict] | None = None,
    unit_options: list[str] | None = None,
) -> dict:
    """Put one intake question on screen, with the right widget.

    Args:
        field: what is being collected — "district", "area", "soil_type",
            "water_source", "season", "budget_bdt", "land_type", "name".
        prompt_bn: the question, in Bangla, as the farmer will read it.
        input_kind: chips | dropdown | number | number_unit | text.
        options: [{value, label_bn}] for chips/dropdown. Omitted for
            field="district" — the 64 districts are filled in here.
        unit_options: for number_unit; defaults to the area units.
    """
    if input_kind not in VALID_KINDS:
        return {
            "error": f"invalid input_kind '{input_kind}'",
            "detail": f"Must be one of: {', '.join(VALID_KINDS)}.",
        }
    if not (prompt_bn or "").strip():
        return {
            "error": "prompt_bn is required",
            "detail": "The farmer has to be able to read the question.",
        }

    # The district list is ours, not the model's — 64 hand-typed options is a
    # place for a transcription error, and the canonical spellings have to match
    # what geocode and crop.db accept.
    if input_kind == "dropdown" and field == "district" and not options:
        options = district_options()

    if input_kind in ("chips", "dropdown"):
        cleaned = []
        for option in options or []:
            value = str(option.get("value", "")).strip()
            label = str(option.get("label_bn", "")).strip() or value
            if value:
                cleaned.append({"value": value, "label_bn": label})
        if not cleaned:
            return {
                "error": f"'{input_kind}' needs options",
                "detail": "Pass options as [{value, label_bn}] — label_bn in Bangla.",
            }
        options = cleaned
    else:
        options = None

    if input_kind == "number_unit":
        unit_options = [str(u) for u in (unit_options or AREA_UNITS)]
    else:
        unit_options = None

    return {
        "input_request": {
            "type": "input_request",
            "field": field,
            "prompt_bn": prompt_bn,
            "input_kind": input_kind,
            "options": options,
            "unit_options": unit_options,
        },
        # The model must stop after asking. Without this it tends to answer its
        # own question and carry on, which defeats the entire point of asking.
        "note": (
            "The question is now on the farmer's screen with a widget. End your "
            "turn here — say nothing further and do not assume an answer. The "
            "farmer's reply arrives as the next user message."
        ),
    }
