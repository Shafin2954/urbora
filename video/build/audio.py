"""Soundtrack for the v4 cut (PLAN_v4.md §4–§5): voice lines through a clarity chain, placed on the timeline;
a cold music bed from the five supplied tracks, held well under the voice and carved out of its band;
sound effects that live inside their shots; loudness mastering; and a voice-to-music check per line.

Writes vo_place.json (line timings, word timings for the kinetic captions, English subtitles; read by final.py)
and out/mix.wav. Run from video/build: python3 audio.py <vo_dir> <music_dir>
"""
import json, sys, re, subprocess
import numpy as np, librosa, soundfile as sf, scipy.signal as ss
import imageio_ffmpeg
import timeline as T

FF = imageio_ffmpeg.get_ffmpeg_exe()
SR = 48000
VO_DIR, MUS = sys.argv[1], sys.argv[2]
N = int(SR * T.TOTAL)
TEXT = {l['id']: l['text'] for l in json.load(open('vo_lines.json'))}
VOICE_RMS = 10 ** (-18 / 20)      # every line's active speech sits at -18 dBFS RMS before mastering
MUSIC_RMS = 10 ** (-31 / 20)      # the bed between lines: about 13 dB under the voice
DUCK = 0.3                        # a further -10.5 dB while anyone speaks (over 20 dB under the voice)


def load(path, sr=SR):
    return librosa.load(path, sr=sr, mono=True)[0]


def rms_active(y):
    iv = librosa.effects.split(y, top_db=30)
    act = np.concatenate([y[a:b] for a, b in iv]) if len(iv) else y
    return np.sqrt(np.mean(act ** 2)) + 1e-9


# ------------------------------------------------ voice clarity chain
def peaking(f0, gain_db, q=1.0):
    A = 10 ** (gain_db / 40); w = 2 * np.pi * f0 / SR; al = np.sin(w) / (2 * q)
    b = [1 + al * A, -2 * np.cos(w), 1 - al * A]; a = [1 + al / A, -2 * np.cos(w), 1 - al / A]
    return np.array(b) / a[0], np.array(a) / a[0]


def compress(y, thr_db=-24, ratio=3.0, att=0.005, rel=0.08):
    env = np.abs(y); out = np.empty_like(env); ga, gr = np.exp(-1 / (att * SR)), np.exp(-1 / (rel * SR)); e = 0.0
    for i, v in enumerate(env):                      # simple peak follower
        e = ga * e + (1 - ga) * v if v > e else gr * e + (1 - gr) * v; out[i] = e
    thr = 10 ** (thr_db / 20)
    g = np.where(out > thr, (thr / np.maximum(out, 1e-9)) ** (1 - 1 / ratio), 1.0)
    return y * g


def chain(y):
    y = ss.lfilter(*ss.butter(2, 80, btype='high', fs=SR), y)          # rumble out
    y = ss.lfilter(*peaking(3000, 3.0, 1.0), y)                        # presence: consonants read through the music
    y = ss.lfilter(*peaking(250, -2.0, 1.2), y)                        # a little less box
    y = y / (np.abs(y).max() + 1e-9) * 0.5
    y = compress(y)
    return y / rms_active(y) * VOICE_RMS


def phone_speaker(y):
    b, a = ss.butter(4, [450, 3800], btype='band', fs=SR); return ss.lfilter(b, a, y)


def memory(y):
    y = ss.lfilter(*ss.butter(2, 3400, btype='low', fs=SR), y)
    ir = np.exp(-np.linspace(0, 6, int(0.3 * SR))) * np.random.RandomState(3).randn(int(0.3 * SR)) * 0.06
    return y + np.convolve(y, ir)[:len(y)]


