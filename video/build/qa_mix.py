"""In-mix intelligibility check (PLAN_v4 §5, v5: flagged when a line scores more than 0.05 under its source take): cut every placed voice line out of the final mix, transcribe it,
and compare with the script. Catches words masked by music or effects (the v3 'তেমনি' bug)."""
import json, subprocess, difflib, sys, os
import imageio_ffmpeg
from dotenv import dotenv_values
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor
FF = imageio_ffmpeg.get_ffmpeg_exe()
SRC = sys.argv[1] if len(sys.argv) > 1 else 'out/mix.wav'
oa = OpenAI(api_key=dotenv_values('../../.env.local')['OPENAI_API_KEY'])
TEXT = json.load(open('vo5/script.json', encoding='utf8'))
SRCS = json.load(open('vo5/src/scores.json', encoding='utf8'))
norm = lambda s: ''.join(ch for ch in s if ch.isalnum())
LATIN = {'N8', 'N16'}          # the transcriber writes these words in Latin letters


def check(p):
    os.makedirs('out/qa', exist_ok=True); out = f"out/qa/{os.path.basename(SRC)}_{p['id']}.wav"
    subprocess.run([FF, '-y', '-loglevel', 'error', '-ss', str(p['start'] - 0.2), '-t', str(p['end'] - p['start'] + 0.4),
                    '-i', SRC, '-ac', '1', '-ar', '16000', out], check=True)
    res = []
    for _ in range(3):                    # the transcriber is noisy on short clips: score three passes, keep the median
        tr = oa.audio.transcriptions.create(model='gpt-4o-transcribe', file=open(out, 'rb'), language='bn').text
        res.append((round(difflib.SequenceMatcher(None, norm(TEXT[p['id']]), norm(tr)).ratio(), 3), tr))
    res.sort(); return p['id'], res[1][0], res[1][1]


with ThreadPoolExecutor(6) as ex:
    for lid, sc, tr in ex.map(check, json.load(open('vo_place.json', encoding='utf8'))):
        src = SRCS.get({'N16': 'N16b', 'N17': 'N17a'}.get(lid, lid), {}).get('score', 0)
        flag = '' if sc >= src - 0.05 or lid in LATIN else f'  <-- check (source {src})'
        print(f'{lid:5} {sc:.3f} {tr}{flag}')
