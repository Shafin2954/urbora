"""Soundtrack for the v5 cut (PLAN_v5.md §4–§5): Jawat's polished voice lines placed on the timeline, the four
Pixabay tracks cut to the edit, sound effects that live inside their shots, loudness mastering, and a
voice-over-music check per line.

Level targets (PLAN_v5 §4): music about 11 dB under the voice while anyone speaks (short-term), about 4 dB under
the voice level in the gaps; the duck opens fast and releases slowly (250 ms) so it never pumps.

Writes vo_place.json (line timings, word timings for the kinetic captions, English subtitles; read by final.py)
and out/mix.wav. Run from video/build: python audio.py
"""
import json, re, subprocess
import numpy as np, librosa, soundfile as sf, scipy.signal as ss
import imageio_ffmpeg
import timeline as T

FF = imageio_ffmpeg.get_ffmpeg_exe()
SR = 48000
N = int(SR * T.TOTAL)
MUS = '../music5'
TEXT = json.load(open('vo5/script.json', encoding='utf8'))
WHISPER = json.load(open(f'{T.VO_DIR}/words.json', encoding='utf8'))
VOICE_RMS = 10 ** (-18 / 20)      # every line's active speech sits at -18 dBFS RMS before mastering
GAP_DB, UNDER_DB = -4.0, -12.5    # music vs voice level: in the gaps / under speech


def load(path, sr=SR):
    return librosa.load(path, sr=sr, mono=True)[0]


def rms_active(y):
    iv = librosa.effects.split(y, top_db=30)
    act = np.concatenate([y[a:b] for a, b in iv]) if len(iv) else y
    return np.sqrt(np.mean(act ** 2)) + 1e-9


def db(x): return 20 * np.log10(x + 1e-12)


# ------------------------------------------------ character treatments (on top of vo5_polish.py)
def phone_speaker(y):
    b, a = ss.butter(4, [450, 3800], btype='band', fs=SR); return ss.lfilter(b, a, y)


def memory(y):
    y = ss.lfilter(*ss.butter(2, 3800, btype='low', fs=SR), y)
    ir = np.exp(-np.linspace(0, 6, int(0.3 * SR))) * np.random.RandomState(3).randn(int(0.3 * SR)) * 0.05
    return y + np.convolve(y, ir)[:len(y)]


# ------------------------------------------------ word timings for the kinetic captions
def word_times(lid, text, start, lead):
    """Script words -> absolute times. Whisper gives word spans for the line (its spelling is unreliable, its timing
    is good); script words are spread over them by their share of the characters, phrase by phrase."""
    words = text.split()
    ww = [w for w in WHISPER.get(lid, []) if w[0].strip()]
    ends = [i for i, w in enumerate(words) if re.search(r'[।?!,]$', w)]
    if not ends or ends[-1] != len(words) - 1: ends.append(len(words) - 1)
    gi = []; g = 0
    for i in range(len(words)):
        gi.append(g)
        if i in ends: g += 1
    if not ww: return [[w, round(start, 3), gi[i]] for i, w in enumerate(words)]
    # cumulative character share on both sides
    sc = np.cumsum([0] + [len(w) + 1 for w in words])[:-1] / sum(len(w) + 1 for w in words)
    wl = np.array([max(1, len(w[0])) + 1 for w in ww], float); wc = np.concatenate([[0], np.cumsum(wl)]) / wl.sum()
    wt = np.array([w[1] for w in ww] + [ww[-1][2]])
    t = np.interp(sc, wc, wt)
    return [[w, round(start + lead + float(t[i]), 3), gi[i]] for i, w in enumerate(words)]


