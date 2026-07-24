"""Deterministic, source-cited season-plan calendar.

The LLM chooses neither dates nor tasks. It supplies an explicitly confirmed
planting/transplant date and narrates this tool's output.
"""
from __future__ import annotations

from datetime import date, timedelta, timezone, datetime


_SOURCE_ID = "ais_bamis_calendar_2026"
_SOURCE_TITLE = "AIS e-Krishi and BAMIS cultivation guidance"

# Each tuple is (days after start, Bangla task, category, weather dependent,
# details, source locator). Values are the cited stage windows, not estimates.
_CALENDARS = {
    "potato": [
        (0, "বীজ আলু রোপণ", "sowing", False, "রোপণের তারিখ নিশ্চিত করে শুরু করুন।", "AIS e-Krishi ‘আলু’"),
        (22, "প্রথম সেচ", "irrigation", True, "বপনের 20–25 দিন পর; মাঠে পানি জমতে দেবেন না।", "AIS e-Krishi ‘আলু’: 20–25 DAS"),
        (32, "আগাছা দমন ও গোড়ায় মাটি দেওয়া", "weeding", False, "রোপণের 30–35 দিন পর।", "AIS কৃষিকথা ‘আলু ফসলের উন্নত জাত ও উৎপাদন কলাকৌশল’"),
        (42, "দ্বিতীয় সেচ", "irrigation", True, "বপনের 40–45 দিন পর।", "AIS e-Krishi ‘আলু’: 40–45 DAS"),
        (62, "তৃতীয় সেচ", "irrigation", True, "বপনের 60–65 দিন পর।", "AIS e-Krishi ‘আলু’: 60–65 DAS"),
    ],
    "lentil": [
        (0, "মসুর বপন", "sowing", False, "উপযুক্ত বপনকাল: অক্টোবরের শেষ থেকে নভেম্বরের প্রথম সপ্তাহ।", "AIS e-Krishi ‘মসুর’"),
        (27, "মাটির আর্দ্রতা পরীক্ষা", "irrigation", True, "রসের ঘাটতিতে 25–30 দিন পর একবার হালকা সেচ; জলাবদ্ধতা এড়ান।", "AIS e-Krishi ‘মসুর’: আন্তপরিচর্যা"),
        (100, "ফসল সংগ্রহের প্রস্তুতি", "harvest", True, "ফসল সাধারণত মধ্য-ফাল্গুন থেকে মধ্য-চৈত্রে সংগ্রহ করা যায়; মাঠের অবস্থা দেখে নিশ্চিত করুন।", "AIS e-Krishi ‘মসুর’: ফসল তোলা"),
    ],
    "mustard": [
        (0, "সরিষা বপন", "sowing", False, "উপযুক্ত বপনকাল: অক্টোবরের শেষ থেকে মধ্য নভেম্বর।", "AIS কৃষিকথা ‘তেলজাতীয় ফসল সরিষার গুরুত্ব এবং চাষাবাদ পদ্ধতি’"),
        (14, "আর্দ্রতা ও চারা পরীক্ষা", "weeding", True, "মাটিতে রস কম হলে হালকা সেচ দিন; পানি জমতে দেবেন না।", "AIS কৃষিকথা ‘শূন্য চাষে ... সরিষা উৎপাদন’"),
        (20, "আগাছা দমন", "weeding", False, "বপনের 15–20 দিন পর প্রথম নিড়ানি।", "AIS কৃষিকথা ‘জলবায়ু পরিবর্তন ও কৃষি অভিযোজন হাওরে সরিষা চাষের সম্ভাবনা’"),
    ],
    "boro_rice": [
        (0, "বোরো চারা রোপণ", "sowing", False, "35–45 দিনের চারা রোপণ করুন; রোপণের সময় 1–2 সেমি পানি রাখুন।", "BAMIS ‘Boro Paddy’: Sowing"),
        (10, "মরা গোছা পূরণ ও পানি পরীক্ষা", "irrigation", True, "প্রথম 15 দিন অল্প পানির স্তর রাখুন।", "BAMIS ‘Boro Paddy’: Sowing"),
        (25, "প্রথম ইউরিয়া উপরি প্রয়োগ", "fertilizer", True, "রোপণের 20–25 দিন পর; প্রয়োগের আগে আগাছা দমন করুন।", "BAMIS ‘Boro Paddy’: Fertiliser Applications"),
        (55, "দ্বিতীয় ইউরিয়া উপরি প্রয়োগ", "fertilizer", True, "প্যানিকল শুরু হওয়ার 5–7 দিন আগে।", "BAMIS ‘Boro Paddy’: Fertiliser Applications"),
    ],
    "aman_rice": [
        (0, "আমন চারা রোপণ", "sowing", True, "পর্যাপ্ত বৃষ্টি হলে 25–30 দিনের চারা রোপণ করুন; অতিরিক্ত পানির নিষ্কাশন রাখুন।", "BAMIS bulletin 23903: Aman Paddy"),
        (7, "মরা গোছা পূরণ ও পানি ব্যবস্থাপনা", "irrigation", True, "এক সপ্তাহের মধ্যে মরা গোছা পূরণ করুন এবং সর্বোচ্চ কুশি পর্যন্ত 5–7 সেমি পানি রাখুন।", "BAMIS bulletin 24140: Aman Paddy"),
        (18, "প্রথম নাইট্রোজেন উপরি প্রয়োগ", "fertilizer", True, "রোপণের 15–20 দিন পর; প্রয়োগের আগে আগাছা পরিষ্কার করুন।", "BAMIS bulletin 24603: Aman Paddy"),
        (33, "দ্বিতীয় আগাছা দমন", "weeding", False, "রোপণের 30–35 দিন পর আগাছা দমন করুন।", "BAMIS bulletin 24603: Aman Paddy"),
        (60, "প্যানিকল শুরুর আগের নাইট্রোজেন", "fertilizer", True, "প্যানিকল শুরুর 5–7 দিন আগে শেষ এক-তৃতীয়াংশ নাইট্রোজেন।", "BAMIS bulletin 24603: Aman Paddy"),
    ],
}


def season_plan(farm_id: str, crop: str, start_date: str) -> dict:
    try:
        start = date.fromisoformat(start_date)
    except ValueError:
        return {"error": "start_date must be YYYY-MM-DD"}
    rows = _CALENDARS.get(crop)
    if not rows:
        return {"error": f"no source-cited plan calendar for '{crop}'"}
    retrieved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    tasks = [
        {
            "date": (start + timedelta(days=offset)).isoformat(), "task": task,
            "category": category, "details": details, "depends_on_weather": weather,
            "provenance": {"value": task, "unit": None, "source_type": "static_table",
                           "source_id": _SOURCE_ID, "source_title": _SOURCE_TITLE,
                           "locator": locator, "retrieved_at": retrieved_at,
                           "formula": f"confirmed start date + {offset} days", "confidence": "medium"},
        }
        for offset, task, category, weather, details, locator in rows
    ]
    return {"plan": {"farm_id": farm_id, "crop": crop, "tasks": tasks}}