# ------------------------------------------------ word timings for the kinetic captions
def word_times(y, text, start):
    words = text.split()
    ends = [i for i, w in enumerate(words) if re.search(r'[।?!,]$', w)]
    if not ends or ends[-1] != len(words) - 1: ends.append(len(words) - 1)
    groups, s0 = [], 0
    for e in ends: groups.append(list(range(s0, e + 1))); s0 = e + 1
    iv = librosa.effects.split(y, top_db=28, frame_length=1024, hop_length=256).tolist()
    merged = []
    for a, b in iv:                                  # join gaps shorter than 0.14 s
        if merged and a - merged[-1][1] < 0.14 * SR: merged[-1][1] = b
        else: merged.append([a, b])
    while len(merged) > len(groups):                 # too many pieces: close the smallest gap
        k = int(np.argmin([merged[i + 1][0] - merged[i][1] for i in range(len(merged) - 1)]))
        merged[k][1] = merged[k + 1][1]; del merged[k + 1]
    if len(merged) < len(groups):                    # too few: spread all words over the whole line
        merged = [[merged[0][0], merged[-1][1]]]; groups = [list(range(len(words)))]
    out = []
    for gi, (g, (a, b)) in enumerate(zip(groups, merged)):
        wts = np.array([len(words[i]) + 1.0 for i in g]); cum = np.concatenate([[0], np.cumsum(wts)[:-1]]) / wts.sum()
        for i, c in zip(g, cum):
            out.append([words[i], round(start + (a + c * (b - a)) / SR, 3), gi])
    return out


def place_vo():
    vo = np.zeros(N); placed = []; prev_end = 0.0
    for lid, want in T.WANT:
        y = load(f'{VO_DIR}/{lid}.wav')
        _, (i0, i1) = librosa.effects.trim(y, top_db=45)
        y = y[max(0, i0 - int(0.03 * SR)):min(len(y), i1 + int(0.12 * SR))]    # keep soft word endings (the -ক of ফলুক)
        y = chain(y)
        if lid == 'L07': y = chain(phone_speaker(y)) * 0.85
        if lid == 'L08': y = memory(y) * 0.9
        start = max(want, prev_end + 0.12)
        fade_n = int(0.02 * SR); y[:fade_n] *= np.linspace(0, 1, fade_n); y[-fade_n:] *= np.linspace(1, 0, fade_n)
        i0 = int(start * SR); vo[i0:i0 + len(y)] += y[:N - i0]
        end = start + len(y) / SR; prev_end = end
        placed.append(dict(id=lid, start=round(start, 3), end=round(end, 3), en=T.EN[lid], words=word_times(y, TEXT[lid], start)))
        if start - want > 0.25: print('shifted', lid, want, '->', round(start, 2))
    json.dump(placed, open('vo_place.json', 'w'), ensure_ascii=False, indent=1)
    return vo, placed


# ------------------------------------------------ music bed
def fade(x, fin=0.0, fout=0.0):
    x = x.copy(); n = len(x)
    if fin: k = min(n, int(fin * SR)); x[:k] *= np.linspace(0, 1, k)
    if fout: k = min(n, int(fout * SR)); x[n - k:] *= np.linspace(1, 0, k)
    return x


def music():
    bed = np.zeros(N); cache = {}
    for name, tin, t0, t1, fi, fo, lvl in T.MUSIC:
        y = cache.setdefault(name, load(f'{MUS}/{name}.mp3'))
        a = int(tin * SR); piece = y[a:a + int((t1 - t0) * SR)]
        piece = piece / (np.sqrt(np.mean(piece ** 2)) + 1e-9) * MUSIC_RMS * lvl
        piece = fade(piece, fi, fo); i = int(t0 * SR); bed[i:i + len(piece)] += piece[:N - i]
    return bed


# ------------------------------------------------ sound effects (synthesised, each inside its own shot)
rs = np.random.RandomState(7)


def env_adsr(n, a=0.005, r=0.2):
    e = np.ones(n); ka = max(1, int(a * SR)); e[:ka] = np.linspace(0, 1, ka)
    kr = min(n, int(r * SR)); e[n - kr:] *= np.linspace(1, 0, kr) ** 2
    return e


def bandnoise(d, lo, hi):
    return ss.lfilter(*ss.butter(2, [lo, hi], btype='band', fs=SR), rs.randn(int(d * SR)))


def whoosh(d=0.55, lo=300, hi=3000):
    n = int(d * SR); x = rs.randn(n); out = np.zeros(n); step = 512
    for k in range(0, n, step):
        f = lo * (hi / lo) ** (k / n); b, a = ss.butter(2, [max(50, f * 0.7), min(SR / 2 - 100, f * 1.4)], btype='band', fs=SR)
        out[k:k + step] = ss.lfilter(b, a, x[k:k + step])
    return out * np.sin(np.linspace(0, np.pi, n)) ** 1.5 * 0.5


