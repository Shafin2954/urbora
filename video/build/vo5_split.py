"""v5 voice step 1: split Jawat's recording (recordings/My_Voice.m4a) into speech pieces by silence and transcribe
each piece (gpt-4o-transcribe, bn). Writes vo5/pieces.json. Run from video/build."""
import json, io
import numpy as np, librosa, soundfile as sf
from dotenv import dotenv_values
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor
oa = OpenAI(api_key=dotenv_values('../../.env.local')['OPENAI_API_KEY'])
y, sr = sf.read('vo5/raw/full.wav')
iv = librosa.effects.split(y, top_db=32, frame_length=2048, hop_length=480)
m = []
for a, b in iv:
    if m and a - m[-1][1] < 0.45 * sr: m[-1][1] = b
    else: m.append([int(a), int(b)])
m = [x for x in m if x[1] - x[0] > 0.25 * sr]


def tr(ab):
    a, b = ab; buf = io.BytesIO()
    sf.write(buf, y[max(0, a - 2400):b + 4800], sr, format='WAV'); buf.seek(0)
    return oa.audio.transcriptions.create(model='gpt-4o-transcribe', file=('p.wav', buf), language='bn').text


with ThreadPoolExecutor(8) as ex:
    texts = list(ex.map(tr, m))
out = [dict(i=i, a=round(a / sr, 3), b=round(b / sr, 3), text=t) for i, ((a, b), t) in enumerate(zip(m, texts))]
json.dump(out, open('vo5/pieces.json', 'w'), ensure_ascii=False, indent=1)
for p in out: print(p['i'], p['a'], p['b'], p['text'])
