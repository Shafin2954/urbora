"""units.py tests (CLAUDE.md §2.12, docs/NOTES.md #9).

These guard the numbers the whole finance engine multiplies by. A silent 0.18%
drift in a bigha is a silent 0.18% drift in every profit figure on stage.

Run from the repo root:  .venv/Scripts/python -m pytest backend/tests -q
"""

import pytest

from backend.units import (
    ACRE_HA,
    BIGHA_HA,
    MAUND_KG,
    UnknownUnitError,
    convert_area,
    convert_mass,
    from_hectares,
    from_kg,
    label_bn,
    normalize_unit,
    to_hectares,
    to_kg,
)

# --- the ratified convention ------------------------------------------------


def test_bigha_matches_the_ratified_hectare_figure():
    """CLAUDE.md §2.11 / docs/NOTES.md #9: 1 bigha = 0.1338 ha."""
    assert to_hectares(1, "bigha") == pytest.approx(0.1338, abs=5e-5)
    assert BIGHA_HA == pytest.approx(0.1337803776, rel=1e-12)


def test_bigha_katha_relationship_is_exact():
    """20 katha to the bigha, with no rounding artefact in between."""
    assert to_hectares(1, "bigha") == pytest.approx(to_hectares(20, "katha"), rel=1e-15)
    assert convert_area(1, "bigha", "katha") == pytest.approx(20.0, rel=1e-12)


def test_acre_is_the_exact_international_acre():
    """Not bent to make the folk '33 decimal' equality hold."""
    assert ACRE_HA == pytest.approx(0.40468564224, rel=1e-12)
    assert convert_area(1, "acre", "decimal") == pytest.approx(100.0, rel=1e-12)


def test_bigha_is_actually_33_06_decimal_not_33():
    """The documented discrepancy, pinned so nobody 'fixes' it by accident.

    The docs say '1 bigha = 33 decimal = 0.1338 ha'. Both halves cannot be
    true; units.py anchors on 0.1338 and this test records the consequence.
    """
    assert convert_area(1, "bigha", "decimal") == pytest.approx(33.06, abs=0.01)
    # And the size of the disagreement stays under a quarter of a percent.
    thirty_three_decimal = to_hectares(33, "decimal")
    assert abs(BIGHA_HA - thirty_three_decimal) / BIGHA_HA < 0.002


# --- round trips ------------------------------------------------------------


@pytest.mark.parametrize("unit", ["ha", "bigha", "katha", "decimal", "acre", "sq_m", "sq_ft"])
def test_area_round_trip(unit):
    assert from_hectares(to_hectares(7.25, unit), unit) == pytest.approx(7.25, rel=1e-12)


@pytest.mark.parametrize("unit", ["kg", "maund", "seer", "quintal", "metric_ton", "g"])
def test_mass_round_trip(unit):
    assert from_kg(to_kg(7.25, unit), unit) == pytest.approx(7.25, rel=1e-12)


def test_demo_script_area_change():
    """docs/archive/hackathon/PLAN.md §5 step 3 changes the farm from 2 bigha to 3 live."""
    assert to_hectares(2, "bigha") == pytest.approx(0.2675607552, rel=1e-9)
    assert to_hectares(3, "bigha") == pytest.approx(0.4013411328, rel=1e-9)
    # The judged behaviour is that outputs move when the input moves.
    assert to_hectares(3, "bigha") > to_hectares(2, "bigha")


# --- mass -------------------------------------------------------------------


def test_maund_is_the_market_maund():
    """40 kg, not the 37.3242 kg historical maund — see units.py for why."""
    assert MAUND_KG == 40.0
    assert to_kg(1, "maund") == 40.0
    assert to_kg(2.5, "maund") == 100.0


def test_maund_seer_relationship():
    assert convert_mass(1, "maund", "seer") == pytest.approx(40.0, rel=1e-12)


def test_yield_conversion_realistic():
    """A ~4 t/ha Boro yield expressed in maunds per hectare."""
    assert from_kg(4000, "maund") == pytest.approx(100.0, rel=1e-12)


# --- aliases, including Bangla ----------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("বিঘা", "bigha"),
        ("কাঠা", "katha"),
        ("শতক", "decimal"),
        ("শতাংশ", "decimal"),
        ("একর", "acre"),
        ("মণ", "maund"),
        ("কেজি", "kg"),
        ("Bigha", "bigha"),
        ("  ACRE  ", "acre"),
        ("hectares", "ha"),
        ("sq-ft", "sq_ft"),
        ("maunds", "maund"),
        ("mon", "maund"),
        ("shotok", "decimal"),
    ],
)
def test_alias_resolution(raw, expected):
    assert normalize_unit(raw) == expected


def test_bangla_intake_converts():
    """'২ বিঘা' arrives as (2, 'বিঘা') from the intake edge."""
    assert to_hectares(2, "বিঘা") == pytest.approx(2 * BIGHA_HA, rel=1e-12)


def test_bangla_labels_for_display():
    assert label_bn("bigha") == "বিঘা"
    assert label_bn("kg") == "কেজি"
    assert label_bn("maund") == "মণ"


# --- failure is loud --------------------------------------------------------


@pytest.mark.parametrize("bad", ["", "  ", "furlong", "cubit", "dragonfruit", "ha ha"])
def test_unknown_units_raise(bad):
    with pytest.raises(UnknownUnitError):
        to_hectares(1, bad)


def test_non_string_unit_raises():
    with pytest.raises(UnknownUnitError):
        to_hectares(1, None)


def test_mass_unit_rejected_for_area_and_vice_versa():
    """The expensive mistake: silently treating maunds as an area."""
    with pytest.raises(UnknownUnitError):
        to_hectares(1, "maund")
    with pytest.raises(UnknownUnitError):
        to_kg(1, "bigha")


def test_zero_and_negative_pass_through_untouched():
    """Validation belongs at intake, not here; conversion stays a pure scale."""
    assert to_hectares(0, "bigha") == 0.0
    assert to_hectares(-1, "bigha") == pytest.approx(-BIGHA_HA, rel=1e-12)
