"""Voice-matching loop: synthesise candidate voices with Sarvam Bulbul v3, then measure
pace (words/s of speech), median pitch, pitch spread and speech-to-text similarity."""
import httpx, base64, io, wave, difflib, json, sys, numpy as np, librosa
from concurrent.futures import ThreadPoolExecutor
from dotenv import dotenv_values
from openai import OpenAI
env = dotenv_values(__import__('os').path.join(__import__('os').path.dirname(__file__), '..', '..', '.env.local')); K = env['SARVAM_API_KEY']; oa = OpenAI(api_key=env['OPENAI_API_KEY'])
OUT = sys.argv[1]


def tts(text, speaker, pace=1.0, temperature=None):
    body = {'text': text, 'language_code': 'bn-IN', 'model': 'bulbul:v3', 'speaker': speaker, 'pace': pace}
    if temperature is not None:
        body['temperature'] = temperature
    r = httpx.post('https://api.sarvam.ai/text-to-speech', headers={'api-subscription-key': K}, json=body, timeout=120)
    r.raise_for_status()
    return base64.b64decode(r.json()['audios'][0])


def measure(b, text):
    w = wave.open(io.BytesIO(b)); sr = w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16) / 32768
    iv = librosa.effects.split(x, top_db=30); speech = sum(e - s for s, e in iv) / sr
    f0, v, _ = librosa.pyin(x, fmin=65, fmax=300, sr=sr); f = f0[v]
    t = oa.audio.transcriptions.create(model='gpt-4o-transcribe', file=('a.wav', b), language='bn').text
    norm = lambda s: ''.join(ch for ch in s if ch.isalnum())
    words = len(text.split())
    return dict(dur=round(len(x) / sr, 2), wps=round(words / speech, 2), f0=round(float(np.median(f)), 1),
                spread=round(float(np.std(12 * np.log2(f / np.median(f)))), 2),
                acc=round(difflib.SequenceMatcher(None, norm(text), norm(t)).ratio(), 3))


def job(c):
    b = tts(c['text'], c['speaker'], c.get('pace', 1.0), c.get('temperature'))
    name = f"{c['role']}_{c['speaker']}_p{c.get('pace',1.0)}_t{c.get('temperature')}"
    open(f'{OUT}/{name}.wav', 'wb').write(b)
    return dict(name=name, **measure(b, c['text']))


if __name__ == '__main__':
    cands = json.loads(sys.stdin.read())
    with ThreadPoolExecutor(6) as ex:
        for r in ex.map(job, cands):
            print(json.dumps(r, ensure_ascii=False), flush=True)