def boom(d=0.9, f0=55):
    n = int(d * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * (f0 * t + 30 * (1 - np.exp(-t * 18)) / 18)) * np.exp(-t * 5)) * 0.9


def tick(f=2200, d=0.05):
    n = int(d * SR); t = np.arange(n) / SR; return np.sin(2 * np.pi * f * t) * np.exp(-t * 90) * 0.35


def pencil(d=0.6):
    """A pencil stroke on paper: grainy high noise with an uneven hand pressure."""
    n = int(d * SR); x = bandnoise(d, 2500, 9000)
    am = 0.6 + 0.4 * np.abs(np.sin(np.linspace(0, 9, n))) * (0.7 + 0.3 * rs.rand(n))
    return x * am * np.sin(np.linspace(0, np.pi, n)) ** 0.6 * 0.18


def flick():
    return bandnoise(0.05, 1500, 7000) * np.exp(-np.linspace(0, 8, int(0.05 * SR))) * 0.25


def thud():
    return boom(0.35, 120) * 0.5 + bandnoise(0.35, 200, 1200) * np.exp(-np.linspace(0, 20, int(0.35 * SR))) * 0.3


def thunder(d=1.6):
    """Distant thunder: low rumble only (nothing in the speech band), faded out inside the shot."""
    n = int(d * SR); x = ss.lfilter(*ss.butter(3, 160, btype='low', fs=SR), rs.randn(n))
    e = np.minimum(1, np.linspace(0, 6, n)) * np.exp(-np.linspace(0, 3.2, n))
    return x * e * 2.2


DTMF = {'1': (697, 1209), '2': (697, 1336), '3': (697, 1477), '4': (770, 1209), '5': (770, 1336), '6': (770, 1477),
        '7': (852, 1209), '8': (852, 1336), '9': (852, 1477), '*': (941, 1209), '0': (941, 1336), '#': (941, 1477)}


def dtmf(k, d=0.1):
    n = int(d * SR); t = np.arange(n) / SR; lo, hi = DTMF[k]
    return (np.sin(2 * np.pi * lo * t) + np.sin(2 * np.pi * hi * t)) * env_adsr(n, 0.003, 0.03) * 0.1


def buzz(d=0.8):
    n = int(d * SR); t = np.arange(n) / SR
    am = (np.sin(2 * np.pi * 7 * t) > -0.2).astype(float)
    return np.sign(np.sin(2 * np.pi * 150 * t)) * 0.07 * am * env_adsr(n, 0.01, 0.05)


def ding():
    n = int(0.9 * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 1318 * t) * np.exp(-t * 6) + 0.6 * np.sin(2 * np.pi * 1760 * t) * np.exp(-(t - 0.12).clip(0) * 6) * (t > 0.12)) * 0.16


def stamp():
    b = boom(0.5, 90) * 0.7; w = whoosh(0.12, 800, 3000) * 0.5; b[:len(w)] += w; return b


