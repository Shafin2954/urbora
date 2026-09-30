"""v5 timeline: the single source of timing for picture (final.py) and sound (audio.py).

Fitted to Jawat's recorded takes (vo5/final/*.wav, PLAN_v5.md §2) and to the music: scene changes sit on the
tracks' measured hits (piano 27.44/30.43 s, AtlasAudio 43.26 s, Tunetank entry 1.55 s and 4.57 s, leberch's
closing hit 104.8 s). Word-synced cuts use whisper word times (vo5/final/words.json).
Times are absolute seconds on the final cut.
"""

TOTAL = 114.4
VO_DIR = 'vo5/final'

# ------------------------------------------------ voice: start of each line file (audio.py never moves a line earlier)
WANT = [('M1', 0.30), ('N1', 5.20), ('N2', 10.60), ('N3', 14.90),
        ('C1', 17.35), ('C2', 20.60), ('C3', 23.40), ('M4', 24.90), ('M2', 27.20), ('M3', 30.90),
        ('N4', 34.60), ('N5', 38.30), ('N6', 41.80), ('N7', 47.50), ('N8', 50.95),
        ('N9', 54.80), ('N10', 62.30), ('N11', 68.75), ('C4', 74.30), ('M5', 80.40),
        ('N12', 83.60), ('N13', 86.90), ('N14', 93.40), ('M6', 97.60), ('N15', 100.80),
        ('N16', 108.10), ('N17', 109.50)]
ROLE = {'C1': 'seller', 'C4': 'seller', 'C2': 'neighbour', 'C3': 'video', 'M4': 'memory'}

# ------------------------------------------------ picture: (start, duration, source, source_in, speed)
# 'xf:A@a>B@b' is a 0.8 s dissolve from clip A (from a) into clip B (from b); the cut point is XF_AT seconds into the segment.
# 'mg:X' plates hold their last frame when the slot is longer than the plate.
XF_AT, XF_LEN = 1.1, 0.8
EDL = [
    (0.00, 1.30, 'N1', 0.0, 1), (1.30, 1.30, 'P1', 0.5, 1), (2.60, 1.30, 'N5', 0.1, 1),   # hook: 50 মণ -> paddy -> 30 মণ
    (3.90, 4.20, 'xf:N5@1.4>N2@0.0', 0, 1),                                               # the sacks dissolve into the dawn
    (8.10, 2.30, 'c00', 2.0, 1), (10.40, 3.80, 'c01', 0.4, 1),                             # land, question 1 + beat
    (14.20, 3.00, 'mg:S03', 0, 1),                                                          # one question, four answers
    (17.20, 3.30, 'c02', 0.2, 1), (20.50, 2.80, 'c03', 1.0, 1), (23.30, 1.50, 'c04', 1.0, 1), (24.80, 2.30, 'c05', 1.0, 1),
    (27.10, 3.10, 'mg:S05', 0, 2.6 / 3.1),                                                  # piano 27.44 hit
    (30.20, 4.00, 'mg:S06b', 0, 2.0),                                                       # piano 30.43 hit
    (34.20, 4.00, 'mg:S06c', 0, 1),                                                         # every time (AtlasAudio in)
    (38.20, 3.50, 'mg:S07', 0, 1), (41.70, 5.70, 'mg:S07q', 0, 0.7),                        # bank; question 2 on the 43.26 hit
    (47.40, 4.80, 'mg:S08', 0, 1), (52.20, 2.50, 'mg:S08h', 0, 1),                          # "যায়।" (Tunetank), the seal, how it reaches you
    (54.70, 14.00, 'phone', 0, 1), (68.70, 5.40, 'smart', 0, 1),                            # button phone; smartphone
    (74.10, 2.10, 'c09', 0.3, 1), (76.20, 2.00, 'c10', 0.5, 1),                             # at the shop
    (78.20, 1.30, 'mg:S13a', 0, 1), (79.50, 4.00, 'c11', 0.8, 1),                           # ten days later, the alert
    (83.50, 3.30, 'mg:S12q', 0, 2.2 / 3.3), (86.80, 6.50, 'mg:S14b', 0, 1),                 # question 3 (leberch in), trust
    (93.30, 1.05, 'c12', 0.4, 1), (94.35, 1.00, 'c13', 1.0, 1), (95.35, 2.00, 'mg:S15a', 1.8, 1),   # smartphone / button phone / day or night
    (97.35, 3.25, 'c15', 1.5, 1), (100.60, 2.30, 'N3', 0.0, 1), (102.90, 3.00, 'mg:S16h', 0, 1),  # the child; the gift; everyone's hands
    (105.90, 8.50, 'mg:S17', 0, 1),                                                         # end card
]
CUTS_PUNCH = (0.0, 1.3, 2.6, 17.2, 20.5, 23.3, 24.8, 93.3, 94.35)

