"""Local unit conversion — the ONLY place local units exist.

CLAUDE.md §2.11: everything internal is hectares and kg. Local units live at
the intake edge (a farmer says "২ বিঘা") and the display edge (we show the
answer back in bigha), never in between. If a bigha appears in the finance
engine or in crop.db, that is a bug.

------------------------------------------------------------------------------
CONVENTION, AND A DISCREPANCY THAT HAD TO BE RESOLVED
------------------------------------------------------------------------------
CLAUDE.md §2.11 and NOTES.md #9 both state: "1 bigha = 33 decimal = 0.1338 ha".
Those two halves are not equal, and the difference is real:

    33 decimal  = 0.33 acre       = 0.1335463 ha
    0.1338 ha   = 14,400 sq ft    = 20 katha × 720 sq ft

i.e. a bigha is really 33.06 decimal, not 33. The gap is 0.18%.

RESOLUTION (B, H1): anchor bigha and katha on the **sq-ft definition**, and
decimal and acre on the **exact international acre**.

  - bigha = 20 katha = 14,400 sq ft = 0.1337803776 ha, which rounds to the
    0.1338 both documents explicitly ratify, and keeps bigha↔katha exact
    (a farmer converting bigha to katha must never see a rounding artefact).
  - acre stays exactly 4046.8564224 m², because it is an internationally
    fixed unit and quietly redefining it to make a folk equality hold would
    corrupt every acre-denominated figure we ever read from a source.

So "1 bigha = 33 decimal" is treated as the approximation it actually is
(33.06), while "0.1338 ha" is treated as the definition. Stated in the README
per NOTES.md #9. Changing this is a one-line edit to BIGHA_HA — but it moves
every cost and revenue number, so it is a team decision, not a tidy-up.
"""

from typing import Iterable

# --- exact primitives -------------------------------------------------------

SQ_FT_M2 = 0.09290304  # exact by definition of the international foot
ACRE_M2 = 4046.8564224  # exact: 43,560 sq ft
M2_PER_HA = 10_000.0

# --- area, in hectares ------------------------------------------------------

KATHA_HA = (720 * SQ_FT_M2) / M2_PER_HA  # 0.00668901888
BIGHA_HA = 20 * KATHA_HA  # 0.1337803776 -> the ratified 0.1338
ACRE_HA = ACRE_M2 / M2_PER_HA  # 0.40468564224
DECIMAL_HA = ACRE_HA / 100  # 1 decimal = 1/100 acre, exactly

AREA_IN_HA: dict[str, float] = {
    "ha": 1.0,
    "bigha": BIGHA_HA,
    "katha": KATHA_HA,
    "decimal": DECIMAL_HA,
    "acre": ACRE_HA,
    "sq_m": 1 / M2_PER_HA,
    "sq_ft": SQ_FT_M2 / M2_PER_HA,
}

# --- mass, in kg ------------------------------------------------------------

# The Bangladeshi market maund is 40 kg. The historical/imperial maund is
# 37.3242 kg (82.28 lb), and the two are 7% apart — which lands directly on
# every revenue figure, since prices are quoted per maund.
#
# 40 kg is chosen because that is what today's markets and the DAM daily price
# bulletins (PRD.md §10, the source prices.md is built from) actually mean by
# "মণ". Pricing a 40 kg maund with a 37.32 kg divisor would overstate revenue
# by 7% while looking perfectly reasonable on screen.
#
# FLAGGED FOR HUMAN RATIFICATION — see LOG2. If prices.md turns out to quote
# the historical maund, change MAUND_KG and the finance tests will follow.
MAUND_KG = 40.0
MAUND_HISTORICAL_KG = 37.3242  # not used; kept so the alternative is explicit
SEER_KG = MAUND_KG / 40  # 1 maund = 40 seer

MASS_IN_KG: dict[str, float] = {
    "kg": 1.0,
    "maund": MAUND_KG,
    "seer": SEER_KG,
    "quintal": 100.0,
    "metric_ton": 1000.0,
    "g": 0.001,
}

