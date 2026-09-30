"""Score speech-to-speech outputs: cut each marked line from a converted file, transcribe (median of 3),
compare with the source line's score, and report median pitch. usage: sts_check.py marks.json conv.wav [conv2.wav ...]"""
import json, sys, io, difflib
import numpy as np, soundfile as sf, librosa
from dotenv import dotenv_values
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor
oa = OpenAI(api_key=dotenv_values('../../.env.local')['OPENAI_API_KEY'])
SCRIPT = json.load(open('vo5/script.json')); SRC = json.load(open('vo5/src/scores.json'))
norm = lambda s: ''.join(ch for ch in s if ch.isalnum())
marks = None if sys.argv[1] == '-' else json.load(open(sys.argv[1]))


def f0(y, sr):
    f, v, _ = librosa.pyin(librosa.resample(y, orig_sr=sr, target_sr=16000), fmin=60, fmax=350, sr=16000); return float(np.nanmedian(f[v]))


def job(a):
    path, (lid, t0, t1) = a
    y, sr = sf.read(path); seg = y[max(0, int((t0 - 0.1) * sr)):int((t1 + 0.2) * sr)]
    buf = io.BytesIO(); sf.write(buf, seg, sr, format='WAV'); res = []
    for _ in range(3):
        buf.seek(0); t = oa.audio.transcriptions.create(model='gpt-4o-transcribe', file=('a.wav', buf.read()), language='bn').text
        res.append((round(difflib.SequenceMatcher(None, norm(SCRIPT[lid.rstrip('ab')]), norm(t)).ratio(), 3), t))
    res.sort(); return path, lid, res[1], round(f0(seg, sr), 1)


import os
jobs = ([(p, m) for p in sys.argv[2:] for m in marks] if marks else
        [(p, (os.path.basename(p)[:-4], 0.1, sf.info(p).duration - 0.2)) for p in sys.argv[2:]])
with ThreadPoolExecutor(8) as ex:
    for path, lid, (s, t), hz in ex.map(job, jobs):
        print(f"{path:28} {lid:4} {s:.3f} (src {SRC.get({'N16': 'N16b', 'N17': 'N17a'}.get(lid, lid), {}).get('score', 0):.3f}) f0 {hz} | {t}")
# whole-file mode:  sts_check.py - vo5/final/N1.wav ...   (the file name is the line id)