# ------------------------------------------------ button-phone demo (PLAN_v5 note 8: 0.7 s steps)
D0 = 54.7
DIAL = [(k, D0 + 2.2 + i * 0.15) for i, k in enumerate('*3700#')]      # on "একটা নাম্বার ডায়াল করুন"
GREEN = D0 + 3.2
STEP = 0.7
PRESSES = [(scr, k, sel, D0 + 3.6 + i * STEP) for i, (scr, k, sel) in
           enumerate([('menu', '2', 1), ('crop', '2', 2), ('stage', '2', 2), ('organ', '2', 2), ('symptom', '1', 1), ('extent', '1', 1)])]
NOTIFY, SMS_ON, SMS_END = D0 + 7.55, D0 + 7.95, D0 + 11.4
CALLOUT = D0 + 12.2                     # on "ঠিক কতটুকু" (N10 + 4.86 s)
ASK_HEAD = D0 + 3.3
PHONE_END = D0 + 14.0

# ------------------------------------------------ smartphone demo (smart.py; relative seconds inside the scene)
S0 = 68.7
SMART_END = 74.1

# rain alert on c11
ALERT_IN, ALERT_OUT = 79.8, 83.5

EN = {
    'M1': 'Last time I got fifty maunds of paddy. This time... only thirty.',
    'N1': "This country's soil is fertile. This soil is our greatest gift.",
    'N2': 'So why is the same land giving less?',
    'N3': 'One question. Many answers.',
    'C1': "Brother, take this one. Everyone's taking it this year.",
    'C2': 'I used potash. It worked.',
    'C3': 'Just use this!',
    'M4': 'Father always used this.',
    'M2': 'Everyone says something different. Whose word do I take?',
    'M3': 'Going to the agriculture office takes a whole day.',
    'N4': "And you can't go there every time there's a problem.",
    'N5': "Yet you don't need a bank to send money any more. It's done on the phone.",
    'N6': "So if banking works without a bank, why can't farming advice come on the phone too?",
    'N7': 'It can. Farming advice, now on the phone in your hand.',
    'N8': 'Urbora.',
    'N9': 'It works on a button phone. Dial a number, press a few buttons.',
    'N10': 'The answer comes by SMS: what disease, which medicine, and exactly how much for your land.',
    'N11': 'On a smartphone? Type or speak your question, and the answer comes right away.',
    'C4': 'Oh, stem borer? Then take this. This much is all you need.',
    'M5': 'The warning came before the rain. The urea was saved.',
    'N12': 'But why should you trust this advice?',
    'N13': "Every answer comes from government data and verified sources. And when it doesn't know, it says so.",
    'N14': 'Smartphone or button phone. Day or night.',
    'M6': 'Well, now I know what to do.',
    'N15': "The soil is our gift. The knowledge to care for it is now in everyone's hands.",
    'N16': 'Urbora.',
    'N17': 'May your dreams bear fruit.',
}