# --- aliases ----------------------------------------------------------------
# Bangla spellings reach us from the intake edge; English ones from tool params
# and the UI's unit selector. Both resolve to one canonical key.
_ALIASES: dict[str, str] = {
    # area — Bangla
    "বিঘা": "bigha",
    "কাঠা": "katha",
    "শতক": "decimal",
    "শতাংশ": "decimal",
    "একর": "acre",
    "হেক্টর": "ha",
    # area — English variants
    "hectare": "ha",
    "hectares": "ha",
    "bighas": "bigha",
    "kattha": "katha",
    "kathas": "katha",
    "decimals": "decimal",
    "shotok": "decimal",
    "acres": "acre",
    "sqft": "sq_ft",
    "sq ft": "sq_ft",
    "square_feet": "sq_ft",
    "sqm": "sq_m",
    "m2": "sq_m",
    "square_metres": "sq_m",
    # mass — Bangla
    "মণ": "maund",
    "কেজি": "kg",
    "সের": "seer",
    "টন": "metric_ton",
    # mass — English variants
    "mon": "maund",
    "maunds": "maund",
    "kilogram": "kg",
    "kilograms": "kg",
    "kgs": "kg",
    "tonne": "metric_ton",
    "ton": "metric_ton",
    "mt": "metric_ton",
    "quintals": "quintal",
    "gram": "g",
    "grams": "g",
}


class UnknownUnitError(ValueError):
    """Raised for an unrecognised unit.

    Deliberately loud. Guessing — defaulting an unknown unit to hectares, say —
    would silently produce a farm 7x the real size and a plan to match. A
    crash at intake is cheap; a confident wrong number is not (NOTES.md #9).
    """


def normalize_unit(unit: str) -> str:
    """Resolve a unit string (English or Bangla, any case) to its canonical key."""
    if not isinstance(unit, str):
        raise UnknownUnitError(f"Unit must be a string, got {type(unit).__name__}")
    key = unit.strip().lower().replace("-", "_")
    key = _ALIASES.get(key, key)
    # Bangla keys are case-insensitive no-ops but must survive the lookup.
    if key not in AREA_IN_HA and key not in MASS_IN_KG:
        raise UnknownUnitError(f"Unknown unit: {unit!r}")
    return key


def _factor(unit: str, table: dict[str, float], kind: str) -> float:
    key = normalize_unit(unit)
    if key not in table:
        raise UnknownUnitError(f"{unit!r} is not a {kind} unit")
    return table[key]


# --- public API -------------------------------------------------------------


def to_hectares(value: float, unit: str) -> float:
    """Local area -> hectares (the internal representation)."""
    return float(value) * _factor(unit, AREA_IN_HA, "area")


def from_hectares(hectares: float, unit: str) -> float:
    """Hectares -> local area, for the display edge only."""
    return float(hectares) / _factor(unit, AREA_IN_HA, "area")


def to_kg(value: float, unit: str) -> float:
    """Local mass -> kg (the internal representation)."""
    return float(value) * _factor(unit, MASS_IN_KG, "mass")


def from_kg(kilograms: float, unit: str) -> float:
    """kg -> local mass, for the display edge only."""
    return float(kilograms) / _factor(unit, MASS_IN_KG, "mass")


def convert_area(value: float, from_unit: str, to_unit: str) -> float:
    return from_hectares(to_hectares(value, from_unit), to_unit)


def convert_mass(value: float, from_unit: str, to_unit: str) -> float:
    return from_kg(to_kg(value, from_unit), to_unit)


def scale_rate(amount: float, per_unit: str, area: float, area_unit: str) -> float:
    """An application rate given per `per_unit` of land (e.g. 900 g per acre),
    applied to `area` `area_unit` (e.g. 2 bigha). Quantity unit is unchanged."""
    if area <= 0:
        raise ValueError("area must be positive")
    return float(amount) * convert_area(area, area_unit, per_unit)


def area_units() -> Iterable[str]:
    """Canonical area units, for the UI's unit selector."""
    return tuple(AREA_IN_HA)


def mass_units() -> Iterable[str]:
    return tuple(MASS_IN_KG)


# Bangla labels for the display edge. PRD.md §9: farmer-facing text is Bangla,
# but the numeral beside it stays Western (NOTES.md #17).
UNIT_LABELS_BN: dict[str, str] = {
    "ha": "হেক্টর",
    "bigha": "বিঘা",
    "katha": "কাঠা",
    "decimal": "শতক",
    "acre": "একর",
    "sq_m": "বর্গমিটার",
    "sq_ft": "বর্গফুট",
    "kg": "কেজি",
    "maund": "মণ",
    "seer": "সের",
    "quintal": "কুইন্টাল",
    "metric_ton": "টন",
    "g": "গ্রাম",
}


def label_bn(unit: str) -> str:
    return UNIT_LABELS_BN[normalize_unit(unit)]
