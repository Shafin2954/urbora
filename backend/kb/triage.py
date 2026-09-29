"""Crop-problem triage — a deterministic lookup, bounded by our KB.

A farmer on a button phone reports a problem by digits: crop → growth stage →
where on the plant → what it looks like → how much of the field → last week's
weather. `diagnose()` maps that to the candidate problems our curated KB
covers (data/kb/corpus.json, backend/tools/pest_risk.py). The model never picks
a diagnosis (the spirit of CLAUDE.md rule 1), and nothing here is general
knowledge: a combination with no KB passage returns `coverage="none"`, and the
farmer is referred to the local SAAO / 16123 instead of being guessed at.

Design and sources: CHANNELS_RESEARCH.md §4 (agronomy review, 2026-09-28).

Coverage, per candidate:
  S  the symptom itself is described in the KB passage
  W  organism, stage window and treatment are in the KB, the symptom is not —
     said as "হতে পারে"
  P  organism only named in a survey, no treatment — named, then referred

Doses: only for an S candidate, only as the passage states it (every number in
`Dose.text_bn` must appear in the passage — tested), and area rates are
scaled to the farmer's land by `units.scale_rate`, never by the model.
Carbofuran (the YSB passage) is withheld: it is highly hazardous and its current
registration must be checked with DAE before any SMS quotes it.

Stage day-ranges are derived from season_plan / pest_risk offsets, not stated by
a source — confidence low, so they travel as ranges, never as a single day.
For rice the count is days after *transplanting*.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

CORPUS_PATH = Path(__file__).resolve().parents[2] / "data" / "kb" / "corpus.json"

CROPS: list[tuple[str, str]] = [
    ("aman_rice", "আমন ধান"), ("boro_rice", "বোরো ধান"), ("potato", "আলু"),
    ("mustard", "সরিষা"), ("lentil", "মসুর"),
]
CROP_BN = dict(CROPS)

# (key, Bangla label, first day, last day)
STAGES: dict[str, list[tuple[str, str, int, int]]] = {
    "aman_rice": [("seedling", "চারা", 0, 17), ("tillering", "কুশি", 18, 59), ("booting", "থোড়", 60, 74),
                  ("flowering", "ফুল", 75, 89), ("grain", "দানা/পাকা", 90, 120)],
    "boro_rice": [("seedling", "চারা", 0, 19), ("tillering", "কুশি", 20, 54), ("booting", "থোড়", 55, 74),
                  ("flowering", "ফুল", 75, 94), ("grain", "দানা/পাকা", 95, 125)],
    "potato": [("seedling", "চারা", 0, 24), ("vegetative", "বাড়ন্ত", 25, 44),
               ("tuber_bulking", "আলু ধরছে", 45, 79), ("mature", "পাকা", 80, 100)],
    "mustard": [("seedling", "চারা", 0, 20), ("vegetative", "বাড়ন্ত", 21, 34), ("flowering", "ফুল", 35, 59),
                ("pod", "শুঁটি", 60, 79), ("mature", "পাকা", 80, 90)],
    "lentil": [("seedling", "চারা", 0, 29), ("vegetative", "বাড়ন্ত", 30, 49), ("flowering", "ফুল", 50, 69),
               ("pod", "শুঁটি", 70, 99), ("mature", "পাকা", 100, 120)],
}
RICE = ("aman_rice", "boro_rice")

ORGAN_BN = {"leaf": "পাতা", "stem": "কাণ্ড", "sheath": "কাণ্ড/খোল", "root": "শিকড়", "panicle": "শীষ/দানা",
            "tuber": "আলু", "pod": "ফুল/শুঁটি", "whole": "পুরো গাছ"}

SYMPTOM_BN = {
    "yellow": "হলুদ", "spots": "দাগ", "insects": "পোকা/ডিম", "burnt": "পোড়া ভাব", "other": "অন্য",
    "deadheart": "ডগা শুকানো", "sheath_spots": "খোলে দাগ", "cut": "কাটা", "rot": "পচা",
    "white_head": "সাদা/চিটা শীষ", "grain_spots": "দানায় দাগ", "holes": "ছিদ্র",
    "flower_drop": "ফুল ঝরা", "wilting": "ঢলে পড়া", "stunted": "বাড়ে না",
}

EXTENTS = [("little", "অল্প"), ("half", "অর্ধেক"), ("most", "প্রায় সব")]
WEATHER = [("rain_fog", "বৃষ্টি/কুয়াশা"), ("fertilizer", "সার দিয়েছি"), ("both", "দুটোই"), ("none", "না")]


def organs(crop: str) -> list[str]:
    if crop in RICE:
        return ["leaf", "sheath", "root", "panicle", "whole"]
    if crop == "potato":
        return ["leaf", "stem", "root", "tuber", "whole"]
    return ["leaf", "stem", "root", "pod", "whole"]


def symptoms(crop: str, organ: str) -> list[str]:
    table = {
        "leaf": ["yellow", "spots", "insects", "burnt", "other"],
        "sheath": ["deadheart", "sheath_spots", "insects", "other"],
        "stem": ["insects", "cut", "other"],
        "root": ["rot", "insects", "other"],
        "panicle": ["white_head", "insects", "grain_spots", "other"],
        "tuber": ["holes", "rot", "other"],
        "pod": ["insects", "holes", "spots", "flower_drop", "other"],
        "whole": ["wilting", "burnt", "stunted", "yellow", "other"],
    }
    return table[organ]


@dataclass(frozen=True)
class Dose:
    text_bn: str                     # as the passage states it, in Bangla
    kb_id: str
    amount: float | None = None      # an area rate, scaled to the farmer's land
    unit_bn: str = ""                # of `amount` (গ্রাম, কেজি)
    per: str | None = None           # area unit the rate is per (ha, acre, bigha)
    water_l: float | None = None     # spray water per the same area, scaled alongside


@dataclass(frozen=True)
class Candidate:
    key: str
    name_bn: str
    kb_id: str
    coverage: str                    # S | W | P
    advice_bn: str = ""              # what to do, from the passage; no numbers unless it states them
    dose: Dose | None = None
    spray: bool = True               # a pesticide/fungicide answer carries the spray-safety lines
    advice_kb: str | None = None     # the passage the advice comes from, when not `kb_id`


@dataclass(frozen=True)
class Rule:
    crop: str
    organ: str
    symptoms: tuple[str, ...]
    days: tuple[int, int]
    candidate: Candidate
    needs_weather: str | None = None  # "rain_fog": only if the farmer reported rain/fog/cold


SAAO_LINE = "স্প্রের আগে স্থানীয় কৃষি অফিসার (SAAO)-কে দেখান।"
GEAR_LINE = "স্প্রের সময় মাস্ক-দস্তানা পরুন।"
HOTLINE_LINE = "কৃষি কল সেন্টার: 16123"
NO_KB_TEXT = ("তথ্য যথেষ্ট নয়: এই লক্ষণের যাচাই করা তথ্য আমাদের কাছে নেই। "
              "স্থানীয় উপসহকারী কৃষি কর্মকর্তা (SAAO) বা কৃষি কল সেন্টার 16123-এ কল করুন।")

_YSB = Candidate("yellow_stem_borer", "মাজরা পোকা", "aman_pest_ysb", "S",
                 "পরের বার রোপণের সময় চারার আগা কেটে লাগান। কীটনাশকের জন্য SAAO-র পরামর্শ নিন।")
_BPH_P = Candidate("brown_planthopper", "বাদামি গাছফড়িং (বিপিএইচ)", "boro_pest_bph", "P",
                   "আইলের আগাছা পরিষ্কার করুন।")

RULES: list[Rule] = [
    # --- aman rice
    Rule("aman_rice", "sheath", ("deadheart",), (18, 59), _YSB),
    Rule("aman_rice", "leaf", ("insects",), (18, 74), _YSB),
    Rule("aman_rice", "panicle", ("white_head",), (60, 120), _YSB),
    Rule("aman_rice", "leaf", ("spots",), (30, 89),
         Candidate("blast", "ব্লাস্ট রোগ", "aman_disease_blast", "W",
                   "রোগ দেখা দিলেই ট্রাইসাইক্লাজল ছত্রাকনাশক স্প্রে; মাত্রা লেবেল/SAAO থেকে জানুন।")),
    Rule("aman_rice", "sheath", ("sheath_spots",), (40, 120),
         Candidate("sheath_blight", "খোলপোড়া রোগ", "aman_disease_sheathblight", "W",
                   "একটানা পানি না রেখে পর্যায়ক্রমে ভেজানো-শুকানো (AWD) সেচ দিন।")),
    Rule("aman_rice", "whole", ("burnt",), (0, 120), _BPH_P),
    # --- boro rice
    Rule("boro_rice", "sheath", ("deadheart",), (20, 54),
         Candidate("stem_borer", "মাজরা পোকা", "boro_pest_stemborer", "S",
                   "আক্রমণ দেখা দিলে কীটনাশক দিন।",
                   Dose("ভিরতাকো 40WG, হেক্টরে 75 গ্রাম", "boro_pest_stemborer", 75, "গ্রাম", "ha"))),
    Rule("boro_rice", "panicle", ("white_head",), (55, 125), _YSB),
    Rule("boro_rice", "panicle", ("white_head",), (55, 94),
         Candidate("cold_injury", "ঠান্ডার ক্ষতি", "boro_critical_temp", "W",
                   "শৈত্যপ্রবাহে জমিতে 5-7 সেমি পানি ধরে রাখুন।", spray=False,
                   advice_kb="boro_irrigation_awd"),
         needs_weather="rain_fog"),
    Rule("boro_rice", "whole", ("burnt", "wilting"), (45, 125),
         Candidate("brown_planthopper", "বাদামি গাছফড়িং (বিপিএইচ)", "boro_pest_bph", "S",
                   "আইলের আগাছা পরিষ্কার করুন; পরের বার প্রতিরোধী জাত লাগান।")),
    Rule("boro_rice", "sheath", ("insects",), (45, 125),
         Candidate("brown_planthopper", "বাদামি গাছফড়িং (বিপিএইচ)", "boro_pest_bph", "S",
                   "আইলের আগাছা পরিষ্কার করুন; পরের বার প্রতিরোধী জাত লাগান।")),
    Rule("boro_rice", "leaf", ("yellow",), (0, 125),
         Candidate("sulphur_deficiency", "গন্ধকের অভাব", "boro_nutrient_topdress", "S",
                   "বাড়তি জিপসাম উপরি প্রয়োগ করুন।",
                   Dose("বিঘায় বাড়তি 8 কেজি জিপসাম", "boro_nutrient_topdress", 8, "কেজি", "bigha"),
                   spray=False)),
    Rule("boro_rice", "whole", ("yellow",), (0, 125),
         Candidate("sulphur_deficiency", "গন্ধকের অভাব", "boro_nutrient_topdress", "S",
                   "বাড়তি জিপসাম উপরি প্রয়োগ করুন।",
                   Dose("বিঘায় বাড়তি 8 কেজি জিপসাম", "boro_nutrient_topdress", 8, "কেজি", "bigha"),
                   spray=False)),
    Rule("boro_rice", "whole", ("stunted",), (0, 125),
         Candidate("zinc_deficiency", "দস্তার অভাব", "boro_nutrient_topdress", "S",
                   "জিংক সালফেট প্রয়োগ করুন।",
                   Dose("বিঘায় 1.5 কেজি জিংক সালফেট", "boro_nutrient_topdress", 1.5, "কেজি", "bigha"),
                   spray=False)),
    Rule("boro_rice", "whole", ("stunted",), (0, 125),
         Candidate("bph_virus", "বিপিএইচ-বাহিত ভাইরাস", "boro_pest_bph", "W",
                   "আইলের আগাছা পরিষ্কার করুন।")),
    # --- potato
    Rule("potato", "leaf", ("spots", "burnt"), (30, 75),
         Candidate("late_blight", "নাবি ধসা (লেট ব্লাইট)", "potato_disease_blight", "S",
                   "ম্যানকোজেব-জাতীয় ছত্রাকনাশক স্প্রে করুন; মাত্রা লেবেল/SAAO থেকে জানুন।")),
    Rule("potato", "leaf", ("spots",), (30, 75),
         Candidate("early_blight", "আগাম ধসা (আর্লি ব্লাইট)", "potato_disease_biocontrol", "W",
                   "ট্রাইকোডার্মা-ভিত্তিক জৈব ছত্রাকনাশক বা ম্যানকোজেব কাজ করে।")),
    Rule("potato", "leaf", ("insects",), (25, 70),
         Candidate("aphid", "জাব পোকা", "potato_pest_aphid", "W",
                   "জাব পোকা ভাইরাস ছড়ায়। ইমিডাক্লোপ্রিড-জাতীয় কীটনাশক; মাত্রা লেবেল/SAAO থেকে জানুন।")),
    Rule("potato", "stem", ("cut",), (0, 100),
         Candidate("cutworm", "কাটুই পোকা", "potato_pest_survey", "P")),
    Rule("potato", "tuber", ("holes",), (0, 100),
         Candidate("tuber_moth", "আলুর সুতলি পোকা", "potato_pest_survey", "P")),
    Rule("potato", "whole", ("stunted",), (0, 100),
         Candidate("virus", "ভাইরাস (জাব পোকা বাহিত)", "potato_pest_aphid", "W",
                   "জাব পোকা দমন করুন। ভাইরাসের চিকিৎসা আমাদের তথ্যে নেই।")),
    # --- mustard
    Rule("mustard", "leaf", ("spots",), (35, 75),
         Candidate("alternaria", "অল্টারনারিয়া ব্লাইট", "mustard_disease_alternaria", "S",
                   "রোগ দেখা দিলেই ইপ্রোডিয়ন ছত্রাকনাশক অনুমোদিত মাত্রায়, 10-12 দিন পরপর 3-4 বার।")),
    Rule("mustard", "pod", ("insects",), (45, 85),
         Candidate("aphid", "জাব পোকা", "mustard_pest_aphid", "S", "কীটনাশক স্প্রে করুন।",
                   Dose("ম্যালাথিয়ন 57EC, প্রতি লিটার পানিতে 2 মিলি", "mustard_pest_aphid"))),
    Rule("mustard", "leaf", ("insects",), (45, 85),
         Candidate("aphid", "জাব পোকা", "mustard_pest_aphid", "S", "কীটনাশক স্প্রে করুন।",
                   Dose("ম্যালাথিয়ন 57EC, প্রতি লিটার পানিতে 2 মিলি", "mustard_pest_aphid"))),
    # --- lentil
    Rule("lentil", "leaf", ("spots", "burnt"), (40, 80),
         Candidate("stemphylium", "স্টেমফাইলিয়াম ব্লাইট", "lentil_disease_stemphylium", "W",
                   "ফুল আসার পর M-45 (ম্যানকোজেব) স্প্রে; পরের বার বারি মসুর-8 লাগান।")),
    Rule("lentil", "leaf", ("spots",), (40, 80),
         Candidate("rust", "মরিচা রোগ", "lentil_disease_rust_blight", "W", "M-45 (ম্যানকোজেব) স্প্রে করুন।")),
    Rule("lentil", "pod", ("holes", "insects"), (55, 95),
         Candidate("pod_borer", "ফল ছিদ্রকারী পোকা", "lentil_pest_podborer", "S",
                   "ফুল আসার সময় স্প্রে; আক্রমণ থাকলে 3 সপ্তাহ পর আবার।",
                   Dose("হেক্সাভিন 50WP (কার্বারিল), একরে 900 গ্রাম, 90 লিটার পানিতে",
                        "lentil_pest_podborer", 900, "গ্রাম", "acre", water_l=90))),
    Rule("lentil", "root", ("rot",), (0, 120),
         Candidate("root_rot", "গোড়া পচা", "lentil_disease_stemphylium", "W", "পরের বার বারি মসুর-8 লাগান।")),
    Rule("lentil", "whole", ("wilting",), (0, 120),
         Candidate("root_rot", "গোড়া পচা", "lentil_disease_stemphylium", "W", "পরের বার বারি মসুর-8 লাগান।")),
]


@lru_cache(maxsize=1)
def corpus() -> dict[str, dict]:
    data = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    return {p["id"]: p for p in data["passages"]}


def stage(crop: str, key: str) -> tuple[str, str, int, int]:
    return next(s for s in STAGES[crop] if s[0] == key)


@dataclass
class Diagnosis:
    request: dict
    candidates: list[Candidate] = field(default_factory=list)

    @property
    def coverage(self) -> str:
        if not self.candidates:
            return "none"
        return "covered" if any(c.coverage == "S" for c in self.candidates) else "partial"

    def dose_allowed(self) -> bool:
        """A dose only for a single S candidate that is not a whole-field outbreak."""
        s = [c for c in self.candidates if c.coverage == "S"]
        return len({c.key for c in s}) == 1 and self.request.get("extent") != "most" and s[0].dose is not None

    def to_dict(self) -> dict:
        return {**self.request, "coverage": self.coverage, "candidates": [
            {"key": c.key, "name_bn": c.name_bn, "kb_id": c.kb_id, "advice_kb": c.advice_kb,
             "coverage": c.coverage,
             "source_title": corpus().get(c.kb_id, {}).get("source_title"),
             "confidence": corpus().get(c.kb_id, {}).get("confidence")}
            for c in self.candidates]}


def diagnose(crop: str, stage_key: str, organ: str, symptom: str, extent: str,
             weather: str = "none", days_exact: int | None = None) -> Diagnosis:
    """The KB-covered candidates for what the farmer reported. Deterministic."""
    _, stage_bn, lo, hi = stage(crop, stage_key)
    if days_exact is not None:
        lo = hi = days_exact
    request = {"crop": crop, "stage": stage_key, "stage_bn": stage_bn, "days_range": [lo, hi],
               "days_basis": "after_transplanting" if crop in RICE else "after_sowing",
               "days_exact": days_exact, "organ": organ, "symptom": symptom, "extent": extent,
               "weather_note": weather}
    fogged = weather in ("rain_fog", "both")
    found: list[Candidate] = []
    for r in RULES:
        if r.crop != crop or r.organ != organ or symptom not in r.symptoms:
            continue
        if r.days[1] < lo or r.days[0] > hi:
            continue
        if r.needs_weather == "rain_fog" and not fogged:
            continue
        if r.candidate.key not in {c.key for c in found}:
            found.append(r.candidate)
    # S before W before P: what the KB describes best comes first.
    found.sort(key=lambda c: "SWP".index(c.coverage))
    return Diagnosis(request, found)


def _fmt(value: float) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".") if value < 10 else f"{value:.0f}"


def dose_line(d: Dose, area_bigha: float | None) -> str:
    line = f"মাত্রা: {d.text_bn}"
    if d.amount is not None and d.per and area_bigha and area_bigha > 0:
        from backend.units import scale_rate
        total = scale_rate(d.amount, d.per, area_bigha, "bigha")
        water = (f", {_fmt(scale_rate(d.water_l, d.per, area_bigha, 'bigha'))} লিটার পানিতে"
                 if d.water_l else "")
        line += f" (আপনার {area_bigha:g} বিঘায় মোট {_fmt(total)} {d.unit_bn}{water})"
    return line + "।"


def answer_sms(diag: Diagnosis, area_bigha: float | None = None) -> str:
    """The farmer's SMS, built only from the table and fixed lines (rule 15)."""
    req = diag.request
    head = (f"{CROP_BN[req['crop']]} ({req['stage_bn']}), {ORGAN_BN[req['organ']]}: "
            f"{SYMPTOM_BN[req['symptom']]}।")
    if not diag.candidates:
        return f"{head}\n{NO_KB_TEXT}"
    names = ", ".join(c.name_bn for c in diag.candidates[:2])
    lines = [head, f"হতে পারে: {names}।"]
    top = diag.candidates[0]
    shown = diag.candidates[:2]
    advice = [c.advice_bn for c in shown if c.coverage != "P" and c.advice_bn]
    if not advice:
        lines.append("এর দমনের যাচাই করা তথ্য আমাদের কাছে নেই।")
    lines += list(dict.fromkeys(advice))  # two candidates may share advice
    if diag.dose_allowed():
        lines.append(dose_line(top.dose, area_bigha))
    elif req.get("extent") == "most":
        lines.append("প্রায় পুরো জমিতে হলে দেরি না করে SAAO-কে দেখান।")
    if any(c.spray for c in shown):
        lines += [SAAO_LINE, f"{GEAR_LINE} {HOTLINE_LINE}"]
    else:
        lines.append(f"সন্দেহ হলে SAAO-কে দেখান। {HOTLINE_LINE}")
    return "\n".join(lines)


def agent_note(detail: dict) -> str:
    """Context for a follow-up SMS question, as a server note to the agent."""
    return ("The farmer reported a crop problem through the keypad menu and was already sent "
            "a deterministic triage result by SMS (KB-bounded; do not re-diagnose beyond it). "
            "Answer follow-up questions against it, citing the KB passages via rag_query; "
            "never state a pesticide dose that the passage does not state. "
            f"Triage: {json.dumps(detail, ensure_ascii=False)}")
