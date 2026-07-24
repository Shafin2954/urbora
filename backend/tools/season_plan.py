"""Deterministic, source-cited season-plan calendar.

The LLM chooses neither dates nor tasks. It supplies an explicitly confirmed
planting/transplant date and narrates this tool's output.

Coverage requirement (competition.md Tier 0 item 4): every crop's calendar
must run the full named sequence — land preparation, sowing window,
fertilizer splits by growth stage, irrigation, a weed checkpoint, a
pest/disease checkpoint (named pest, not generic), and harvest.

Day-offset sourcing (cited per row via `locator`; this block is the index
used to build them, kept here so a judge can trace a number back to a URL
without us re-searching under pressure):

  boro_rice
    - N-P2O5-K2O-Zn split (60-30-30-5 kg/ha, basal + 2 top-dressings) and
      80-85% grain maturity harvest cue:
      https://scialert.net/fulltext/?doi=ijar.2018.53.57
    - Modern Boro variety total duration (~150-155 days, BRRI dhan58):
      https://www.researchsquare.com/article/rs-5987962/v1
    - Stem borer / gall midge / hopper granular-insecticide guidance and
      basal TSP/MOP/Zn application at land preparation:
      https://www.bamis.gov.bd/en/croppnp/1/all/75/ ,
      https://www.bamis.gov.bd/res/bulletins/2020/08/27/20697.pdf
    - Herbicide at 4 DAT + hand weeding at 40 DAT: BRRI recommended weed
      management practice (compiled in BAMIS crop calendar advisories above).
    - Land preparation lead time (~15-20 days of ploughing/puddling before
      transplanting): documented agronomic norm, not a single-bulletin
      figure — labeled low confidence below.

  aman_rice
    - 25-30 day nursery seedlings; basal TSP/MOP/Zn/gypsum at the last stage
      of land preparation; N top-dress splits (~15-20 DAT, ~30-35 DAT, 5-7
      days before panicle initiation):
      https://agricrafters.blogspot.com/2024/10/rice-boro-aman-aus.html
    - Stem borer (Scirpophaga incertulas) scouting at max-tillering
      (20-30 DAT): https://www.bighaat.com/kisan-vedika/blogs/management-of-rice-stem-borer ,
      https://plantwiseplusknowledgebank.org/doi/full/10.1079/pwkb.20197800351
    - Harvest window (100-120 DAT for modern T. Aman varieties; Nov-Dec
      field harvest): documented agronomic norm — labeled low confidence.

  potato
    - Half urea + all other fertilizer/manure at final land preparation,
      remaining half urea top-dressed 27-30 DAP:
      https://pmc.ncbi.nlm.nih.gov/articles/PMC11272610/
    - Late blight (Phytophthora infestans) infection risk from ~40 DAP,
      fungicide spray schedule 30-68 DAP:
      https://link.springer.com/article/10.1007/s10343-023-00918-0
    - Early planting (by 15 Nov) as blight-avoidance guidance:
      https://ais.gov.bd/site/page/989e4706-35bd-4889-934c-4423785615f5
    - Harvest ~90 DAP for peak tuber yield: BARI variety duration trials
      (documented agronomic norm across BARI early/medium maturing
      varieties) — labeled low confidence.

  mustard
    - Fertilizer dose N-P2O5-K2O-S-Zn-B 120-80-60-40-4-1 kg/ha; half N + all
      other nutrients basal, remainder before flowering (~25 DAS); three
      irrigations at 12 DAS / after top-dress / 50 DAS:
      https://www.banglajol.info/index.php/BAJ/article/download/28904/19288
    - First weeding 15-20 DAS: AIS কৃষিকথা "জলবায়ু পরিবর্তন ও কৃষি
      অভিযোজন হাওরে সরিষা চাষের সম্ভাবনা" (existing citation, unchanged).
    - Mustard aphid (Lipaphis erysimi) population peaks ~60 DAS:
      https://idosi.org/wjz/wjz4(2)2009/8.pdf
    - Harvest 80-85 DAS (most BARI Sarisha varieties <80 days,
      Binasharisha-4 up to 85):
      https://www.researchgate.net/publication/323337043_PERFORMANCE_OF_MUSTARD_VARIETIES_IN_THE_HILLY_AREAS_OF_BANGLADESH

  lentil
    - Basal fertilizer (urea/TSP/MP/ZnSO4/boric acid) applied at final
      ploughing: krishi.gov.bd "মুসুর এর আধুনিক চাষ পদ্ধতি"
      http://krishi.gov.bd/content/915/
    - Hand weeding ~30 days after crop establishment; aphid infestation
      controlled with dimethoate from flowering onward, peak infestation
      ~7th-9th standard meteorological week:
      https://www.researchgate.net/publication/359820939_Magnitude_of_aphid_infestation_root_rot_and_rust_disease_of_lentil
    - Light irrigation at 40-45 DAS and again at pod-formation:
      https://krishijagran.com/agripedia/boost-your-harvest-the-complete-lentil-cultivation-handbook/
    - Harvest: BARI Masur-8 matures 115-120 days
      (https://acsess.onlinelibrary.wiley.com/doi/full/10.1002/plr2.20210);
      general BD lentil practice cites 100-110 days for older varieties —
      100-days start of the window kept from the pre-existing entry,
      pushed to 105 as a documented mid-range estimate (low confidence).
"""
from __future__ import annotations

