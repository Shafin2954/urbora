"""v4 timeline: the single source of timing for picture (final.py) and sound (audio.py).

Shot boundaries were fitted to the measured length of each chosen voice take (PLAN_v4.md §2).
Times are absolute seconds on the final cut.
"""

TOTAL = 104.5

# ------------------------------------------------ picture: (start, duration, source, source_in, speed)
# 'xf:A@a>B@b' is a 0.8 s dissolve from clip A (from a) into clip B (from b); the cut point is XF_AT seconds into the segment.
XF_AT, XF_LEN = 1.1, 0.8
EDL = [
    (0.00, 1.25, 'N1', 0.0, 1), (1.25, 1.25, 'N5', 0.1, 1), (2.50, 1.25, 'P1', 0.5, 1),
    (3.75, 4.35, 'xf:N6@3.0>N2@0.0', 0, 1),                               # hook storm dissolves into the dawn ridge
    (8.10, 2.60, 'c00', 2.0, 1), (10.70, 3.40, 'c01', 0.4, 1),
    (14.10, 3.00, 'mg:S03', 0, 1),
    (17.10, 3.30, 'c02', 0.2, 1), (20.40, 2.45, 'c03', 1.0, 1), (22.85, 1.00, 'c04', 1.0, 1), (23.85, 2.65, 'c05', 1.0, 1),
    (26.50, 2.60, 'mg:S05', 0, 1), (29.10, 4.00, 'mg:S06b', 0, 2.0), (33.10, 3.00, 'mg:S07', 0, 1), (36.10, 6.00, 'mg:S08', 0, 1),
    (42.10, 2.60, 'web', 0, 1), (44.70, 17.50, 'phone', 0, 1),
    (62.20, 2.20, 'c09', 0.3, 1), (64.40, 2.20, 'c10', 0.5, 1),
    (66.60, 1.30, 'mg:S13a', 0, 1), (67.90, 4.00, 'c11', 0.8, 1),
    (71.90, 9.50, 'mg:S14', 0, 12 / 9.5), (81.40, 3.80, 'mg:S15a', 0, 1),
    (85.20, 1.10, 'c12', 0.4, 1), (86.30, 1.10, 'c13', 1.0, 1), (87.40, 1.10, 'c14', 1.0, 1),
    (88.50, 3.60, 'c15', 1.5, 1), (92.10, 3.90, 'N3', 0.0, 1), (96.00, 8.50, 'mg:S17', 0, 1),
]
CUTS_PUNCH = (0.0, 1.25, 2.5, 3.75, 17.1, 20.4, 22.85, 23.85, 85.2, 86.3, 87.4)

# ------------------------------------------------ phone demo (offsets from D0)
D0 = 44.7
WEB0 = 42.1
DIAL = [(k, D0 + 0.5 + i * 0.18) for i, k in enumerate('*3700#')]
GREEN = D0 + 1.65
STEP = 1.25
PRESSES = [(scr, k, sel, D0 + 3.0 + i * STEP) for i, (scr, k, sel) in
           enumerate([('menu', '2', 1), ('crop', '2', 2), ('stage', '2', 2), ('organ', '2', 2), ('symptom', '1', 1), ('extent', '1', 1)])]
NOTIFY, SMS_ON, SMS_END = D0 + 10.2, D0 + 10.8, D0 + 14.2
CALLOUT = D0 + 14.3
ASK_HEAD = D0 + 2.2                      # the "it asks you" column heading appears

# rain alert on c11
ALERT_IN, ALERT_OUT = 68.2, 71.9

# ------------------------------------------------ voice: desired start of each take (never before the previous take ends + 0.12 s)
WANT = [('L01', 0.30), ('N01', 5.55), ('N02', 10.85), ('N03', 14.75),
        ('L05', 17.20), ('L06', 20.50), ('L07', 22.95), ('L08', 23.95), ('L09', 26.90), ('L10', 29.90), ('L11', 33.20),
        ('L12', 36.90), ('L12b', 40.00),
        ('L13', D0 + 1.9), ('L15', D0 + 10.95), ('L16', 62.40), ('L17', 68.90), ('L18', 72.40), ('L19', 81.60),
        ('L20', 89.10), ('L21a', 92.30), ('L21b', 98.30), ('L21c', 99.60)]

