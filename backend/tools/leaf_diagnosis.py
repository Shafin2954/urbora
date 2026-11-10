"""Plant disease detection from a leaf photo — docs/product/competition.md Tier 2.

A PlantVillage-trained image classifier
(`linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification`, 38 classes,
MobileNetV2) run locally on CPU through transformers. No image ever leaves the
machine.

Two limitations ship WITH every result rather than in a footnote, because both
of them can make a confident-looking answer wrong:

1. **This model only really covers potato, of our five crops.** PlantVillage's
   38 classes are apple, blueberry, cherry, corn, grape, orange, peach, pepper,
   potato, raspberry, soybean, squash, strawberry and tomato. Rice, mustard and
   lentil — three of the five crops this app advises on — are **not in the label
   set at all**. A rice leaf will therefore still be classified, confidently, as
   whichever of those 38 it most resembles. That is not a bug we can fix by
   thresholding; it is what a closed-set classifier does. So every result names
   whether the predicted crop is one we support, and a photo of an unsupported
   crop is reported as out-of-scope rather than diagnosed.

2. **PlantVillage is lab imagery.** Its photos are single detached leaves on a
   uniform background under even light. Accuracy on a real field photo — soil,
   shadow, several leaves, a thumb in frame — is substantially lower than the
   headline benchmark. The result says so, and tells the farmer to treat it as
   a second opinion, not a diagnosis.

The classifier's own label is returned untranslated alongside the Bangla text so
a judge can check what the model actually said.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any

_MODEL_ID = "linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification"

# PlantVillage label prefix -> our canonical crop, where one exists.
_LABEL_CROP = {
    "Potato": "potato",
    "Tomato": None,
    "Pepper": None,
    "Corn": None,
    "Apple": None,
    "Grape": None,
    "Cherry": None,
    "Peach": None,
    "Orange": None,
    "Strawberry": None,
    "Squash": None,
    "Soybean": None,
    "Blueberry": None,
    "Raspberry": None,
}

# Crops this app advises on that the model cannot see at all.
_UNCOVERED_CROPS = ("boro_rice", "aman_rice", "mustard", "lentil")

_pipeline: Any = None
_load_error: str | None = None


def _classifier():
    """Load once, on first use. Import is inside the function so the whole
    backend still starts (and every other tool still works) on a machine where
    torch was never installed."""
    global _pipeline, _load_error
    if _pipeline is not None or _load_error is not None:
        return _pipeline
    try:
        from transformers import pipeline  # noqa: PLC0415
        _pipeline = pipeline("image-classification", model=_MODEL_ID, device=-1)
    except Exception as exc:  # noqa: BLE001
        _load_error = f"{type(exc).__name__}: {exc}"
    return _pipeline


def _pretty(label: str) -> tuple[str, str, bool]:
    """Split a label into (crop, condition, healthy).

    This checkpoint does NOT use the raw PlantVillage `Potato___Late_blight`
    form — its labels are written as prose, in three shapes:

        'Potato with Late Blight'        crop + condition
        'Healthy Potato Plant'           crop, no disease
        'Apple Scab' / 'Cedar Apple Rust' / 'Tomato Mosaic Virus'   neither

    Matching the crop by substring rather than by position is what makes the
    third shape work; splitting on a separator (as an earlier version did)
    silently classified every potato photo as an unsupported crop, because
    'Potato with Late Blight' has no separator to split on.
    """
    text = label.strip()
    healthy = text.lower().startswith("healthy")

    crop = next((name for name in _LABEL_CROP if name.lower() in text.lower()), None)
    if crop is None:
        return text, "unknown", healthy

    if healthy:
        return crop, "healthy", True
    if " with " in text:
        return crop, text.split(" with ", 1)[1].strip(), False
    # 'Apple Scab', 'Cedar Apple Rust', 'Tomato Mosaic Virus' — the condition is
    # whatever remains once the crop name is removed.
    condition = text.lower().replace(crop.lower(), " ").split()
    return crop, " ".join(condition).strip() or "unknown", False


def diagnose_leaf(image_bytes: bytes, top_k: int = 3) -> dict:
    """Classify a leaf photo. Returns predictions plus mandatory disclosures."""
    base = {
        "model_id": _MODEL_ID,
        "trained_on": "PlantVillage (laboratory leaf imagery)",
        "supported_crops_in_model": ["potato"],
        "crops_this_app_advises_that_the_model_cannot_see": list(_UNCOVERED_CROPS),
        "field_photo_caveat_bn": (
            "এই মডেল পরীক্ষাগারে তোলা একক পাতার ছবি দিয়ে শেখানো — মাঠে তোলা ছবিতে "
            "এর নির্ভুলতা কম। এটিকে চূড়ান্ত রোগনির্ণয় নয়, দ্বিতীয় মতামত হিসেবে দেখুন।"
        ),
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    classifier = _classifier()
    if classifier is None:
        return {
            **base,
            "error": "model_unavailable",
            "detail": _load_error,
            "message_bn": "ছবি থেকে রোগ শনাক্তের মডেল এখন কাজ করছে না।",
            "degraded": "তথ্য যথেষ্ট নয়",
        }

    try:
        from PIL import Image  # noqa: PLC0415
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        return {
            **base,
            "error": "unreadable_image",
            "detail": str(exc),
            "message_bn": "ছবিটি পড়া গেল না। আবার তুলে পাঠান।",
        }

    raw = classifier(image, top_k=max(1, min(top_k, 5)))

    predictions = []
    for row in raw:
        crop_part, condition, healthy = _pretty(row["label"])
        predictions.append({
            "label": row["label"],           # untranslated, so a judge sees the model's own output
            "crop_in_photo": crop_part,
            "condition": condition,
            "healthy": healthy,
            "confidence": round(float(row["score"]), 4),
            "maps_to_supported_crop": _LABEL_CROP.get(crop_part),
        })

    top = predictions[0] if predictions else None
    supported = bool(top and top["maps_to_supported_crop"])

    return {
        **base,
        "predictions": predictions,
        "top_label": top["label"] if top else None,
        "top_confidence": top["confidence"] if top else None,
        "is_supported_crop": supported,
        # The closed-set problem, made explicit. A rice photo WILL come back as
        # one of the 38; saying so is the difference between a caveat and a lie.
        "out_of_scope_note_bn": None if supported else (
            "এই মডেল শুধু আলুসহ কয়েকটি ফসলের পাতা চেনে — ধান, সরিষা বা মসুর চেনে না। "
            "উপরের ফলাফল সেই তালিকার মধ্যে সবচেয়ে কাছের অনুমান, আপনার ফসলের রোগ নয়। "
            "এটির উপর ভরসা করবেন না।"
        ),
        "next_step_bn": (
            "রোগের নাম নিশ্চিত হলে চিকিৎসার পরামর্শের জন্য জিজ্ঞাসা করুন — "
            "সূত্রসহ পরামর্শ দেওয়া হবে।"
        ),
        "provenance": {
            "source_type": "computed",
            "source_id": f"huggingface:{_MODEL_ID}",
            "source_title": "MobileNetV2 fine-tuned on PlantVillage (38 classes)",
            "locator": f"https://huggingface.co/{_MODEL_ID}",
            "formula": "top-k softmax over 38 PlantVillage classes, CPU inference",
            "retrieved_at": base["retrieved_at"],
            "confidence": "low",  # lab-trained model on a field photo
        },
    }