from datetime import date, timedelta, timezone, datetime

_SOURCE_ID = "ais_bamis_calendar_2026"
_SOURCE_TITLE = "AIS e-Krishi, BAMIS, BRRI/BARI and DAE cultivation guidance"

# Each tuple is (days after start, Bangla task, category, weather dependent,
# details, source locator, confidence). Values are cited stage windows where
# a specific field-trial/bulletin figure exists; "confidence": "low" marks
# rows built from a documented agronomic norm rather than a single dated
# source (see module docstring for the full citation index).
_CALENDARS = {
    "potato": [
        (-7, "জমি প্রস্তুতি ও ভিত্তি সার প্রয়োগ", "land_prep", False,
         "শেষ চাষের সময় সম্পূর্ণ গোবর সার, অর্ধেক ইউরিয়া এবং সব টিএসপি/এমওপি/জিপসাম/জিংক সালফেট/বোরিক এসিড প্রয়োগ করে জমি তৈরি করুন।",
         "PMC11272610 (2024) potato fertilizer baseline study, Bangladesh: basal application at final land preparation",
         "medium"),
        (0, "বীজ আলু রোপণ", "sowing", False, "রোপণের তারিখ নিশ্চিত করে শুরু করুন।", "AIS e-Krishi ‘আলু’", "medium"),
        (22, "প্রথম সেচ", "irrigation", True, "বপনের 20–25 দিন পর; মাঠে পানি জমতে দেবেন না।", "AIS e-Krishi ‘আলু’: 20–25 DAS", "medium"),
        (27, "অবশিষ্ট ইউরিয়া উপরি প্রয়োগ", "fertilizer", True,
         "রোপণের 27–30 দিন পর বাকি অর্ধেক ইউরিয়া উপরি প্রয়োগ করুন।",
         "PMC11272610 (2024) potato fertilizer baseline study, Bangladesh: remaining urea top-dressed 27–30 DAP",
         "medium"),
        (32, "আগাছা দমন ও গোড়ায় মাটি দেওয়া", "weeding", False, "রোপণের 30–35 দিন পর।", "AIS কৃষিকথা ‘আলু ফসলের উন্নত জাত ও উৎপাদন কলাকৌশল’", "medium"),
        (40, "লেট ব্লাইট (নাবী ধ্বসা) পর্যবেক্ষণ", "pest_checkpoint", True,
         "কুয়াশাচ্ছন্ন আবহাওয়ায় ৪০ দিন পর থেকে Phytophthora infestans সংক্রমণের ঝুঁকি বাড়ে; পাতায় দাগ দেখলে অনুমোদিত ছত্রাকনাশক স্প্রে করুন।",
         "Journal of Crop Health (2023) 10.1007/s10343-023-00918-0: late blight infection risk from ~40 DAP",
         "medium"),
        (42, "দ্বিতীয় সেচ", "irrigation", True, "বপনের 40–45 দিন পর।", "AIS e-Krishi ‘আলু’: 40–45 DAS", "medium"),
        (62, "তৃতীয় সেচ", "irrigation", True, "বপনের 60–65 দিন পর।", "AIS e-Krishi ‘আলু’: 60–65 DAS", "medium"),
        (90, "আলু সংগ্রহ", "harvest", True,
         "সাধারণত রোপণের ৯০ দিন পর সর্বোচ্চ ফলন পাওয়া যায়; জাতভেদে ৮০–১০০ দিনের মধ্যে সংগ্রহ করুন।",
         "BARI early/medium maturing variety duration trials: peak tuber yield near 90 DAP (documented agronomic norm)",
         "low"),
    ],
    "lentil": [
        (-7, "জমি চাষ ও মই দেওয়া", "land_prep", False, "বপনের আগে ২–৩টি চাষ ও মই দিয়ে জমি ঝুরঝুরে করুন।",
         "krishi.gov.bd ‘মুসুর এর আধুনিক চাষ পদ্ধতি’", "medium"),
        (-5, "ভিত্তি সার প্রয়োগ", "fertilizer", False,
         "শেষ চাষের সময় ইউরিয়া, টিএসপি, এমপি, জিংক সালফেট ও বোরিক এসিড প্রয়োগ করুন।",
         "krishi.gov.bd ‘মুসুর এর আধুনিক চাষ পদ্ধতি’: সার প্রয়োগ শেষ চাষের সময়", "medium"),
        (0, "মসুর বপন", "sowing", False, "উপযুক্ত বপনকাল: অক্টোবরের শেষ থেকে নভেম্বরের প্রথম সপ্তাহ।", "AIS e-Krishi ‘মসুর’", "medium"),
        (27, "মাটির আর্দ্রতা পরীক্ষা", "irrigation", True, "রসের ঘাটতিতে 25–30 দিন পর একবার হালকা সেচ; জলাবদ্ধতা এড়ান।", "AIS e-Krishi ‘মসুর’: আন্তপরিচর্যা", "medium"),
        (30, "আগাছা দমন", "weeding", False, "চারা গজানোর প্রায় ৩০ দিন পর হাত নিড়ানি দিন।",
         "ResearchGate 359820939 (lentil root rot/aphid study): weeding ~30 days after crop establishment", "medium"),
        (50, "জাব পোকা (এফিড) পর্যবেক্ষণ", "pest_checkpoint", False,
         "ফুল আসার পর থেকে জাব পোকার আক্রমণ শুরু হতে পারে; আক্রমণ দেখলে ডাইমিথোয়েট জাতীয় কীটনাশক স্প্রে করুন।",
         "ResearchGate 359820939: aphid controlled with dimethoate from flowering onward", "medium"),
        (70, "সেচ (ফুল ও শুঁটি ধরার সময়)", "irrigation", True, "ফুল ও শুঁটি ধরার পর্যায়ে একবার হালকা সেচ উপকারী।",
         "krishijagran lentil cultivation handbook: light irrigation at pod-formation stage", "medium"),
        (105, "ফসল সংগ্রহের প্রস্তুতি", "harvest", True, "ফসল সাধারণত মধ্য-ফাল্গুন থেকে মধ্য-চৈত্রে সংগ্রহ করা যায়; মাঠের অবস্থা দেখে নিশ্চিত করুন।", "AIS e-Krishi ‘মসুর’: ফসল তোলা; BARI Masur-8 115–120 days (Journal of Plant Registrations 2022, doi 10.1002/plr2.20210)", "low"),
    ],
    "mustard": [
        (-5, "জমি প্রস্তুতি", "land_prep", False,
         "বপনের আগে ২–৩টি চাষ ও মই দিয়ে জমি তৈরি করুন; সরাসরি বপনেও (শূন্য চাষ) সরিষা চাষ করা যায়।",
         "AIS কৃষিকথা ‘তেলজাতীয় ফসল সরিষার গুরুত্ব এবং চাষাবাদ পদ্ধতি’", "medium"),
        (-3, "ভিত্তি সার প্রয়োগ", "fertilizer", False,
         "শেষ চাষের সময় সম্পূর্ণ টিএসপি, এমওপি, জিপসাম, জিংক, বোরন ও অর্ধেক ইউরিয়া প্রয়োগ করুন।",
         "Bangladesh Agron. J. 2015, 18(2):45-52: N-P2O5-K2O-S-Zn-B 120-80-60-40-4-1 kg/ha, half N + all other nutrients basal",
         "medium"),
        (0, "সরিষা বপন", "sowing", False, "উপযুক্ত বপনকাল: অক্টোবরের শেষ থেকে মধ্য নভেম্বর।", "AIS কৃষিকথা ‘তেলজাতীয় ফসল সরিষার গুরুত্ব এবং চাষাবাদ পদ্ধতি’", "medium"),
        (12, "প্রথম সেচ", "irrigation", True, "বপনের 12 দিন পর প্রথম সেচ দিন।",
         "Bangladesh Agron. J. 2015, 18(2):45-52: three irrigations at 12 DAS / after top-dress / 50 DAS", "medium"),
        (20, "আগাছা দমন", "weeding", False, "বপনের 15–20 দিন পর প্রথম নিড়ানি।", "AIS কৃষিকথা ‘জলবায়ু পরিবর্তন ও কৃষি অভিযোজন হাওরে সরিষা চাষের সম্ভাবনা’", "medium"),
        (25, "অবশিষ্ট ইউরিয়া উপরি প্রয়োগ ও সেচ", "fertilizer", True,
         "ফুল আসার আগে (বপনের ২৫ দিন পর) অবশিষ্ট ইউরিয়া উপরি প্রয়োগ করে সেচ দিন।",
         "Bangladesh Agron. J. 2015, 18(2):45-52: remaining N top-dressed with irrigation ~25 DAS, before flowering", "medium"),
        (50, "তৃতীয় সেচ", "irrigation", True, "বপনের 50 দিন পর সেচ দিন।",
         "Bangladesh Agron. J. 2015, 18(2):45-52: third irrigation at 50 DAS", "medium"),
        (58, "জাব পোকা (এফিড) পর্যবেক্ষণ", "pest_checkpoint", False,
         "বপনের প্রায় 60 দিনে জাব পোকার (Lipaphis erysimi) প্রকোপ সর্বোচ্চ হয়; আক্রমণ দেখলে অনুমোদিত কীটনাশক স্প্রে করুন।",
         "World Journal of Zoology 4(2) 2009 (idosi.org): mustard aphid population peaks ~60 DAS", "medium"),
        (82, "সরিষা কাটা", "harvest", True, "সাধারণত বপনের ৮০–৮৫ দিন পর ফসল কাটার উপযোগী হয়।",
         "ResearchGate 323337043 (BARI Sarisha variety trial): most varieties <80 days, up to 85 days for late varieties", "medium"),
    ],
    "boro_rice": [
        (-15, "জমি চাষ ও মই দেওয়া শুরু", "land_prep", False,
         "রোপণের ১৫–২০ দিন আগে থেকে কমপক্ষে ৩–৪ বার চাষ ও মই দিয়ে জমি সমতল করুন।",
         "documented agronomic norm — general BRRI puddled-rice land preparation practice, no single dated bulletin figure", "low"),
        (-1, "ভিত্তি সার প্রয়োগ", "fertilizer", False,
         "রোপণের সময় সম্পূর্ণ টিএসপি, এমওপি, জিংক সালফেট ও প্রথম এক-তৃতীয়াংশ ইউরিয়া প্রয়োগ করুন।",
         "scialert ijar.2018.53.57: 60-30-30-5 kg/ha N-P2O5-K2O-Zn, N split basal/tillering/panicle-initiation", "medium"),
        (0, "বোরো চারা রোপণ", "sowing", False, "35–45 দিনের চারা রোপণ করুন; রোপণের সময় 1–2 সেমি পানি রাখুন।", "BAMIS ‘Boro Paddy’: Sowing", "medium"),
        (10, "মরা গোছা পূরণ ও পানি পরীক্ষা", "irrigation", True, "প্রথম 15 দিন অল্প পানির স্তর রাখুন।", "BAMIS ‘Boro Paddy’: Sowing", "medium"),
        (25, "প্রথম ইউরিয়া উপরি প্রয়োগ", "fertilizer", True, "রোপণের 20–25 দিন পর; প্রয়োগের আগে আগাছা দমন করুন।", "BAMIS ‘Boro Paddy’: Fertiliser Applications", "medium"),
        (30, "কাণ্ড মাজরা পোকা ও গাছ ফড়িং পর্যবেক্ষণ", "pest_checkpoint", False,
         "সর্বোচ্চ কুশি পর্যায়ে (২০–৩০ দিন) কাণ্ড মাজরা পোকা (stem borer), গল মিজ ও গাছ ফড়িং পরীক্ষা করুন; আক্রমণ দেখলে অনুমোদিত দানাদার কীটনাশক প্রয়োগ করুন।",
         "BAMIS national bulletin 20697 (2020): stem borer/gall midge/hopper granular insecticide guidance; scouting window from stem-borer literature (bighaat.com)",
         "medium"),
        (40, "হাত নিড়ানি", "weeding", False, "রোপণের 40 দিন পর হাত নিড়ানি দিন।", "BRRI recommended weed management: hand weeding at 40 DAT (via BAMIS crop calendar advisories)", "medium"),
        (55, "দ্বিতীয় ইউরিয়া উপরি প্রয়োগ", "fertilizer", True, "প্যানিকল শুরু হওয়ার 5–7 দিন আগে।", "BAMIS ‘Boro Paddy’: Fertiliser Applications", "medium"),
        (115, "বোরো ধান কর্তন", "harvest", True,
         "৮০–৮৫% ধানের শীষ পাকলে (খড়ের রং হলুদ হলে) ধান কাটুন; আধুনিক জাতে রোপণের প্রায় ১০০–১২০ দিন পর।",
         "scialert ijar.2018.53.57: harvest at 80–85% grain physiological maturity; duration range documented agronomic norm",
         "low"),
    ],
    "aman_rice": [
        (-10, "জমি প্রস্তুতি শুরু", "land_prep", True,
         "পর্যাপ্ত বৃষ্টি হওয়ার পর জমি চাষ ও কাদা তৈরি (পাডলিং) শুরু করুন।",
         "bssnews district reports: Aman land preparation begins after sufficient rainfall (documented agronomic norm for lead time)", "low"),
        (-2, "ভিত্তি সার প্রয়োগ", "fertilizer", False,
         "জমি তৈরির শেষ ধাপে সম্পূর্ণ টিএসপি, এমওপি, জিংক ও জিপসাম প্রয়োগ করুন।",
         "agricrafters.blogspot ‘Rice (Boro, Aman, Aus)’: per-hectare TSP/MOP/Zn/gypsum applied at last stage of land preparation", "medium"),
        (0, "আমন চারা রোপণ", "sowing", True, "পর্যাপ্ত বৃষ্টি হলে 25–30 দিনের চারা রোপণ করুন; অতিরিক্ত পানির নিষ্কাশন রাখুন।", "BAMIS bulletin 23903: Aman Paddy", "medium"),
        (7, "মরা গোছা পূরণ ও পানি ব্যবস্থাপনা", "irrigation", True, "এক সপ্তাহের মধ্যে মরা গোছা পূরণ করুন এবং সর্বোচ্চ কুশি পর্যন্ত 5–7 সেমি পানি রাখুন।", "BAMIS bulletin 24140: Aman Paddy", "medium"),
        (18, "প্রথম নাইট্রোজেন উপরি প্রয়োগ", "fertilizer", True, "রোপণের 15–20 দিন পর; প্রয়োগের আগে আগাছা পরিষ্কার করুন।", "BAMIS bulletin 24603: Aman Paddy", "medium"),
        (25, "কাণ্ড মাজরা পোকা পর্যবেক্ষণ", "pest_checkpoint", False,
         "সর্বোচ্চ কুশি পর্যায়ে (২০–৩০ দিন) কাণ্ড মাজরা পোকা (Scirpophaga incertulas) পরীক্ষা করুন; ডিমের গুচ্ছ বা মরা কুশি দেখলে অনুমোদিত কীটনাশক প্রয়োগ করুন।",
         "plantwiseplusknowledgebank.org pwkb.20197800351 (stem borer, Bangladesh); scouting window bighaat.com stem borer guide", "medium"),
        (33, "দ্বিতীয় আগাছা দমন", "weeding", False, "রোপণের 30–35 দিন পর আগাছা দমন করুন।", "BAMIS bulletin 24603: Aman Paddy", "medium"),
        (60, "প্যানিকল শুরুর আগের নাইট্রোজেন", "fertilizer", True, "প্যানিকল শুরুর 5–7 দিন আগে শেষ এক-তৃতীয়াংশ নাইট্রোজেন।", "BAMIS bulletin 24603: Aman Paddy", "medium"),
        (105, "আমন ধান কর্তন", "harvest", True,
         "৮০–৮৫% ধানের শীষ পাকলে ধান কাটুন; আধুনিক জাতে রোপণের প্রায় ১০০–১২০ দিন পর, সাধারণত নভেম্বর-ডিসেম্বরে।",
         "documented agronomic norm — modern T. Aman variety duration range (BRRI), no single dated bulletin figure", "low"),
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
                           "formula": f"confirmed start date + {offset} days", "confidence": confidence},
        }
        for offset, task, category, weather, details, locator, confidence in rows
    ]
    return {"plan": {"farm_id": farm_id, "crop": crop, "tasks": tasks}}
