"""Small, local retrieval layer for the curated Tier 0 agronomy evidence.

This is deliberately deterministic and dependency-free: the indexed corpus is
the hand-curated, source-cited facts already used by the scorer and calendar.
The agent supplies English queries, retrieval ranks matching records, and the
returned passages—not model recall—ground its explanation.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone


_DOCS = (
    {
        "id": "lentil_ais", "crop": "lentil", "title": "AIS e-Krishi: Lentil",
        "locator": "AIS e-Krishi ‘মসুর’",
        "text": "Lentil is a Rabi crop. Sow from late October to early November in well-drained loam. Give light irrigation only when moisture is deficient and avoid waterlogging.",
    },
    {
        "id": "mustard_ais", "crop": "mustard", "title": "AIS কৃষিকথা: Mustard cultivation",
        "locator": "AIS কৃষিকথা ‘তেলজাতীয় ফসল সরিষার গুরুত্ব এবং চাষাবাদ পদ্ধতি’",
        "text": "Mustard is a Rabi crop. Sow from late October to mid-November in sandy-loam through clay-loam soil. Keep the crop free of weeds and inspect it at crop stages.",
    },
    {
        "id": "potato_ais", "crop": "potato", "title": "AIS e-Krishi: Potato",
        "locator": "AIS e-Krishi ‘আলু’",
        "text": "Potato is a Rabi crop suited to sandy-loam or loam. Irrigate around 20–25, 40–45, and 60–65 days after planting; inspect weeds and pests before each irrigation.",
    },
    {
        "id": "boro_bamis", "crop": "boro_rice", "title": "BAMIS: Rice Boro",
        "locator": "BAMIS ‘Rice Boro’",
        "text": "Boro rice is a Rabi crop with a high water requirement. Use irrigated land and keep water management and crop-health checkpoints on the calendar.",
    },
    {
        "id": "aman_brri_bamis", "crop": "aman_rice", "title": "BRRI/BAMIS: Aman rice calendar",
        "locator": "BRRI ‘ধানের বর্ষপঞ্জিকা (আমন)’ and BAMIS rice-water guidance",
        "text": "Aman rice is a Kharif-2 crop. Its calendar includes land preparation, transplanting, nitrogen timing, weeding, water checks, pest checkpoints, and harvest.",
    },
)


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", value.lower()))


def rag_query(query: str, crop: str | None = None, limit: int = 3) -> dict:
    """Retrieve source-cited agronomy passages for an English agent query."""
    if not query.strip():
        return {"error": "query is required"}
    if limit < 1 or limit > 5:
        return {"error": "limit must be between 1 and 5"}

    query_tokens = _tokens(query)
    rows = [row for row in _DOCS if crop is None or row["crop"] == crop]
    if crop is not None and not rows:
        return {"error": f"no curated KB record for crop: {crop}"}
    ranked = sorted(
        ((len(query_tokens & _tokens(row["text"] + " " + row["crop"])), row) for row in rows),
        key=lambda pair: pair[0], reverse=True,
    )[:limit]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "query": query,
        "crop": crop,
        "matches": [
            {
                "id": row["id"], "crop": row["crop"], "text": row["text"],
                "score": score, "source_type": "kb", "source_id": row["id"],
                "source_title": row["title"], "locator": row["locator"],
                "retrieved_at": now, "confidence": "medium",
            }
            for score, row in ranked
        ],
    }
