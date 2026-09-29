"""Generate every voice-over line, up to 3 takes each, keeping the take closest to its target.
All voices are Sarvam Bulbul v3 speakers (native Bangla). OpenAI 'ash' was tried for the narrator and dropped: speech-to-text heard one line as Urdu."""
import json, sys, os
from concurrent.futures import ThreadPoolExecutor
import voice_loop as V
OUT = V.OUT
NARR = ("Voice: a warm, deep Bangladeshi male narrator for a Grameenphone TV commercial. Native Dhaka Bangla pronunciation. "
        "Tone: intimate, smiling, sincere, hopeful. Pacing: brisk and flowing like a modern TV ad, about three words per "
        "second inside each phrase, only a short breath at each full stop. Not slow, not an announcer, not dramatic.")
CAST = {'narrator': ('anand', 1.05, 0.8), 'mahmud': ('ratan', 1.2, 0.8), 'seller': ('varun', 1.2, 0.8), 'neighbour': ('kabir', 1.2, 0.8),
        'video': ('mohit', 1.3, 1.0), 'father': ('mani', 1.0, 0.7)}
TARGET = {'narrator': (2.4, 3.1), 'mahmud': (2.7, 3.4), 'seller': (2.6, 3.4), 'neighbour': (2.6, 3.4), 'video': (2.8, 3.8), 'father': (1.8, 2.6)}


def synth(line):
    s, p, t = CAST[line['who']]
    return V.tts(line['text'], s, p, t)


def score(m, who):
    lo, hi = TARGET[who]
    pace_pen = 0 if lo <= m['wps'] <= hi else min(abs(m['wps'] - lo), abs(m['wps'] - hi))
    return m['acc'] - 0.15 * pace_pen


def best(line):
    takes = []
    for k in range(3):
        b = synth(line); m = V.measure(b, line['text']); takes.append((score(m, line['who']), k, b, m))
        lo, hi = TARGET[line['who']]
        if m['acc'] >= 0.97 and lo <= m['wps'] <= hi:
            break
    sc, k, b, m = max(takes, key=lambda x: x[0])
    open(f"{OUT}/{line['id']}.wav", 'wb').write(b)
    return dict(id=line['id'], who=line['who'], takes=len(takes), pick=k, **m)


if __name__ == '__main__':
    lines = json.load(open(os.path.join(os.path.dirname(__file__), 'vo_lines.json')))
    only = os.environ.get('ONLY')
    if only:
        lines = [l for l in lines if l['id'] in only.split(',') or l['who'] in only.split(',')]
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(best, lines))
    for r in res:
        print(json.dumps(r, ensure_ascii=False))
    rep = f'{OUT}/report.json'
    old = {r['id']: r for r in (json.load(open(rep)) if os.path.exists(rep) else [])}
    old.update({r['id']: r for r in res})
    json.dump(sorted(old.values(), key=lambda r: r['id']), open(rep, 'w'), ensure_ascii=False, indent=1)
