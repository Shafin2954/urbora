"""v5 voice step 2: cut each script line out of Jawat's recording (pieces found by vo5_split.py), save it as
vo5/src/<ID>.wav, and score it against the script (gpt-4o-transcribe, bn, median of 3 passes).
The recording has each line once, with spoken role labels in between ("Mahmud", "Shopkeeper"...);
only the two taglines were said twice, so those two get a real take choice. Run from video/build."""
import json, io, difflib, sys
import numpy as np, soundfile as sf
from dotenv import dotenv_values
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor
oa = OpenAI(api_key=dotenv_values('../../.env.local')['OPENAI_API_KEY'])
SCRIPT = json.load(open('vo5/script.json'))
# line id -> [(start, end)] seconds in recordings/My_Voice.m4a (several spans are joined with their own pauses)
SPANS = {
    'N1': [(5.03, 8.70)], 'N2': [(9.24, 11.57)], 'N3': [(12.42, 13.71)], 'N4': [(14.16, 16.45)],
    'N5': [(17.10, 20.27)], 'N6': [(21.04, 25.11)], 'N7': [(25.93, 28.30)], 'N8': [(28.68, 29.15)],
    'N9': [(29.80, 34.16)], 'N10': [(34.67, 40.07)], 'N11': [(40.89, 44.87)], 'N12': [(45.76, 47.91)],
    'N13': [(49.12, 54.90)], 'N14': [(56.07, 58.89)], 'N15': [(60.34, 63.51)],
    'N16a': [(64.12, 64.57)], 'N17a': [(65.50, 66.25)], 'N16b': [(69.13, 69.60)], 'N17b': [(70.06, 70.76)],
    'M1': [(75.46, 78.88)], 'M2': [(80.13, 82.93)], 'M3': [(84.50, 86.59)], 'M4': [(88.30, 90.21)],
    'M5': [(92.15, 94.67)], 'M6': [(95.51, 97.74)],
    'C1': [(100.38, 103.00)], 'C2': [(105.85, 108.17)], 'C3': [(112.74, 113.71)], 'C4': [(117.42, 120.37)],
}
norm = lambda s: ''.join(ch for ch in s if ch.isalnum())
y, sr = sf.read('vo5/raw/full.wav')


def cut(spans):
    return y[int((spans[0][0] - 0.06) * sr):int((spans[-1][1] + 0.15) * sr)]


def score(path, text, n=3):
    res = []
    for _ in range(n):
        t = oa.audio.transcriptions.create(model='gpt-4o-transcribe', file=open(path, 'rb'), language='bn').text
        res.append((round(difflib.SequenceMatcher(None, norm(text), norm(t)).ratio(), 3), t))
    res.sort(); return res[len(res) // 2]


def job(lid):
    path = f'vo5/src/{lid}.wav'
    sf.write(path, cut(SPANS[lid]), sr)
    return lid, *score(path, SCRIPT[lid.rstrip('ab') if lid[-1] in 'ab' else lid])


if __name__ == '__main__':
    import os; os.makedirs('vo5/src', exist_ok=True)
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(job, SPANS))
    json.dump({l: dict(score=s, heard=t) for l, s, t in res}, open('vo5/src/scores.json', 'w'), ensure_ascii=False, indent=1)
    for l, s, t in res: print(f'{l:5} {s:.3f} {t}')
