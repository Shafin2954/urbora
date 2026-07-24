"""Hardcoded 64-district table — the geocoder's offline fallback (NOTES #6).

Public reference coordinates (approx. district-town centroids). This is the
"village-name geocoding can be silently wrong" mitigation: if the live geocoder
is unreachable or ambiguous, we fall back to these 64 canonical districts and the
agent confirms with the farmer. Rajshahi (demo district) is included.

Canonical district names use the current official English spellings; `ALIASES`
maps common older/alternate spellings to the canonical key.
"""

from __future__ import annotations

# district -> (division, lat, lon)
DISTRICTS: dict[str, tuple[str, float, float]] = {
    # Barishal
    "Barguna": ("Barishal", 22.15, 90.11),
    "Barishal": ("Barishal", 22.70, 90.37),
    "Bhola": ("Barishal", 22.69, 90.65),
    "Jhalokati": ("Barishal", 22.64, 90.20),
    "Patuakhali": ("Barishal", 22.36, 90.33),
    "Pirojpur": ("Barishal", 22.58, 89.97),
    # Chattogram
    "Bandarban": ("Chattogram", 22.20, 92.22),
    "Brahmanbaria": ("Chattogram", 23.96, 91.11),
    "Chandpur": ("Chattogram", 23.23, 90.65),
    "Chattogram": ("Chattogram", 22.36, 91.83),
    "Cumilla": ("Chattogram", 23.46, 91.18),
    "Cox's Bazar": ("Chattogram", 21.44, 91.97),
    "Feni": ("Chattogram", 23.02, 91.40),
    "Khagrachhari": ("Chattogram", 23.10, 91.98),
    "Lakshmipur": ("Chattogram", 22.94, 90.83),
    "Noakhali": ("Chattogram", 22.82, 91.10),
    "Rangamati": ("Chattogram", 22.65, 92.17),
    # Dhaka
    "Dhaka": ("Dhaka", 23.81, 90.41),
    "Faridpur": ("Dhaka", 23.60, 89.83),
    "Gazipur": ("Dhaka", 24.00, 90.42),
    "Gopalganj": ("Dhaka", 23.01, 89.83),
    "Kishoreganj": ("Dhaka", 24.44, 90.78),
    "Madaripur": ("Dhaka", 23.17, 90.20),
    "Manikganj": ("Dhaka", 23.86, 90.00),
    "Munshiganj": ("Dhaka", 23.55, 90.53),
    "Narayanganj": ("Dhaka", 23.62, 90.50),
    "Narsingdi": ("Dhaka", 23.92, 90.72),
    "Rajbari": ("Dhaka", 23.76, 89.64),
    "Shariatpur": ("Dhaka", 23.24, 90.35),
    "Tangail": ("Dhaka", 24.25, 89.92),
    # Khulna
    "Bagerhat": ("Khulna", 22.65, 89.79),
    "Chuadanga": ("Khulna", 23.64, 88.85),
    "Jashore": ("Khulna", 23.17, 89.21),
    "Jhenaidah": ("Khulna", 23.54, 89.15),
    "Khulna": ("Khulna", 22.85, 89.56),
    "Kushtia": ("Khulna", 23.90, 89.12),
    "Magura": ("Khulna", 23.49, 89.42),
    "Meherpur": ("Khulna", 23.76, 88.63),
    "Narail": ("Khulna", 23.16, 89.50),
    "Satkhira": ("Khulna", 22.72, 89.07),
    # Mymensingh
    "Jamalpur": ("Mymensingh", 24.92, 89.94),
    "Mymensingh": ("Mymensingh", 24.75, 90.40),
    "Netrokona": ("Mymensingh", 24.87, 90.73),
    "Sherpur": ("Mymensingh", 25.02, 90.02),
    # Rajshahi
    "Bogura": ("Rajshahi", 24.85, 89.37),
    "Chapainawabganj": ("Rajshahi", 24.60, 88.28),
    "Joypurhat": ("Rajshahi", 25.10, 89.02),
    "Naogaon": ("Rajshahi", 24.80, 88.94),
    "Natore": ("Rajshahi", 24.41, 89.00),
    "Pabna": ("Rajshahi", 24.00, 89.24),
    "Rajshahi": ("Rajshahi", 24.37, 88.60),
    "Sirajganj": ("Rajshahi", 24.45, 89.70),
    # Rangpur
    "Dinajpur": ("Rangpur", 25.63, 88.64),
    "Gaibandha": ("Rangpur", 25.33, 89.53),
    "Kurigram": ("Rangpur", 25.81, 89.64),
    "Lalmonirhat": ("Rangpur", 25.92, 89.45),
    "Nilphamari": ("Rangpur", 25.93, 88.86),
    "Panchagarh": ("Rangpur", 26.34, 88.56),
    "Rangpur": ("Rangpur", 25.75, 89.24),
    "Thakurgaon": ("Rangpur", 26.03, 88.47),
    # Sylhet
    "Habiganj": ("Sylhet", 24.37, 91.42),
    "Moulvibazar": ("Sylhet", 24.48, 91.78),
    "Sunamganj": ("Sylhet", 25.07, 91.40),
    "Sylhet": ("Sylhet", 24.90, 91.87),
}

# Older / alternate English spellings -> canonical key above.
ALIASES: dict[str, str] = {
    "barisal": "Barishal",
    "comilla": "Cumilla",
    "chittagong": "Chattogram",
    "coxs bazar": "Cox's Bazar",
    "cox bazar": "Cox's Bazar",
    "jessore": "Jashore",
    "bogra": "Bogura",
    "nawabganj": "Chapainawabganj",
    "chapai nawabganj": "Chapainawabganj",
    "maulvibazar": "Moulvibazar",
    "moulavibazar": "Moulvibazar",
    "khagrachari": "Khagrachhari",
    "brahminbaria": "Brahmanbaria",
    "cumilla": "Cumilla",
}

assert len(DISTRICTS) == 64, f"expected 64 districts, got {len(DISTRICTS)}"


def _norm(name: str) -> str:
    return " ".join(name.strip().lower().replace(".", "").split())


def lookup_district(name: str) -> tuple[str, str, float, float] | None:
    """Resolve a (possibly misspelled/aliased) district name to
    (canonical_district, division, lat, lon), or None if no match."""
    key = _norm(name)
    # exact (case-insensitive) match on canonical names
    for district, (division, lat, lon) in DISTRICTS.items():
        if _norm(district) == key:
            return district, division, lat, lon
    # alias match
    if key in ALIASES:
        district = ALIASES[key]
        division, lat, lon = DISTRICTS[district]
        return district, division, lat, lon
    # loose contains match (e.g. "rajshahi sadar" -> "Rajshahi")
    for district, (division, lat, lon) in DISTRICTS.items():
        dk = _norm(district)
        if dk in key or key in dk:
            return district, division, lat, lon
    return None
