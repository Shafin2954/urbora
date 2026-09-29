"""Soundtrack for the v3 cut: voice lines placed on the timeline, a three-part CC BY music bed with
ducking under the voice, synthesised sound effects, then loudness mastering.

Writes vo_place.json (line timings + English subtitles, read by final.py) and out/mix.wav.
Run from video/build: python3 audio.py <vo_dir> <music_dir>
"""
import json, sys, os, subprocess
import numpy as np, librosa, soundfile as sf
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
SR, TOTAL = 48000, 119.5
VO_DIR, MUS = sys.argv[1], sys.argv[2]
N = int(SR * TOTAL)

EN = {
    'L01': 'Last season I got fifty maunds of rice. This season, thirty.',
    'L02': "This land was my father's and grandfather's. This soil has fed us.",
    'L03': "But the same land doesn't give rice like it used to.",
    'L04': "The shoots are drying up. I can't even explain what's wrong.",
    'L05': "Brother, take this one. Everyone's taking it this year.",
    'L06': 'I used potash. It worked for me.',
    'L07': 'Just use this!',
    'L08': 'Father always used this.',
    'L09': 'Everyone says something different. Whose word do I take?',
    'L10': 'The upazila agriculture office? Getting there takes all day.',
    'L11': "You don't have to go to a bank to send money any more...",
    'L12': 'Farming advice is the same now: on the phone in your hand.',
    'L12b': 'Urbora.',
    'L13': 'Press a few buttons. Urbora asks the questions itself.',
    'L15': "Then the answer comes by SMS: what's wrong, which medicine, and exactly how much for your land.",
    'L16': 'Oh, stem borer? Then take this. This much is all you need.',
    'L17': 'The warning came before the rain. The urea was saved.',
    'L18': "It doesn't make things up. The numbers come from tested code. If it doesn't know, it says so.",
    'L19': 'Smartphone or button phone. Day or night.',
    'L20': 'Well... now I understand.',
    'L21': "The soil is our gift. The knowledge to care for it is now in everyone's hands. Urbora. May your dreams bear fruit.",
}
# desired start times; a line never starts before the previous one has finished (+0.12 s)
WANT = [('L01', 0.35), ('L02', 5.30), ('L03', 11.50), ('L04', 15.00), ('L05', 18.95), ('L06', 22.70), ('L07', 24.80),
        ('L08', 25.95), ('L09', 28.35), ('L10', 30.60), ('L11', 34.70), ('L12', 37.60), ('L12b', 40.25),
        ('L13', 47.60), ('L15', 58.40), ('L16', 66.90), ('L17', 77.80), ('L18', 82.00), ('L19', 93.70),
        ('L20', 100.00), ('L21', 106.90)]
GAIN = {'L07': 0.8, 'L08': 0.85}


def load(path, sr=SR, mono=True):
    y, _ = librosa.load(path, sr=sr, mono=mono)
    return y


def phone_speaker(y):
    """The 'video on a phone' voice: band-limited like a small speaker."""
    import scipy.signal as ss
    b, a = ss.butter(4, [450, 3800], btype='band', fs=SR)
    return ss.lfilter(b, a, y) * 1.6


def memory(y):
    """The father's line: slightly dulled with a short room tail, like a memory."""
    import scipy.signal as ss
    b, a = ss.butter(2, 3200, btype='low', fs=SR)
    y = ss.lfilter(b, a, y)
    ir = np.exp(-np.linspace(0, 6, int(0.35 * SR))) * np.random.RandomState(3).randn(int(0.35 * SR)) * 0.08
    return y + np.convolve(y, ir)[:len(y)]


def place_vo():
    vo = np.zeros(N); placed = []; prev_end = 0.0
    for lid, want in WANT:
        y = load(f'{VO_DIR}/{lid}.wav')
        y, _ = librosa.effects.trim(y, top_db=35)
        y = y / (np.abs(y).max() + 1e-9) * 0.7 * GAIN.get(lid, 1.0)
        if lid == 'L07': y = phone_speaker(y)
        if lid == 'L08': y = memory(y)
        start = max(want, prev_end + 0.12)
        i0 = int(start * SR); vo[i0:i0 + len(y)] += y[:N - i0]
        end = start + len(y) / SR; prev_end = end
        placed.append(dict(id=lid, start=round(start, 3), end=round(end, 3), en=EN[lid]))
    json.dump(placed, open('vo_place.json', 'w'), ensure_ascii=False, indent=1)
    for p in placed:
        if p['start'] - dict(WANT)[p['id']] > 0.25:
            print('shifted', p['id'], dict(WANT)[p['id']], '->', p['start'])
    return vo, placed


