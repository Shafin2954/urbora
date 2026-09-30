"""In-mix intelligibility check (PLAN_v4 §5): cut every placed voice line out of the final mix, transcribe it,
and compare with the script. Catches words masked by music or effects (the v3 'তেমনি' bug)."""
import json, subprocess, difflib, sys, os
import imageio_ffmpeg
from dotenv import dotenv_values
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor
FF = imageio_ffmpeg.get_ffmpeg_exe()
SRC = sys.argv[1] if len(sys.argv) > 1 else 'out/mix.wav'
oa = OpenAI(api_key=dotenv_values('../../.env.local')['OPENAI_API_KEY'])
TEXT = {l['id']: l['text'] for l in json.load(open('vo_lines.json'))}
norm = lambda s: ''.join(ch for ch in s if ch.isalnum())
LATIN = {'L12b', 'L21b', 'L19'}          # the transcriber writes these words in Latin letters


def check(p):
    out = f"/tmp/qa_{os.path.basename(SRC)}_{p['id']}.wav"
    subprocess.run([FF, '-y', '-loglevel', 'error', '-ss', str(p['start'] - 0.05), '-t', str(p['end'] - p['start'] + 0.15),
                    '-i', SRC, '-ac', '1', '-ar', '16000', out], check=True)
    res = []
    for _ in range(3):                    # the transcriber is noisy on short clips: score three passes, keep the median
        tr = oa.audio.transcriptions.create(model='gpt-4o-transcribe', file=open(out, 'rb'), language='bn').text
        res.append((round(difflib.SequenceMatcher(None, norm(TEXT[p['id']]), norm(tr)).ratio(), 3), tr))
    res.sort(); return p['id'], res[1][0], res[1][1]


with ThreadPoolExecutor(6) as ex:
    for lid, sc, tr in ex.map(check, json.load(open('vo_place.json'))):
        flag = '' if sc >= 0.9 or lid in LATIN else '  <-- check'
        print(f'{lid:5} {sc:.3f} {tr}{flag}')