EN = {
    'L01': 'Last season I got fifty maunds of paddy. This season, thirty.',
    'N01': "This country's soil is fertile. This soil is our greatest gift.",
    'N02': "But the same land doesn't give paddy like it used to.",
    'N03': 'One question. Many answers.',
    'L05': "Brother, take this one. Everyone's taking it this year.",
    'L06': 'I used potash. It worked for me.',
    'L07': 'Just use this!',
    'L08': 'Father always used this.',
    'L09': 'Everyone says something different. Whose word do I take?',
    'L10': 'Just getting to the upazila agriculture office takes a whole day.',
    'L11': "You don't have to go to a bank to send money any more.",
    'L12': 'Farming advice is the same now: on the phone in your hand.',
    'L12b': 'Urbora.',
    'L13': 'Press a few buttons. Urbora asks the questions itself.',
    'L15': "Then the answer comes by SMS: what's wrong, which medicine, and exactly how much for your land.",
    'L16': 'Oh, stem borer? Then take this. This much is all you need.',
    'L17': 'The warning came before the rain. The urea was saved.',
    'L18': "It doesn't make things up. The numbers come from tested code. If it doesn't know, it says so.",
    'L19': 'Smartphone or button phone. Day or night.',
    'L20': 'Well... now I understand.',
    'L21a': "The soil is our gift. The knowledge to care for it is now in everyone's hands.",
    'L21b': 'Urbora.',
    'L21c': 'May your dreams bear fruit.',
}

# ------------------------------------------------ kinetic captions (PLAN_v4 §7). *word* = emphasis.
# (marked text, x, y, style, size). style 'foot' = on footage, 'paper' = on the kraft line art.
KIN = {
    'N01': ('এ দেশের মাটি *উর্বর।* এই মাটিই আমাদের সবচেয়ে বড় *উপহার।*', 960, 870, 'foot', 80),
    'N02': ('কিন্তু একই জমিতে এখন আর আগের মতো ধান *হয়* *না।*', 960, 870, 'foot', 76),
    'N03': ('প্রশ্ন *একটাই।* উত্তর *অনেক।*', 960, 930, 'paper', 84),
    'L09': ('একেকজন একেক কথা কয়। কার কথা *শুনমু?*', 960, 930, 'paper', 80),
    'L10': ('উপজেলা কৃষি অফিসে যাইতেই *পুরা* *দিন* লাগে।', 1450, 830, 'paper', 72),
    'L11': ('টাকা পাঠাইতে তো এখন আর *ব্যাংকে* যাইতে হয় না।', 960, 190, 'paper', 72),
    'L12': ('কৃষি পরামর্শও এখন *তেমনি,* *হাতের* *ফোনে।*', 960, 250, 'paper', 80),
    'L15': ('তারপর উত্তর আসে এসএমএস-এ। কী রোগ, কোন ওষুধ, আর আপনার জমিতে ঠিক *কতটুকু।*', 1470, 870, 'paper', 54),
    'L16': ('ও, মাজরা পোকা? তাইলে এইটা নেন। *এইটুকুই* লাগবে।', 960, 870, 'foot', 76),
    'L17': ('বৃষ্টির *আগেই* খবর আইলো। ইউরিয়াটা *বাঁচলো।*', 700, 870, 'foot', 76),
    'L18': ('বানিয়ে কিছু *বলে* *না।* হিসাব আসে *পরীক্ষিত* *কোড* থেকে। না জানলে, *সোজা* বলে দেয়।', 960, 170, 'paper', 70),
    'L19': ('*স্মার্টফোন* হোক বা *বাটন* *ফোন।* *দিন* হোক বা *রাত।*', 960, 920, 'paper', 80),
    'L20': ('যাক, এইবার *বুঝলাম।*', 960, 870, 'foot', 84),
    'L21a': ('মাটি আমাদের *উপহার।* তার যত্নের জ্ঞান, এখন *সবার* *হাতে।*', 960, 870, 'foot', 78),
}

# ------------------------------------------------ music (PLAN_v4 §4): (track, track_in, start, end, fade_in, fade_out, level)
PIANO_CHORD = 74.4          # the piano's closing notes (measured)
CHORD_AT = 100.9            # lands just after "স্বপ্ন ফলুক"
MUSIC = [
    ('piano', 0.0, 0.0, 26.6, 0.8, 0.7, 1.0),                     # land and problem
    ('tape', 0.0, 29.1, 39.6, 0.5, 0.15, 0.6),                     # the road and the bank (cut by the seal)
    ('acoustic', 0.0, 39.5, 85.4, 0.05, 0.8, 0.75),                # product and proof
    ('mountain', 70.0, 85.2, 93.0, 0.6, 1.4, 0.75),               # the lift: other fields, the child
    ('piano', PIANO_CHORD - (CHORD_AT - 92.1), 92.1, 104.5, 1.2, 1.5, 1.0),   # bookend: closing phrase, chord after the tagline
]
