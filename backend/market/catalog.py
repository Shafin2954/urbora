"""The input vocabulary: which generic products the marketplace knows.

Generic (active-ingredient) keys, not brand names: the agent recommends what
the cited KB passages name (mancozeb, tricyclazole, …) and fertiliser doses
name urea/TSP/MoP, so matching happens on the generic. Dealers list brands
under a generic. Bangla names are for farmer-facing text.
"""

from __future__ import annotations

GENERICS: dict[str, dict[str, str]] = {
    # fertilisers
    "urea": {"bn": "ইউরিয়া", "category": "fertilizer", "unit": "kg"},
    "tsp": {"bn": "টিএসপি", "category": "fertilizer", "unit": "kg"},
    "mop": {"bn": "এমওপি", "category": "fertilizer", "unit": "kg"},
    "dap": {"bn": "ডিএপি", "category": "fertilizer", "unit": "kg"},
    "gypsum": {"bn": "জিপসাম", "category": "fertilizer", "unit": "kg"},
    "zinc_sulphate": {"bn": "জিংক সালফেট", "category": "fertilizer", "unit": "kg"},
    "boron": {"bn": "বোরন", "category": "fertilizer", "unit": "kg"},
    # crop protection named in data/kb/corpus.json
    "mancozeb": {"bn": "ম্যানকোজেব", "category": "fungicide", "unit": "kg"},
    "metalaxyl": {"bn": "মেটালাক্সিল", "category": "fungicide", "unit": "kg"},
    "carbendazim": {"bn": "কার্বেন্ডাজিম", "category": "fungicide", "unit": "kg"},
    "tricyclazole": {"bn": "ট্রাইসাইক্লাজল", "category": "fungicide", "unit": "kg"},
    "sulphur": {"bn": "সালফার", "category": "fungicide", "unit": "kg"},
    "imidacloprid": {"bn": "ইমিডাক্লোপ্রিড", "category": "insecticide", "unit": "l"},
    "thiamethoxam": {"bn": "থায়ামেথোক্সাম", "category": "insecticide", "unit": "kg"},
}

CATEGORY_BN = {"fertilizer": "সার", "fungicide": "ছত্রাকনাশক", "insecticide": "কীটনাশক"}

_ALIASES = {
    "ইউরিয়া": "urea", "টিএসপি": "tsp", "এমওপি": "mop", "পটাশ": "mop", "ডিএপি": "dap",
    "জিপসাম": "gypsum", "দস্তা": "zinc_sulphate", "জিংক": "zinc_sulphate", "বোরন": "boron",
    "ম্যানকোজেব": "mancozeb", "মেটালাক্সিল": "metalaxyl", "কার্বেন্ডাজিম": "carbendazim",
    "ট্রাইসাইক্লাজল": "tricyclazole", "সালফার": "sulphur", "ইমিডাক্লোপ্রিড": "imidacloprid",
    "থায়ামেথোক্সাম": "thiamethoxam", "potash": "mop", "muriate of potash": "mop",
    "triple super phosphate": "tsp", "zinc": "zinc_sulphate", "agrizeb": "mancozeb",
}


def resolve_generic(name: str) -> str | None:
    """'Urea' / 'ইউরিয়া' / 'Agrizeb' -> 'urea' / 'urea' / 'mancozeb'; None if unknown."""
    key = (name or "").strip().lower().replace("-", " ")
    if key.replace(" ", "_") in GENERICS:
        return key.replace(" ", "_")
    return _ALIASES.get(key) or _ALIASES.get((name or "").strip())


def label_bn(generic: str) -> str:
    return GENERICS.get(generic, {}).get("bn", generic)
