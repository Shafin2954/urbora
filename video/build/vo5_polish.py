"""v5 voice step 3: polish Jawat's lines into the final voice files vo5/final/<ID>.wav.
Narrator = his own voice through a GP-ad chain (light spectral denoise from the room tone of the recording,
80 Hz high-pass, warmth at 160 Hz, less box at 350 Hz, presence at 3.2 kHz, air at 10 kHz, gentle 2.5:1 compression).
Characters: speech-to-speech outputs from vo5/sts/ where they pass the transcription check (PLAN_v5 §5.4),
otherwise a pitch shift of his own take (see ROLE). Run from video/build."""
import json, sys, os, subprocess
import imageio_ffmpeg
import numpy as np, soundfile as sf, librosa, scipy.signal as ss, noisereduce as nr
SR = 48000
FF = imageio_ffmpeg.get_ffmpeg_exe()
raw, _ = sf.read('vo5/raw/full.wav')
NOISE = np.concatenate([raw[int(a * SR):int(b * SR)] for a, b in [(3.95, 4.95), (66.4, 69.0), (70.9, 73.2), (108.3, 110.7)]])
# id -> role. kind 'own' = his voice (optional Rubber Band pitch ratio); 'sts' = a converted file + its marks
ROLE = json.load(open('vo5/roles.json'))


def peaking(f0, g, q=1.0):
    A = 10 ** (g / 40); w = 2 * np.pi * f0 / SR; al = np.sin(w) / (2 * q)
    b = [1 + al * A, -2 * np.cos(w), 1 - al * A]; a = [1 + al / A, -2 * np.cos(w), 1 - al / A]
    return np.array(b) / a[0], np.array(a) / a[0]


def shelf_hi(f0, g):
    A = 10 ** (g / 40); w = 2 * np.pi * f0 / SR; al = np.sin(w) / 2 * np.sqrt(2)
    c = np.cos(w); sA = 2 * np.sqrt(A) * al
    b = [A * ((A + 1) + (A - 1) * c + sA), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - sA)]
    a = [(A + 1) - (A - 1) * c + sA, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - sA]
    return np.array(b) / a[0], np.array(a) / a[0]


def compress(y, thr_db=-20, ratio=2.5, att=0.008, rel=0.12):
    env = ss.lfilter([1 - np.exp(-1 / (rel * SR))], [1, -np.exp(-1 / (rel * SR))], np.abs(y))
    env = np.maximum(env, ss.lfilter([1 - np.exp(-1 / (att * SR))], [1, -np.exp(-1 / (att * SR))], np.abs(y)) * 0.8)
    thr = 10 ** (thr_db / 20)
    return y * np.where(env > thr, (thr / np.maximum(env, 1e-9)) ** (1 - 1 / ratio), 1.0)


def ad_chain(y, warmth=2.5, presence=3.0, denoise=0.5):
    if denoise: y = nr.reduce_noise(y=y, sr=SR, y_noise=NOISE, stationary=True, prop_decrease=denoise)
    y = ss.lfilter(*ss.butter(2, 80, btype='high', fs=SR), y)
    y = ss.lfilter(*peaking(160, warmth, 0.8), y)
    y = ss.lfilter(*peaking(350, -2.0, 1.2), y)
    y = ss.lfilter(*peaking(3200, presence, 0.9), y)
    y = ss.lfilter(*shelf_hi(10000, 2.0), y)
    y = compress(y / (np.abs(y).max() + 1e-9) * 0.7)
    return y / (np.abs(y).max() + 1e-9) * 0.89


def own(lid, pitch=1.0):
    src = f'vo5/src/{lid}.wav'
    if pitch == 1.0: return sf.read(src)[0]
    # Rubber Band (ffmpeg) with shifted formants: a different, lighter man, and the consonants survive
    # (librosa's phase-vocoder shift cost 0.1 in transcription similarity; this costs none, see LOG.md)
    out = f'vo5/tmp_{lid}.wav'
    subprocess.run([FF, '-y', '-loglevel', 'error', '-i', src, '-af', f'rubberband=pitch={pitch}:formant=shifted:pitchq=quality', out], check=True)
    y = sf.read(out)[0]; os.remove(out); return y


def sts(path, t0, t1):
    y, sr = sf.read(path)
    if y.ndim > 1: y = y.mean(1)
    return y[int((t0 - 0.06) * sr):int((t1 + 0.15) * sr)]


if __name__ == '__main__':
    os.makedirs('vo5/final', exist_ok=True)
    only = sys.argv[1:]
    for lid, r in ROLE.items():
        if only and lid not in only: continue
        y = own(r.get('src', lid), r.get('pitch', 1.0)) if r['kind'] == 'own' else sts(r['file'], r['t0'], r['t1'])
        y = ad_chain(y, **({'denoise': 0} if r['kind'] == 'sts' else {}), **r.get('eq', {}))   # converted voices come back clean
        sf.write(f'vo5/final/{lid}.wav', y, SR); print(lid, r['kind'], round(len(y) / SR, 2))