# ------------------------------------------------ kinetic captions on the emphasis lines. *word* = emphasis.
# The words are what Jawat actually said (his own phrasing where it differs from the sheet).
# (marked text, x, y, style, size). style 'foot' = on footage, 'paper' = on the kraft line art.
KIN = {
    'N1': ('এ দেশের মাটি *উর্বর।* এই মাটিই আমাদের সবচেয়ে বড় *উপহার।*', 960, 870, 'foot', 80),
    'N2': ('তাহলে একই জমিতে ফলন *কমছে* *কেন?*', 960, 870, 'foot', 84),
    'N3': ('প্রশ্ন *একটাই।* উত্তর *অনেক।*', 960, 930, 'paper', 84),
    'M2': ('একেকজন একেক কথা বলে। কার কথা *শুনবো?*', 960, 930, 'paper', 80),
    'M3': ('কৃষি অফিসে যেতে গেলে *পুরো* *একটা* *দিন* শেষ।', 1450, 850, 'paper', 64),
    'N4': ('আর *প্রতিবার* সমস্যা হলে তো যাওয়াও *সম্ভব* *না।*', 960, 960, 'paper', 70),
    'N5': ('অথচ টাকা পাঠাতে এখন আর *ব্যাংকে* যেতে হয় না। *ফোনেই* হয়ে যায়।', 960, 190, 'paper', 66),
    'N6': ('তাহলে ব্যাংকে না গিয়েই যেমন কাজ হয়, *কৃষির* *পরামর্শও* কি তেমনি *ফোনে* পাওয়া যায় না?', 960, 140, 'paper', 64),
    'C4': ('ও, মাজরা পোকা? তাহলে এটা নেন। *এইটুকুই* লাগবে।', 960, 870, 'foot', 76),
    'M5': ('বৃষ্টির *আগেই* খবর পেলাম। ইউরিয়াটা *বেঁচে* *গেল।*', 700, 870, 'foot', 76),
    'N12': ('কিন্তু এই পরামর্শে *ভরসা* করবেন *কেন?*', 960, 900, 'paper', 84),
    'N14': ('*স্মার্টফোন* হোক বা *বাটন* *ফোন।* *দিন* হোক বা *রাত।*', 960, 920, 'mixed', 80),
    'M6': ('যাক, এবার *বুঝলাম* কী করতে হবে।', 960, 870, 'foot', 80),
    'N15': ('মাটি আমাদের *উপহার।* তার যত্নের জ্ঞান, এখন *সবার* *হাতে।*', 960, 900, 'mixed', 76),
}

# ------------------------------------------------ music (PLAN_v5 §4): (track, track_in, start, end, fade_in, fade_out, level)
# Levels are relative: 1.0 puts the track's RMS at the bed level (audio.py). Cross-track changes are 0.8-1.2 s blends,
# except at a reveal ("যায়।"), where Tunetank's entry lands on the word.
MUSIC = [
    ('paulyudin-emotional-piano', 0.23, 0.0, 35.0, 0.6, 1.2, 1.0),         # hook, land, problem: its 27.44/30.43 hits on S05/S06b
    ('atlasaudio-documentary', 35.76, 34.2, 47.6, 1.0, 0.5, 1.0),          # far office, bank, question 2: 43.26 hit on S07q
    ('tunetank-hopeful-cinematic', 0.0, 45.95, 84.6, 0.2, 1.2, 0.95),     # entry (1.55) on "যায়।", 4.57 on the seal
    ('leberch-inspiring-piano-trailer', 77.5, 83.4, TOTAL, 0.8, 3.0, 1.0),  # question 3 to the end; 104.8 hit after "স্বপ্ন ফলুক"
]
# where the music may rise to full level (no voice): (start, end)
MUSIC_UP = [(3.9, 5.1), (13.0, 14.8), (46.1, 47.4), (51.2, 54.7), (59.4, 62.2), (72.9, 74.2), (77.7, 80.3),
            (92.9, 93.3), (96.4, 97.5), (104.2, 108.0), (110.5, TOTAL)]
