"""Cited agronomy facts used by the deterministic crop scorer.

These are intentionally small, auditable facts rather than LLM knowledge. Each
entry is hand-curated from the named government sources below. Climate scoring
is supplied separately from BAMIS/Open-Meteo because its input is district and
month specific.
"""

from __future__ import annotations

from backend.tools.crop_scorer import CropFacts


SOURCE_ID = "ais_bamis_2026"
SOURCE_TITLE = "AIS e-Krishi and BAMIS crop guidance"

# Source locators are retained here so the facts can be audited in code and
# copied to UI provenance when the scorer activates them.
LOCATORS = {
    "lentil": "AIS e-Krishi ‘মসুর’: well-drained loam; sow late Oct–early Nov; light irrigation only if moisture is deficient",
    "mustard": "AIS কৃষিকথা ‘তেলজাতীয় ফসল সরিষার গুরুত্ব এবং চাষাবাদ পদ্ধতি’: sandy-loam to clay-loam; sow late Oct–mid Nov",
    "potato": "AIS e-Krishi ‘আলু’: sandy-loam/loam; irrigate at 20–25, 40–45, and 60–65 days after planting",
    "boro_rice": "BAMIS ‘Rice Boro’: very high water requirement; Rabi irrigation management",
    "aman_rice": "BRRI ‘ধানের বর্ষপঞ্জিকা (আমন)’ and BAMIS rice-water guidance",
}


# Soil classes are deliberately conservative: only source-stated fits are
# included. A missing class excludes rather than pretending suitability.
CROP_FACTS: dict[str, CropFacts] = {
    "lentil": CropFacts(
        crop="lentil", seasons=frozenset({"rabi"}),
        soil_primary=frozenset({"loam"}),
        soil_secondary=frozenset({"sandy_loam", "clay_loam"}),
        soil_marginal=frozenset(), water_min_rank=0, water_need="low",
        temp_opt_c=(10.0, 25.0), rain_opt_mm=(0.0, 100.0),
        growing_months=frozenset({11, 12, 1, 2, 3}),
        source_id=SOURCE_ID, source_title=SOURCE_TITLE, locator=LOCATORS["lentil"],
    ),
    "mustard": CropFacts(
        crop="mustard", seasons=frozenset({"rabi"}),
        soil_primary=frozenset({"sandy_loam", "clay_loam"}),
        soil_secondary=frozenset({"loam"}), soil_marginal=frozenset(),
        water_min_rank=0, water_need="low", temp_opt_c=(15.0, 29.0),
        rain_opt_mm=(0.0, 100.0), growing_months=frozenset({10, 11, 12, 1, 2}),
        source_id=SOURCE_ID, source_title=SOURCE_TITLE, locator=LOCATORS["mustard"],
    ),
    "potato": CropFacts(
        crop="potato", seasons=frozenset({"rabi"}),
        soil_primary=frozenset({"sandy_loam", "loam"}),
        soil_secondary=frozenset(), soil_marginal=frozenset(),
        water_min_rank=1, water_need="medium", temp_opt_c=(15.0, 20.0),
        rain_opt_mm=(400.0, 600.0), growing_months=frozenset({11, 12, 1, 2}),
        source_id=SOURCE_ID, source_title=SOURCE_TITLE, locator=LOCATORS["potato"],
    ),
    "boro_rice": CropFacts(
        crop="boro_rice", seasons=frozenset({"rabi"}),
        soil_primary=frozenset({"clay", "clay_loam", "loam"}),
        soil_secondary=frozenset({"silt"}), soil_marginal=frozenset(),
        water_min_rank=2, water_need="high", temp_opt_c=(20.0, 36.0),
        rain_opt_mm=(1120.0, 1500.0), growing_months=frozenset({12, 1, 2, 3, 4, 5}),
        source_id=SOURCE_ID, source_title=SOURCE_TITLE, locator=LOCATORS["boro_rice"],
    ),
    "aman_rice": CropFacts(
        crop="aman_rice", seasons=frozenset({"kharif2"}),
        soil_primary=frozenset({"clay", "clay_loam", "loam", "silt"}),
        soil_secondary=frozenset(), soil_marginal=frozenset(),
        water_min_rank=0, water_need="medium", temp_opt_c=(20.0, 36.0),
        rain_opt_mm=(800.0, 1500.0), growing_months=frozenset({7, 8, 9, 10, 11}),
        source_id=SOURCE_ID, source_title=SOURCE_TITLE, locator=LOCATORS["aman_rice"],
    ),
}