def seg(y, sr_in, s0, dur):
    a = int(s0 * SR); return y[a:a + int(dur * SR)]


def fade(x, fin=0.0, fout=0.0):
    x = x.copy(); n = len(x)
    if fin: k = int(fin * SR); x[:k] *= np.linspace(0, 1, k)
    if fout: k = int(fout * SR); x[n - k:] *= np.linspace(1, 0, k)
    return x


def music():
    bed = np.zeros(N)
    A = load(f'{MUS}/Vadodora.mp3'); B = load(f'{MUS}/Carpe Diem.mp3'); Cm = load(f'{MUS}/Americana.mp3')
    # A: hook to the far office (from its first downbeat)
    a = fade(seg(A, SR, 2.53, 34.4), 0.02, 0.6); bed[:len(a)] += a
    # B: from the reveal downbeat (the seal lands at 40.1 s) through proof, trust and reach
    bt = librosa.beat.beat_track(y=B[:SR * 40], sr=SR, units='time')[1]
    b0 = float(bt[np.argmin(np.abs(bt - 11.5))])
    b = fade(seg(B, SR, b0, 60.2), 0.05, 1.4); i = int(40.1 * SR); bed[i:i + len(b)] += b
    # C: the ending, timed so the track's own final chord lands on the end card
    env = librosa.feature.rms(y=Cm, frame_length=4096, hop_length=SR // 10)[0]
    last = (np.where(env > env.max() * 0.25)[0][-1]) / 10.0      # time of the final chord
    c_end_at = 118.2; c_len = 19.6
    c = fade(seg(Cm, SR, last - (c_end_at - 99.3) , c_len), 1.3, 1.2); i = int(99.3 * SR); bed[i:i + len(c)] += c[:N - i]
    return bed, dict(B_in=b0, C_final_chord=last)


# ------------------------------------------------ sound effects (synthesised)
rs = np.random.RandomState(7)


def env_adsr(n, a=0.005, r=0.2):
    e = np.ones(n); ka = max(1, int(a * SR)); e[:ka] = np.linspace(0, 1, ka)
    kr = min(n, int(r * SR)); e[n - kr:] *= np.linspace(1, 0, kr) ** 2
    return e


def whoosh(d=0.55, lo=300, hi=3000):
    import scipy.signal as ss
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


DTMF = {'1': (697, 1209), '2': (697, 1336), '3': (697, 1477), '4': (770, 1209), '5': (770, 1336), '6': (770, 1477),
        '7': (852, 1209), '8': (852, 1336), '9': (852, 1477), '*': (941, 1209), '0': (941, 1336), '#': (941, 1477)}


def dtmf(k, d=0.12):
    n = int(d * SR); t = np.arange(n) / SR; lo, hi = DTMF[k]
    return (np.sin(2 * np.pi * lo * t) + np.sin(2 * np.pi * hi * t)) * env_adsr(n, 0.003, 0.03) * 0.12


def buzz(d=0.9):
    n = int(d * SR); t = np.arange(n) / SR
    am = (np.sin(2 * np.pi * 7 * t) > -0.2).astype(float)
    return np.sign(np.sin(2 * np.pi * 150 * t)) * 0.08 * am * env_adsr(n, 0.01, 0.05)


def ding():
    n = int(0.9 * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 1318 * t) * np.exp(-t * 6) + 0.6 * np.sin(2 * np.pi * 1760 * t) * np.exp(-(t - 0.12).clip(0) * 6) * (t > 0.12)) * 0.18


