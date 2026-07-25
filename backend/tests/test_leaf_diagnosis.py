"""leaf_diagnosis — label parsing and honest degradation.

Deliberately does NOT load the model. `backend/requirements-vision.txt` is
optional (torch is a ~200 MB download), so these must pass on a checkout that
never installed it — which is also the case they most need to cover: the whole
feature has to degrade rather than break when the model is absent.
"""

from __future__ import annotations

import pytest

from backend.tools import leaf_diagnosis as module


@pytest.mark.parametrize(
    "label,crop,condition,healthy",
    [
        # The three label shapes this checkpoint actually uses.
        ("Potato with Late Blight", "Potato", "Late Blight", False),
        ("Potato with Early Blight", "Potato", "Early Blight", False),
        ("Healthy Potato Plant", "Potato", "healthy", True),
        ("Squash with Powdery Mildew", "Squash", "Powdery Mildew", False),
        ("Apple Scab", "Apple", "scab", False),
        ("Cedar Apple Rust", "Apple", "cedar rust", False),
        ("Tomato Mosaic Virus", "Tomato", "mosaic virus", False),
    ],
)
def test_label_parsing_covers_every_shape(label, crop, condition, healthy):
    assert module._pretty(label) == (crop, condition, healthy)


def test_potato_is_recognised_as_a_crop_this_app_supports():
    """The regression that matters: an earlier parser split on '___', which this
    checkpoint's labels do not contain, so every potato photo was reported as an
    unsupported crop."""
    crop, _, _ = module._pretty("Potato with Late Blight")
    assert module._LABEL_CROP[crop] == "potato"


def test_the_four_crops_the_model_cannot_see_are_named():
    """Rice, mustard and lentil are absent from PlantVillage's label set. A
    closed-set classifier still returns a confident answer for them, so the
    payload has to say which crops it cannot see."""
    assert set(module._UNCOVERED_CROPS) == {"boro_rice", "aman_rice", "mustard", "lentil"}
    assert all(module._LABEL_CROP.get(name) is None for name in ("Tomato", "Corn", "Grape"))


def test_missing_model_degrades_instead_of_raising(monkeypatch):
    monkeypatch.setattr(module, "_classifier", lambda: None)
    monkeypatch.setattr(module, "_load_error", "ModuleNotFoundError: No module named 'torch'")

    result = module.diagnose_leaf(b"anything")
    assert result["error"] == "model_unavailable"
    assert result["degraded"] == "তথ্য যথেষ্ট নয়"
    assert result["message_bn"]


def test_disclosures_ship_with_every_result(monkeypatch):
    """The lab-imagery caveat and the covered-crop list are not optional extras
    — they must be present even on the error paths."""
    monkeypatch.setattr(module, "_classifier", lambda: None)
    result = module.diagnose_leaf(b"anything")
    assert result["field_photo_caveat_bn"]
    assert result["supported_crops_in_model"] == ["potato"]
    assert result["trained_on"].startswith("PlantVillage")
