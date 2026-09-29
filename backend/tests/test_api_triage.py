"""Web crop-problem check (/api/triage/*): same table as USSD menu 2, dose scaled by code."""

from fastapi.testclient import TestClient

from backend.api.main import app

client = TestClient(app)


def test_options_lists_every_crop_with_stages_and_symptoms():
    data = client.get("/api/triage/options").json()
    keys = [c["key"] for c in data["crops"]]
    assert keys == ["aman_rice", "boro_rice", "potato", "mustard", "lentil"]
    boro = data["crops"][1]
    assert boro["stages"][1] == {"key": "tillering", "name_bn": "কুশি", "days": [20, 54]}
    sheath = next(o for o in boro["organs"] if o["key"] == "sheath")
    assert "deadheart" in [s["key"] for s in sheath["symptoms"]]


def test_boro_deadheart_scales_the_dose_to_the_farmers_land():
    r = client.post("/api/triage/check", json={"crop": "boro_rice", "stage": "tillering", "organ": "sheath",
                                              "symptom": "deadheart", "extent": "little", "area_bigha": 2}).json()
    assert r["coverage"] == "covered"
    assert r["candidates"][0]["key"] == "stem_borer"
    # 75 g/ha x 2 bigha (0.2676 ha) = 20.07 g -> "20", same figure as the SMS
    assert r["dose"]["total"]["value"] == "20"
    prov = r["dose"]["total"]["prov"]
    assert prov["source_type"] == "computed" and "scale_rate" in prov["formula"]
    assert r["safety_bn"] and "16123" not in " ".join(r["safety_bn"])


def test_whole_field_outbreak_withholds_the_dose():
    r = client.post("/api/triage/check", json={"crop": "boro_rice", "stage": "tillering", "organ": "sheath",
                                              "symptom": "deadheart", "extent": "most", "area_bigha": 2}).json()
    assert r["dose"] is None
    assert r["safety_bn"][0].startswith("প্রায় পুরো জমিতে")


def test_uncovered_combination_says_so_instead_of_guessing():
    r = client.post("/api/triage/check", json={"crop": "potato", "stage": "seedling", "organ": "root",
                                              "symptom": "other"}).json()
    assert r["coverage"] == "none" and r["candidates"] == []
    assert r["no_kb_bn"].startswith("তথ্য যথেষ্ট নয়")


def test_rejects_symptoms_the_crop_does_not_have():
    r = client.post("/api/triage/check", json={"crop": "potato", "stage": "seedling", "organ": "panicle",
                                              "symptom": "white_head"})
    assert r.status_code == 400