def riser(d=3.6):
    import scipy.signal as ss
    n = int(d * SR); x = rs.randn(n); out = np.zeros(n); step = 1024
    for k in range(0, n, step):
        f = 200 * (6000 / 200) ** (k / n); b, a = ss.butter(2, [f * 0.8, min(SR / 2 - 100, f * 1.25)], btype='band', fs=SR)
        out[k:k + step] = ss.lfilter(b, a, x[k:k + step])
    return out * np.linspace(0, 1, n) ** 2 * 0.35


def rain(d):
    import scipy.signal as ss
    n = int(d * SR); x = rs.randn(n); b, a = ss.butter(2, [1500, 9000], btype='band', fs=SR)
    w = ss.lfilter(*ss.butter(2, 400, btype='low', fs=SR), rs.randn(n)) * 3
    return (ss.lfilter(b, a, x) * 0.12 + w * 0.15) * np.sin(np.linspace(0, np.pi, n)) ** 0.5


def stamp():
    b = boom(0.5, 90) * 0.7; w = whoosh(0.12, 800, 3000) * 0.5; b[:len(w)] += w; return b


def sfx_track():
    s = np.zeros(N)

    def at(t, x, g=1.0):
        i = int(t * SR); s[i:i + len(x)] += (x * g)[:N - i]
    at(0.0, boom(1.2, 45), 0.9)
    for t in (1.25, 2.5, 3.75): at(t - 0.05, whoosh(0.35, 600, 4000), 0.7); at(t, boom(0.4, 70), 0.5)
    at(5.0, whoosh(0.8, 200, 2500), 0.6)
    for t in (18.8, 23.0, 25.1, 26.0): at(t, tick(1800, 0.06), 1.2)
    at(28.9, boom(0.8, 50), 0.6)
    at(34.45, whoosh(0.9, 250, 3500), 0.8); at(37.9, whoosh(0.9, 250, 3500), 0.8)
    at(36.5, riser(3.6), 1.0); at(39.55, stamp(), 1.1)
    from final import DIAL, GREEN, PRESSES, NOTIFY, CALLOUT
    for k, t in DIAL: at(t, dtmf(k))
    at(GREEN, tick(1400, 0.08), 1.0)
    for _, k, _, t in PRESSES: at(t, dtmf(k)); at(t + 0.35, tick(2600, 0.04), 0.6)
    at(NOTIFY, buzz(0.9)); at(NOTIFY + 0.1, ding())
    at(CALLOUT + 0.5, boom(0.5, 110), 0.5); at(CALLOUT + 0.5, ding(), 0.6)
    at(72.5, rain(9.0), 1.0); at(72.7, boom(2.0, 38), 0.8)
    at(76.3, buzz(1.0)); at(76.4, ding(), 0.8)
    for t in (81.9, 83.1, 84.3): at(t, tick(1900, 0.05))
    for t in (88.1, 88.4, 88.7): at(t, tick(2400, 0.05))
    for t in (93.5, 94.9, 96.1, 97.3): at(t - 0.05, whoosh(0.3, 800, 5000), 0.5)
    at(112.3, ding(), 0.7)
    return s


def mix():
    vo, placed = place_vo()
    bed, info = music()
    s = sfx_track()
    # ducking: follow the voice envelope, smoothed, and pull the music down under it
    import scipy.signal as ss
    envv = np.abs(vo); b, a = ss.butter(1, 3, fs=SR); envv = ss.filtfilt(b, a, envv)
    duck = 1.0 - 0.72 * np.clip(envv / 0.05, 0, 1)
    base = np.full(N, 0.55)
    t = np.arange(N) / SR
    base[(t > 81.5) & (t < 93.5)] = 0.38          # trust: calmer bed
    base[(t > 112.8)] = 0.75                        # end card: let the music finish
    base[(t > 45.5) & (t < 57.5)] = 0.42            # keypad clicks should be heard
    m = bed * base * duck
    out = vo + m + s * 0.8
    stereo = np.stack([out, out], 1)
    sf.write('out/mix_raw.wav', stereo, SR)
    subprocess.run([FF, '-y', '-loglevel', 'error', '-i', 'out/mix_raw.wav', '-af',
                    'loudnorm=I=-14:TP=-1.0:LRA=11', '-ar', '48000', 'out/mix.wav'], check=True)
    print(json.dumps(info), 'lines', len(placed))


if __name__ == '__main__':
    mix()