def sfx_track():
    s = np.zeros(N)

    def at(t, x, g=1.0, shot_end=None):
        i = int(t * SR); x = x * g
        if shot_end is not None:                     # an effect never outlives its shot
            keep = max(0, int((shot_end - t) * SR)); x = x[:keep].copy(); k = min(len(x), int(0.2 * SR))
            if k: x[-k:] *= np.linspace(1, 0, k)
        s[i:i + len(x)] += x[:N - i]
    at(0.0, boom(1.2, 45), 0.9)
    for t in (1.25, 2.5, 3.75): at(t - 0.05, whoosh(0.35, 600, 4000), 0.6); at(t, boom(0.4, 70), 0.3)
    at(4.7, whoosh(0.9, 200, 2000), 0.35)                                    # the dissolve into the dawn
    at(14.3, pencil(0.5), 0.3)                                               # S03: the "?" is drawn
    for t in (17.1, 20.4, 22.85, 23.85): at(t, tick(1800, 0.06), 1.0)
    at(27.7, pencil(1.0), 1.0, shot_end=29.1)                                # S05: the scribbled knot
    at(36.25, whoosh(0.6, 250, 3500), 0.7)                                   # S08: the road rolls up (before the voice)
    at(39.5, stamp(), 1.0)                                                   # the seal
    for k, t in T.DIAL: at(t, dtmf(k), 0.8)
    at(T.GREEN, tick(1400, 0.08), 0.9)
    for _, k, _, t in T.PRESSES: at(t, dtmf(k), 0.6); at(t + 0.35, tick(2600, 0.04), 0.4)
    at(T.NOTIFY, buzz(0.7)); at(T.NOTIFY + 0.1, ding(), 0.7)
    at(64.9, thud(), 0.8, shot_end=66.6)                                     # the one bottle set on the counter
    for i in range(10): at(66.8 + i * 0.085, flick(), 0.9)                   # S13a: calendar pages
    at(67.95, thunder(1.6), 1.0, shot_end=71.6)                              # c11: distant thunder, gone before the cut
    at(T.ALERT_IN, buzz(0.8)); at(T.ALERT_IN + 0.1, ding(), 0.8)
    for a in (0.4, 1.6, 2.8): at(71.9 + a / (12 / 9.5), pencil(0.5), 0.8)     # S14 icons drawn
    for a in (6.6, 6.9, 7.2): at(71.9 + a / (12 / 9.5), tick(1900, 0.05))
    for t in (81.55, 82.35): at(t, tick(2100, 0.05))                         # S15a: phones pop in
    for t in (85.2, 86.3, 87.4): at(t - 0.05, whoosh(0.3, 800, 5000), 0.35)
    return s


def voice_activity(vo):
    env = ss.filtfilt(*ss.butter(1, 2.5, fs=SR), np.abs(vo))          # slow release: the bed stays down between words
    return np.clip(env / (VOICE_RMS * 0.35), 0, 1)


def mix():
    vo, placed = place_vo()
    bed = music(); s = sfx_track()
    va = voice_activity(vo)
    t = np.arange(N) / SR
    lift = np.ones(N)
    lift[(t > 85.2) & (t < 88.9)] = 10 ** (5 / 20)                           # the lift: other fields, no voice
    lift[(t > 100.6)] = 10 ** (4 / 20)                                        # the closing chord after the tagline
    lift = ss.filtfilt(*ss.butter(1, 2, fs=SR), lift)
    band = ss.filtfilt(*ss.butter(2, [1000, 4000], btype='band', fs=SR), bed)
    m = (bed - 0.7 * band * va) * lift * (1 - (1 - DUCK) * va)                # carve the voice's band, then duck
    fx = s * (1 - 0.85 * va)                                               # effects step back under the voice too
    out = vo + m + fx
    # the voice-to-bed check (PLAN_v4 §4): every line should sit at least 18 dB over music and effects
    worst = []
    for p in placed:
        a, b = int(p['start'] * SR), int(p['end'] * SR)
        r = rms_active(vo[a:b]); db = lambda x: round(float(20 * np.log10(r / (np.sqrt(np.mean(x[a:b] ** 2)) + 1e-9))), 1)
        worst.append((db(m + fx), p['id'], 'music', db(m), 'fx', db(fx)))
    print('voice over bed, dB (lowest first):'); [print('  ', w) for w in sorted(worst)[:8]]
    sf.write('out/mix_raw.wav', np.stack([out, out], 1), SR)
    sf.write('out/stem_vo.wav', vo, SR); sf.write('out/stem_bed.wav', m + fx, SR)
    meas = subprocess.run([FF, '-hide_banner', '-i', 'out/mix_raw.wav', '-af', 'ebur128', '-f', 'null', '-'],
                          capture_output=True, text=True).stderr
    li = float(meas.rsplit('I:', 1)[1].split('LUFS')[0])
    subprocess.run([FF, '-y', '-loglevel', 'error', '-i', 'out/mix_raw.wav', '-af',
                    f'volume={-14 - li:.2f}dB,alimiter=limit=0.89:attack=5:release=60', '-ar', '48000', 'out/mix.wav'], check=True)
    print('lines', len(placed), 'raw loudness', li)


if __name__ == '__main__':
    mix()
