"""v5 voice step 4: word timestamps for every final line (whisper-1 verbose_json, word granularity), written to
vo5/final/words.json as {id: [[word, start, end], ...]} relative to the line file. Used for the word-synced cuts
and kinetic captions. The words whisper hears can be misspelt; only their timing is used, matched to the script
words by order (see timeline.word_at)."""
import json, glob, os
from dotenv import dotenv_values
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor
oa = OpenAI(api_key=dotenv_values('../../.env.local')['OPENAI_API_KEY'])


def job(p):
    r = oa.audio.transcriptions.create(model='whisper-1', file=open(p, 'rb'), response_format='verbose_json',
                                       timestamp_granularities=['word'])
    return os.path.basename(p)[:-4], [[w.word, round(w.start, 2), round(w.end, 2)] for w in r.words]


with ThreadPoolExecutor(8) as ex:
    out = dict(ex.map(job, sorted(glob.glob('vo5/final/*.wav'))))
json.dump(out, open('vo5/final/words.json', 'w'), ensure_ascii=False, indent=0)
for k, v in out.items(): print(k, v)