def place_vo():
    vo = np.zeros(N); placed = []; prev_end = 0.0
    for lid, want in T.WANT:
        y = load(f'{T.VO_DIR}/{lid}.wav')
        _, (i0, i1) = librosa.effects.trim(y, top_db=45)
        a0 = max(0, i0 - int(0.08 * SR))                              # soft onsets (the কৃ of M3) survive
        y = y[a0:min(len(y), i1 + int(0.15 * SR))]                    # keep soft word endings (the -ক of ফলুক)
        y = y / rms_active(y) * VOICE_RMS
        role = T.ROLE.get(lid)
        if role == 'video': y = phone_speaker(y); y = y / rms_active(y) * VOICE_RMS * 0.85
        start = max(want, prev_end + 0.08)
        fade_n = int(0.015 * SR); y[:fade_n] *= np.linspace(0, 1, fade_n); y[-fade_n:] *= np.linspace(1, 0, fade_n)
        i0 = int(start * SR); vo[i0:i0 + len(y)] += y[:N - i0]
        end = start + len(y) / SR; prev_end = end
        text = T.KIN[lid][0].replace('*', '') if lid in T.KIN else TEXT[lid]
        lead = -(a0 / SR - 0.0)            # whisper times are relative to the untrimmed file
        placed.append(dict(id=lid, start=round(start, 3), end=round(end, 3), en=T.EN[lid], words=word_times(lid, text, start, lead)))
        if start - want > 0.15: print('shifted', lid, want, '->', round(start, 2))
    json.dump(placed, open('vo_place.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    return vo, placed


# ------------------------------------------------ music bed
def fade(x, fin=0.0, fout=0.0):
    x = x.copy(); n = len(x)
    if fin: k = min(n, int(fin * SR)); x[:k] *= np.linspace(0, 1, k)
    if fout: k = min(n, int(fout * SR)); x[n - k:] *= np.linspace(1, 0, k)
    return x


def music():
    bed = np.zeros(N); cache = {}
    gap_rms = VOICE_RMS * 10 ** (GAP_DB / 20)
    for name, tin, t0, t1, fi, fo, lvl in T.MUSIC:
        y = cache.setdefault(name, load(f'{MUS}/{name}.mp3'))
        a = int(tin * SR); piece = y[a:a + int((t1 - t0) * SR)]
        ref = np.sqrt(np.mean(piece ** 2))                             # each excerpt on its own level (leberch's climax runs 8 dB hot)
        piece = piece / ref * gap_rms * lvl
        piece = fade(piece, fi, fo); i = int(t0 * SR); bed[i:i + len(piece)] += piece[:N - i]
    return bed


def duck_gain(vo):
    """Gain for the music: 1 in the gaps, UNDER_DB-GAP_DB while the voice speaks; 150 ms look-ahead, 60 ms attack, 250 ms release."""
    hop = SR // 1000
    env = np.sqrt(ss.lfilter([1 / 30] * 30, [1], (vo[:len(vo) // hop * hop].reshape(-1, hop) ** 2).mean(1)))
    act = (env > VOICE_RMS * 0.18).astype(float)
    look = 150                                         # look-ahead (ms): the music is down before the first consonant
    act = np.maximum(act, np.concatenate([act[look:], np.zeros(look)]))
    g_low = 10 ** ((UNDER_DB - GAP_DB) / 20)
    target = 1 - (1 - g_low) * act
    out = np.empty_like(target); g = 1.0
    ka, kr = np.exp(-1 / 60), np.exp(-1 / 250)
    for i, v in enumerate(target):
        k = ka if v < g else kr; g = k * g + (1 - k) * v; out[i] = g
    return np.interp(np.arange(N), np.arange(len(out)) * hop, out), np.interp(np.arange(N), np.arange(len(act)) * hop, act)


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


def pop(f=900):
    n = int(0.12 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * f * (1 + 0.6 * np.exp(-t * 40)) * t) * np.exp(-t * 35) * 0.3


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
    for t in (1.3, 2.6): at(t - 0.05, whoosh(0.35, 600, 4000), 0.6); at(t, boom(0.4, 70), 0.3)
    at(4.6, whoosh(0.9, 200, 2000), 0.3)                                     # the dissolve into the dawn
    at(14.65, pencil(0.5), 0.25)                                             # S03: the "?" is drawn (clear of "উত্তর অনেক")
    for t in (17.2, 20.5, 23.3, 24.8): at(t, tick(1800, 0.06), 1.0)
    at(28.5, pencil(1.2), 0.9, shot_end=30.2)                                # S05: the scribbled knot
    for i in range(3): at(34.2 + i * 1.1, pop(700 + 150 * i), 0.8)           # S06c: a new problem each trip
    at(37.6, pencil(0.4), 0.9)                                               # the tally struck through
    at(38.65, whoosh(0.5, 250, 2500), 0.35)                                  # S07: the bank road rolls up
    at(43.8, pencil(0.7), 0.8)                                               # S07q: the "?" is drawn
    at(50.45, stamp(), 1.0)                                                  # S08: the seal, on Tunetank's 4.57 s hit
    for i in range(3): at(52.4 + i * 0.1, tick(2000 + 200 * i, 0.04), 0.7)   # S08h: signal
    at(53.8, whoosh(0.6, 500, 3500), 0.4)                                    # the SMS flies back
    for k, t in T.DIAL: at(t, dtmf(k), 0.8)
    at(T.GREEN, tick(1400, 0.08), 0.9)
    for _, k, _, t in T.PRESSES: at(t, dtmf(k), 0.6); at(t + 0.3, tick(2600, 0.04), 0.4)
    at(T.NOTIFY, buzz(0.7)); at(T.NOTIFY + 0.1, ding(), 0.7)
    at(T.S0 - 0.08, whoosh(0.35, 700, 5000), 0.7)                            # whip-pan to the smartphone
    at(76.7, thud(), 0.8, shot_end=78.2)                                     # the one bottle set on the counter
    for i in range(10): at(78.4 + i * 0.085, flick(), 0.9)                   # S13a: calendar pages
    at(79.55, thunder(1.6), 1.0, shot_end=83.2)                              # c11: distant thunder, gone before the cut
    at(T.ALERT_IN, buzz(0.8)); at(T.ALERT_IN + 0.1, ding(), 0.8)
    at(85.62, stamp(), 0.6)                                                  # S12q: the "?" stamps
    for a in (0.5, 1.7, 3.5): at(86.8 + a, pencil(0.5), 0.8)                 # S14b: icons drawn
    for t in (93.25, 94.3): at(t, whoosh(0.3, 800, 5000), 0.35)
    for i in range(12): at(103.05 + i * 0.12, pop(500 + 40 * i), 0.25)      # S16h: hands rise
    return s


def mix():
    vo, placed = place_vo()
    bed = music(); s = sfx_track()
    g, act = duck_gain(vo)
    band = ss.filtfilt(*ss.butter(2, [1500, 4000], btype='band', fs=SR), bed)
    m = (bed - 0.6 * band * act) * g                                    # a light carve of the consonant band, then the duck
    fx = s * (1 - 0.8 * act)                                              # effects step back under the voice too
    out = vo + m + fx
    # the check (PLAN_v5 §4): music about 11 dB under each line, never less than 8
    rows = []
    for p in placed:
        a, b = int(p['start'] * SR), int(p['end'] * SR)
        on = act[a:b] > 0.5                                             # only while the voice is actually speaking
        r = rms_active(vo[a:b]); rel = lambda x: round(float(db(r) - db(np.sqrt(np.mean(x[a:b][on] ** 2)))), 1)
        rows.append((rel(m + fx), p['id'], 'music', rel(m), 'fx', rel(fx)))
    print('voice over bed, dB (lowest first), median', np.median([r[0] for r in rows])); [print('  ', w) for w in sorted(rows)[:5]]
    gaps = [(a, b) for a, b in T.MUSIC_UP if b - a > 0.8]
    gl = [round(float(db(VOICE_RMS) - db(np.sqrt(np.mean(m[int(a * SR):int(b * SR)] ** 2)))), 1) for a, b in gaps]
    print('music under voice level in the gaps, dB:', gl)
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
