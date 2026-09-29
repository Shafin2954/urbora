"""Urbora Round 1 video, v4: base plates -> frame compositor -> final MP4 (audio muxed by audio.py).

Run from video/build:
  python3 final.py base      # cut every plate to 1920x1080@30 and join them into out/base.mp4
  python3 final.py frames    # composite overlays, phone demo and subtitles into out/video.mp4
  python3 final.py still T   # write one composited frame at time T to out/still_T.png (for checks)

Every number on screen is real system output (backend/kb/triage.py, the emulator run of
2026-09-30, alerts_job.alert_sms_text with an Open-Meteo forecast). Nothing is typed by hand
except the words of the script.
"""
import os, sys, json, subprocess, math
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import imageio_ffmpeg
import timeline as T

FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS = 1920, 1080, 30
CLIPS = os.environ.get('CLIPS', 'clips')
FS = 'node_modules/@fontsource/'
FONT = {
    'serif': FS + 'noto-serif-bengali/files/noto-serif-bengali-bengali-700-normal.woff2',
    'sans': FS + 'noto-sans-bengali/files/noto-sans-bengali-bengali-600-normal.woff2',
    'sansb': FS + 'noto-sans-bengali/files/noto-sans-bengali-bengali-700-normal.woff2',
    'galada': FS + 'galada/files/galada-bengali-400-normal.woff2',
    'latin': FS + 'instrument-sans/files/instrument-sans-latin-500-normal.woff2',
    'sym': '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    'serif_l': FS + 'noto-serif-bengali/files/noto-serif-bengali-latin-700-normal.woff2',
    'sans_l': FS + 'noto-sans-bengali/files/noto-sans-bengali-latin-600-normal.woff2',
    'sansb_l': FS + 'noto-sans-bengali/files/noto-sans-bengali-latin-700-normal.woff2',
    'galada_l': FS + 'galada/files/galada-latin-400-normal.woff2',
}
LATIN_OF = {'serif': 'serif_l', 'sans': 'sans_l', 'sansb': 'sansb_l', 'galada': 'galada_l', 'latin': 'latin'}
SYMS = set('→·✉›✓')
C = dict(shyamol=(13, 59, 46), sun=(242, 162, 49), kraft=(235, 217, 180), sepia=(107, 74, 30),
         straw=(250, 245, 234), ink=(17, 32, 26), paddy=(168, 214, 92), lcd_ink=(28, 40, 30), terra=(184, 71, 42))

# ---------------------------------------------------------------- plates (base track)
# (start, duration, source, source_in, speed) lives in timeline.py, shared with audio.py.
EDL, TOTAL = T.EDL, T.TOTAL
CONFORM = 'scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30,setsar=1'
ENC = ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '16', '-preset', 'medium', '-an']


def run(args):
    subprocess.run([FF, '-y', '-loglevel', 'error', *args], check=True)


def build_base():
    os.makedirs('seg3', exist_ok=True)
    parts = []
    for i, (t0, dur, src, sin, speed) in enumerate(EDL):
        out = f'seg3/{i:02d}.mp4'; n = round(dur * FPS)
        if src in ('phone', 'web'):
            run(['-f', 'lavfi', '-i', f'color=c=0xEBD9B4:s=1920x1080:r=30', '-frames:v', str(n), *ENC, out])
        elif src.startswith('mg:'):
            vf = CONFORM + (f',setpts=PTS/{speed},fps=30' if speed != 1 else '')
            run(['-i', f'out/{src[3:]}.mp4', '-vf', vf, '-frames:v', str(n), *ENC, out])
        elif src.startswith('xf:'):
            (ca, ia), (cb, ib) = [x.split('@') for x in src[3:].split('>')]
            la = T.XF_AT + T.XF_LEN; lb = dur - T.XF_AT
            run(['-ss', ia, '-t', str(la + 0.2), '-i', f'{CLIPS}/{ca}.mp4', '-ss', ib, '-t', str(lb + 0.2), '-i', f'{CLIPS}/{cb}.mp4',
                 '-filter_complex', f'[0:v]{CONFORM}[a];[1:v]{CONFORM}[b];[a][b]xfade=transition=fade:duration={T.XF_LEN}:offset={T.XF_AT}',
                 '-frames:v', str(n), *ENC, out])
        elif src.startswith('freeze:'):
            clip, at = src[7:].split('@')
            run(['-ss', at, '-i', f'{CLIPS}/{clip}.mp4', '-frames:v', '1', 'seg3/freeze.png'])
            zoom = f"scale=3840:-2,zoompan=z='1+0.10*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1920x1080:fps=30"
            run(['-loop', '1', '-i', 'seg3/freeze.png', '-vf', zoom + ',setsar=1', '-frames:v', str(n), *ENC, out])
        else:
            slow = f',setpts={1 / speed}*PTS,minterpolate=fps=30:mi_mode=blend' if speed != 1 else ''
            run(['-ss', str(sin), '-t', str(dur * speed + 0.2), '-i', f'{CLIPS}/{src}.mp4',
                 '-vf', CONFORM + slow, '-frames:v', str(n), *ENC, out])
        parts.append(out)
    with open('seg3/list.txt', 'w') as f:
        f.writelines(f"file '{os.path.basename(p)}'\n" for p in parts)
    run(['-f', 'concat', '-safe', '0', '-i', 'seg3/list.txt', '-c', 'copy', 'out/base.mp4'])
    print('base done', sum(d for _, d, *_ in EDL))


# ---------------------------------------------------------------- helpers
def cl(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, a, b): return cl((t - a) / (b - a))
def eo(x): return 1 - (1 - x) ** 3
def back(x, c=1.7): return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


@lru_cache(None)
def font(name, size):
    return ImageFont.truetype(FONT[name], size, layout_engine=ImageFont.Layout.RAQM)


def _cls(ch):
    o = ord(ch)
    if ch in SYMS: return 'sym'
    if 0x0980 <= o <= 0x09FF or o in (0x0964, 0x0965, 0x200C, 0x200D): return 'bn'
    if ch == ' ': return None
    return 'lat'


def runs(text, fname):
    """Split text into (run, font_key) runs: Bangla, Latin (digits, punctuation) and symbols."""
    out, cur, cls = [], '', None
    for ch in text:
        c = _cls(ch)
        if c is not None and cls is not None and c != cls:
            out.append((cur, cls)); cur = ''
        if c is not None: cls = c
        cur += ch
    if cur: out.append((cur, cls or 'bn'))
    key = lambda c: 'sym' if c == 'sym' else (LATIN_OF.get(fname, fname) if c == 'lat' else fname)
    return [(r, key(c)) for r, c in out]


def fsize(key, size):
    return int(size * 0.8) if key == 'sym' else size


def text_len(text, fname, size):
    return sum(font(k, fsize(k, size)).getlength(r) for r, k in runs(text, fname))


def draw_text(d, xy, text, fname, size, fill, **kw):
    x, y = xy; asc = font(fname, size).getmetrics()[0]
    for r, k in runs(text, fname):
        f = font(k, fsize(k, size)); dy = asc - f.getmetrics()[0] + (int(size * 0.06) if k == 'sym' else 0)
        d.text((x, y + dy), r, font=f, fill=fill, **kw); x += f.getlength(r)
    return x


@lru_cache(4096)
def sprite(text, fname, size, fill, stroke=0, stroke_fill=(0, 0, 0), shadow=False):
    """Render one line of text to a tight RGBA sprite (cached)."""
    f = font(fname, size)
    asc, desc = f.getmetrics()
    pad = 12 + stroke + (10 if shadow else 0)
    im = Image.new('RGBA', (int(text_len(text, fname, size)) + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if shadow:
        draw_text(d, (pad + 3, pad + 4), text, fname, size, (0, 0, 0, 150))
    draw_text(d, (pad, pad), text, fname, size, fill + (255,) if len(fill) == 3 else fill, stroke_width=stroke, stroke_fill=stroke_fill)
    if shadow:
        blur = im.filter(ImageFilter.GaussianBlur(4)); blur.alpha_composite(im); im = blur
    return im


def paste(canvas, spr, x, y, anchor='mm', alpha=1.0, scale=1.0):
    if alpha <= 0.003: return
    if scale != 1.0:
        spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.LANCZOS)
    if alpha < 1:
        spr = spr.copy(); a = spr.getchannel('A').point(lambda v: int(v * alpha)); spr.putalpha(a)
    ax = {'l': 0, 'm': spr.width / 2, 'r': spr.width}[anchor[0]]
    ay = {'t': 0, 'm': spr.height / 2, 'b': spr.height}[anchor[1]]
    canvas.alpha_composite(spr, (int(x - ax), int(y - ay)))


def rounded(canvas, box, r, fill):
    ov = Image.new('RGBA', canvas.size, (0, 0, 0, 0)); ImageDraw.Draw(ov).rounded_rectangle(box, r, fill=fill)
    canvas.alpha_composite(ov)


def wrap(text, fname, size, maxw):
    lines = []
    for para in text.split('\n'):
        cur = ''
        for w in para.split(' '):
            t = (cur + ' ' + w).strip()
            if text_len(t, fname, size) > maxw and cur:
                lines.append(cur); cur = w
            else:
                cur = t
        lines.append(cur)
    return lines


# ---------------------------------------------------------------- the phone (real product photo, screens drawn per frame)
PH = json.load(open('assets/phone4k.json'))
PHONE = Image.open('assets/phone4k.png').convert('RGB')
SX0, SY0, SX1, SY1 = PH['screen']
LCD_BG = (163, 175, 156)

MENUS = {
    'menu': 'উর্বরা\n1. ফসল পরামর্শ\n2. ফসলের সমস্যা\n3. আমার প্ল্যান\n4. আবহাওয়া\n9. আরও',
    'crop': 'কোন ফসল?\n1. আমন ধান\n2. বোরো ধান\n3. আলু\n4. সরিষা\n5. মসুর\n0. পিছনে',
    'stage': 'গাছের অবস্থা?\n1. চারা\n2. কুশি\n3. থোড়\n4. ফুল\n5. দানা/পাকা\n0. পিছনে',
    'organ': 'কোথায় সমস্যা?\n1. পাতা\n2. কাণ্ড/খোল\n3. শিকড়\n4. শীষ/দানা\n9. আরও\n0. পিছনে',
    'symptom': 'কেমন দেখায়?\n1. ডগা শুকানো\n2. খোলে দাগ\n3. পোকা/ডিম\n4. অন্য\n0. পিছনে',
    'extent': 'কত জমিতে?\n1. অল্প\n2. অর্ধেক\n3. প্রায় সব\n0. পিছনে',
}
SMS_DIAG = ('বোরো ধান (কুশি), কাণ্ড/খোল: ডগা শুকানো।\nহতে পারে: মাজরা পোকা।\nআক্রমণ দেখা দিলে কীটনাশক দিন।\n'
            'মাত্রা: ভিরতাকো 40WG, হেক্টরে 75 গ্রাম (আপনার 2 বিঘায় মোট 20 গ্রাম)।\n'
            'স্প্রের আগে স্থানীয় কৃষি অফিসার (SAAO)-কে দেখান।\nস্প্রের সময় মাস্ক-দস্তানা পরুন।')
SMS_ALERT = ("উর্বরা সতর্কতা: 9/10 তারিখে 6 মিমি বৃষ্টির পূর্বাভাস (Open-Meteo)।\n"
             "'ইউরিয়া উপরি-প্রয়োগ' কাজটি পরের শুকনো দিনে করুন। জমির পানি নিকাশ দেখুন।")


@lru_cache(64)
def lcd(kind, arg='', sel=-1, scroll=0.0):
    """One LCD state, drawn at the phone photo's native 4K scale (616x574 screen)."""
    w, h = SX1 - SX0, SY1 - SY0
    im = Image.new('RGB', (w, h), LCD_BG); d = ImageDraw.Draw(im)
    fb, fr = font('sansb', 52), font('sans', 48)
    if kind == 'home':
        draw_text(d, (28, 24), 'উর্বরা', 'sansb', 56, C['lcd_ink'])
        draw_text(d, (28, 110), 'ডায়াল করুন *3700#', 'sans', 48, C['lcd_ink'])
        d.line([(24, h - 110), (w - 24, h - 110)], fill=(120, 132, 115), width=3)
        d.text((28, h - 96), arg, font=font('latin', 64), fill=C['lcd_ink'])
    elif kind == 'menu':
        lines = MENUS[arg].split('\n'); lh = 72 if len(lines) > 6 else 78
        for i, ln in enumerate(lines):
            y = 18 + i * lh
            if i == sel:
                d.rectangle([14, y + 2, w - 14, y + lh - 4], fill=C['lcd_ink'])
                draw_text(d, (28, y), ln, 'sans', 48, LCD_BG)
            else:
                draw_text(d, (28, y), ln, 'sansb' if i == 0 else 'sans', 52 if i == 0 else 48, C['lcd_ink'])
    elif kind == 'done':
        for i, ln in enumerate(wrap(arg, 'sans', 48, w - 56)):
            draw_text(d, (28, 30 + i * 72), ln, 'sans', 48, C['lcd_ink'])
    elif kind == 'notify':
        d.text((w / 2, h / 2 - 40), '✉', font=font('sym', 110), fill=C['lcd_ink'], anchor='mm')
        tw = text_len('নতুন SMS', 'sansb', 52); draw_text(d, (w / 2 - tw / 2, h / 2 + 40), 'নতুন SMS', 'sansb', 52, C['lcd_ink'])
    elif kind == 'sms':
        text = SMS_DIAG if arg == 'diag' else SMS_ALERT
        fsz = 40 if arg == 'diag' else 44
        lines = wrap(text, 'sans', fsz, w - 48); lh = int(fsz * 1.45)
        off = int(scroll * max(0, len(lines) * lh + 90 - h))
        draw_text(d, (24, 14 - off), 'উর্বরা', 'sansb', 44, C['lcd_ink'])
        for i, ln in enumerate(lines):
            y = 76 + i * lh - off
            hl = arg == 'diag' and ('20 গ্রাম' in ln or 'মোট' in ln)
            if hl and -lh < y < h:
                d.rectangle([12, y, w - 12, y + lh - 2], fill=(236, 205, 120))
            if -lh < y < h:
                draw_text(d, (24, y), ln, 'sans', fsz, C['lcd_ink'])
    return im


@lru_cache(8)
def phone_with(state_key):
    kind, arg, sel, scroll, key = state_key
    im = PHONE.copy(); im.paste(lcd(kind, arg, sel, scroll), (SX0, SY0))
    # a soft glass sheen so the drawn screen sits inside the photographed phone
    sheen = Image.new('RGBA', (SX1 - SX0, SY1 - SY0), (255, 255, 255, 0)); sd = ImageDraw.Draw(sheen)
    sd.polygon([(0, 0), ((SX1 - SX0) * 0.55, 0), (0, (SY1 - SY0) * 0.45)], fill=(255, 255, 255, 22))
    base = im.convert('RGBA'); base.alpha_composite(sheen, (SX0, SY0))
    if key:
        kx, ky = PH['keys'][key]; ov = Image.new('RGBA', base.size, (0, 0, 0, 0))
        ImageDraw.Draw(ov).ellipse([kx - 150, ky - 95, kx + 150, ky + 95], fill=(242, 162, 49, 120))
        base.alpha_composite(ov.filter(ImageFilter.GaussianBlur(18)))
    return base.convert('RGB')


def camera(img, cx, cy, zoom):
    """Crop the 4K phone photo around (cx, cy) so it fills 1920x1080 at the given zoom (1 = whole photo)."""
    sw, sh = img.width / zoom, img.height / zoom
    x0, y0 = cl(cx - sw / 2, 0, img.width - sw), cl(cy - sh / 2, 0, img.height - sh)
    return img.crop((int(x0), int(y0), int(x0 + sw), int(y0 + sh))).resize((W, H), Image.LANCZOS)


# phone demo timeline (absolute seconds, from timeline.py)
D0, DIAL, GREEN, PRESSES = T.D0, T.DIAL, T.GREEN, T.PRESSES
ANSWERS = [('কোন ফসল?', 'বোরো ধান'), ('গাছের অবস্থা?', 'কুশি'), ('কোথায় সমস্যা?', 'কাণ্ড/খোল'),
           ('কেমন দেখায়?', 'ডগা শুকানো'), ('কত জমিতে?', 'অল্প')]
NOTIFY, SMS_ON, SMS_END, CALLOUT = T.NOTIFY, T.SMS_ON, T.SMS_END, T.CALLOUT


def phone_state(t):
    key = None
    for k, tk in DIAL:
        if tk <= t < tk + 0.16: key = k
    if GREEN <= t < GREEN + 0.2: key = 'green'
    if t < GREEN:
        typed = ''.join(k for k, tk in DIAL if tk <= t)
        return ('home', typed, -1, 0.0, key)
    order = ['menu', 'crop', 'stage', 'organ', 'symptom', 'extent']
    cur = 'menu'
    for i, (scr, k, sel, tp) in enumerate(PRESSES):
        if t >= tp + 0.35:
            cur = order[i + 1] if i + 1 < len(order) else 'done'
        elif t >= tp:
            return ('menu', scr, sel, 0.0, k if t < tp + 0.18 else None)
    if cur == 'done':
        if t < NOTIFY:
            return ('done', 'পেয়েছি। উত্তর কয়েক মিনিটে SMS-এ আসবে।', -1, 0.0, None)
        if t < SMS_ON:
            return ('notify', '', -1, 0.0, None)
        s = round(eo(prog(t, SMS_ON + 0.6, SMS_END)) * 20) / 20
        return ('sms', 'diag', -1, s, None)
    return ('menu', cur, -1, 0.0, None)


def phone_scene(t):
    st = phone_state(t)
    img = phone_with(st)
    # camera: wide on the whole phone while dialling, then push in on the screen and top keys
    fx, fy = (SX0 + SX1) / 2, 1150
    k = eo(prog(t, GREEN - 0.1, GREEN + 0.9))
    zoom = 1.0 + 0.95 * k
    cx = 2048 + (2457 - 2048) * k            # phone to the left third so the checklist fits right
    cy = 1147 + (850 - 1147) * k             # screen plus the top row of keys
    kc = eo(prog(t, CALLOUT - 0.3, CALLOUT + 0.5))   # pull back slightly for the dose callout
    zoom -= 0.25 * kc; cx += 120 * kc
    frame = camera(img, cx, cy, zoom).convert('RGBA')
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    # label: this is the simulator on our real system
    a = prog(t, D0 + 0.2, D0 + 0.6)
    rounded(ov, (1500, 36, 1880, 100), 30, C['straw'] + (int(230 * a),))
    paste(ov, sprite('সিমুলেটর · আসল সিস্টেম', 'sansb', 32, C['terra']), 1690, 68, alpha=a)
    # right column: the questions it asked, filling in as the farmer answers
    xr = 1180
    if t >= T.ASK_HEAD and t < CALLOUT + 0.2:
        fa = prog(t, T.ASK_HEAD, T.ASK_HEAD + 0.5) * (1 - prog(t, CALLOUT - 0.4, CALLOUT))
        paste(ov, sprite('উর্বরা নিজেই জিজ্ঞেস করে', 'serif', 58, C['shyamol']), xr, 200, 'lm', alpha=fa)
        for i, (q, ans) in enumerate(ANSWERS):
            ta = PRESSES[i + 1][3] + 0.35
            qa = prog(t, PRESSES[i][3] + 0.35, PRESSES[i][3] + 0.7) * fa
            y = 330 + i * 118
            paste(ov, sprite(q, 'sans', 44, C['sepia']), xr, y, 'lm', alpha=qa)
            aa = prog(t, ta, ta + 0.25) * fa
            if aa > 0:
                paste(ov, sprite('✓ ' + ans, 'sansb', 50, C['shyamol']), xr + 360, y, 'lm', alpha=aa, scale=0.85 + 0.15 * back(prog(t, ta, ta + 0.3)))
    if t >= CALLOUT:
        k2 = prog(t, CALLOUT, CALLOUT + 0.5)
        paste(ov, sprite('মাজরা পোকা', 'serif', 64, C['shyamol']), xr, 250, 'lm', alpha=k2)
        paste(ov, sprite('ভিরতাকো 40WG · হেক্টরে 75 গ্রাম', 'sans', 40, C['sepia']), xr, 335, 'lm', alpha=k2)
        k3 = prog(t, CALLOUT + 0.5, CALLOUT + 0.9)
        rounded(ov, (xr - 30, 400, xr + 690, 640), 26, C['shyamol'] + (int(245 * k3),))
        paste(ov, sprite('আপনার 2 বিঘায়', 'sans', 52, C['straw']), xr + 10, 470, 'lm', alpha=k3)
        paste(ov, sprite('মোট 20 গ্রাম', 'serif', 104, C['sun']), xr + 10, 570, 'lm', alpha=k3, scale=0.8 + 0.2 * back(k3))
        k4 = prog(t, CALLOUT + 1.3, CALLOUT + 1.8)
        paste(ov, sprite('হিসাব: পরীক্ষিত কোড (units.scale_rate)', 'sans', 32, C['ink']), xr - 10, 700, 'lm', alpha=k4)
        paste(ov, sprite('উৎস: BioProtection Portal, ধানের পোকা দমন', 'sans', 32, C['ink']), xr - 10, 750, 'lm', alpha=k4)
    frame.alpha_composite(ov)
    return frame


def web_scene(t):
    k = prog(t, T.WEB0, D0)
    img = Image.open('assets/home2.png').convert('RGB') if not hasattr(web_scene, 'img') else web_scene.img
    web_scene.img = img
    z = 1.0 + 0.10 * eo(k)
    sw, sh = W / z, H / z
    x0, y0 = (W - sw) * 0.3, (H - sh) * 0.45
    return img.crop((int(x0), int(y0), int(x0 + sw), int(y0 + sh))).resize((W, H), Image.LANCZOS).convert('RGBA')


def alert_phone(frame, t):
    """The rain alert arrives: the same phone rises from the bottom right with the real alert text."""
    a0, a1 = T.ALERT_IN, T.ALERT_OUT
    k = eo(prog(t, a0, a0 + 0.6)) * (1 - prog(t, a1 - 0.3, a1))
    if k <= 0: return
    s = min(1.0, (t - a0 - 0.6) / 2.6) if t > a0 + 0.6 else 0.0
    st = ('sms', 'alert', -1, round(s * 10) / 10, None) if t > a0 + 0.6 else ('notify', '', -1, 0.0, None)
    img = phone_with(st).crop((1560, 60, 2540, 1300))
    sc = 0.86; img = img.resize((int(img.width * sc), int(img.height * sc)), Image.LANCZOS)
    y = int(H - img.height * k + 10)
    frame.paste(img, (W - img.width - 70, y))


# ---------------------------------------------------------------- kinetic type and subtitles
VO = json.load(open('vo_place.json')) if os.path.exists('vo_place.json') else []


def slam(ov, t, t0, t1, text, x, y, size=150, fill=None, fname='serif', anchor='mm', shadow=True):
    if not (t0 - 0.01 <= t <= t1): return
    k = prog(t, t0, t0 + 0.22); out = prog(t, t1 - 0.25, t1)
    paste(ov, sprite(text, fname, size, fill or C['straw'], shadow=shadow), x, y, anchor,
          alpha=k * (1 - out), scale=1.25 - 0.25 * eo(k))


def chip(ov, t, t0, t1, text, x, y, size=46, bg=None, fg=None, anchor='lm'):
    if not (t0 <= t <= t1): return
    k = prog(t, t0, t0 + 0.25) * (1 - prog(t, t1 - 0.2, t1))
    spr = sprite(text, 'sansb', size, fg or C['shyamol'])
    w, h = spr.width, spr.height
    ax = {'l': 0, 'm': w / 2, 'r': w}[anchor[0]]
    rounded(ov, (int(x - ax - 6), int(y - h / 2 + 8), int(x - ax + w + 6), int(y + h / 2 - 8)), 24,
            (bg or C['straw']) + (int(235 * k),))
    paste(ov, spr, x, y, anchor, alpha=k, scale=0.9 + 0.1 * back(prog(t, t0, t0 + 0.3)))


KSTYLE = {'foot': dict(fill=C['straw'], emph=C['sun'], stroke=4, line=C['sun']),
          'paper': dict(fill=C['shyamol'], emph=C['terra'], stroke=0, line=C['terra'])}


def kinetic(ov, t):
    """Bangla captions on the emphasis lines (PLAN_v4 §7): words arrive with the voice, the key word lands bigger in
    colour and gets an underline drawn under it. One phrase at a time."""
    for v in VO:
        if v['id'] not in T.KIN or not (v['start'] - 0.05 <= t <= v['end'] + 0.5): continue
        text, x, y, style, size = T.KIN[v['id']]; st = KSTYLE[style]
        marks = text.split(); words = v['words']
        cur = max([w[2] for w in words if w[1] <= t] or [0])
        idx = [i for i, w in enumerate(words) if w[2] == cur]
        out = prog(t, v['end'] + 0.2, v['end'] + 0.5)
        items = []
        for i in idx:
            em = marks[i].startswith('*'); wd = marks[i].strip('*')
            spr = sprite(wd, 'sansb', size, st['emph'] if em else st['fill'], stroke=st['stroke'], stroke_fill=(20, 20, 16))
            items.append((i, em, spr, spr.width * (1.15 if em else 1.0)))
        gap = size * 0.12; maxw = 900 if x > 1200 else 1720
        lines, cur_line, wsum = [], [], 0
        for it in items:
            if cur_line and wsum + it[3] > maxw: lines.append(cur_line); cur_line, wsum = [], 0
            cur_line.append(it); wsum += it[3] + gap
        if cur_line: lines.append(cur_line)
        for li, line in enumerate(lines):
            lw = sum(it[3] for it in line) + gap * (len(line) - 1); cx = x - lw / 2
            ly = y + (li - (len(lines) - 1)) * size * 1.25
            for i, em, spr, w in line:
                wt = words[i][1]; k = prog(t, wt - 0.04, wt + 0.14)
                if k > 0:
                    sc = (1.0 + 0.15 * back(prog(t, wt, wt + 0.3))) if em else 1.0
                    dy = 14 * (1 - eo(prog(t, wt - 0.04, wt + 0.2)))
                    paste(ov, spr, cx + w / 2, ly + dy, 'mm', alpha=k * (1 - out), scale=sc)
                    if em:
                        u = eo(prog(t, wt + 0.12, wt + 0.4)); uw = (w - 24) * u
                        if uw > 2:
                            d = ImageDraw.Draw(ov); yy = ly + size * 0.62
                            if style == 'foot': d.line([(cx + 12, yy + 2), (cx + 12 + uw, yy + 2)], fill=(20, 20, 16, int(160 * (1 - out))), width=9)
                            d.line([(cx + 12, yy), (cx + 12 + uw, yy)], fill=st['line'] + (int(255 * (1 - out)),), width=7)
                cx += w + gap


def overlays(frame, t):
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    # hook: the farmer's own figures
    slam(ov, t, 0.30, 2.45, '50 মণ', 560, 470, 190)
    if 1.28 <= t <= 2.45:
        slam(ov, t, 1.28, 2.45, '→', 960, 470, 150, fname='sym')
        slam(ov, t, 1.28, 2.45, '30 মণ', 1360, 470, 190, fill=C['sun'])
    if 0.3 <= t <= 4.6:
        a = prog(t, 0.4, 0.8) * (1 - prog(t, 4.3, 4.6))
        paste(ov, sprite('সংখ্যাগুলো দিনাজপুরের এক কৃষকের নিজের কথা', 'sans', 32, C['straw'], shadow=True), 60, 70, 'lm', alpha=a)
    for t0, t1, who, q in [(17.25, 20.45, 'দোকানি', '"এইটা নিয়া যান"'), (20.55, 22.8, 'প্রতিবেশী', '"পটাশ দিছিলাম"'),
                           (22.95, 23.85, 'ভিডিও', '"এইটা দিলেই হয়!"'), (23.95, 26.45, 'আব্বার কথা', '"আব্বা এইটাই দিত"')]:
        chip(ov, t, t0, t1, who, 70, 90, 34, bg=C['shyamol'], fg=C['sun'])
        slam(ov, t, t0 + 0.08, t1, q, 70, 185, 72, anchor='lm')
    kinetic(ov, t)
    # English subtitles from the placed voice lines
    for v in VO:
        if v['start'] <= t <= v['end'] + 0.15 and v.get('en'):
            a = prog(t, v['start'], v['start'] + 0.12) * (1 - prog(t, v['end'] + 0.05, v['end'] + 0.15))
            lines = wrap(v['en'], 'latin', 36, 1500)
            for i, ln in enumerate(lines[-2:]):
                y = 1030 - (len(lines[-2:]) - 1 - i) * 50
                spr = sprite(ln, 'latin', 36, (255, 255, 255), stroke=3, stroke_fill=(0, 0, 0))
                paste(ov, spr, 960, y, 'mb', alpha=a)
    frame.alpha_composite(ov)
    return frame


def punch(img, t):
    """A small zoom punch on the first frames of each hook cut."""
    for t0 in T.CUTS_PUNCH:
        if t0 <= t < t0 + 0.25:
            z = 1.0 + 0.06 * (1 - eo(prog(t, t0, t0 + 0.25)))
            sw, sh = W / z, H / z
            return img.crop((int((W - sw) / 2), int((H - sh) / 2), int((W + sw) / 2), int((H + sh) / 2))).resize((W, H), Image.BILINEAR)
    return img


def compose(base_rgb, t):
    if T.WEB0 <= t < D0:
        fr = web_scene(t)
    elif D0 <= t < D0 + 17.5:
        fr = phone_scene(t)
    else:
        fr = punch(Image.fromarray(base_rgb), t).convert('RGBA')
    if T.ALERT_IN <= t < T.ALERT_OUT:
        alert_phone(fr, t)
    return overlays(fr, t).convert('RGB')


def render_frames():
    n = round(TOTAL * FPS)
    dec = subprocess.Popen([FF, '-loglevel', 'error', '-i', 'out/base.mp4', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen([FF, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                            '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17',
                            '-preset', 'medium', 'out/video.mp4'], stdin=subprocess.PIPE)
    for i in range(n):
        raw = dec.stdout.read(W * H * 3)
        if len(raw) < W * H * 3: raw = last
        last = raw
        fr = compose(np.frombuffer(raw, np.uint8).reshape(H, W, 3), i / FPS)
        enc.stdin.write(fr.tobytes())
        if i % 300 == 0: print('frame', i, '/', n, flush=True)
    enc.stdin.close(); enc.wait(); dec.kill()


def still(t):
    idx = int(t * FPS)
    run(['-ss', str(t), '-i', 'out/base.mp4', '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'out/_f.raw'])
    raw = open('out/_f.raw', 'rb').read()
    compose(np.frombuffer(raw, np.uint8).reshape(H, W, 3), t).save(f'out/still_{t}.png')


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'base': build_base()
    elif cmd == 'frames': render_frames()
    elif cmd == 'still':
        for t in sys.argv[2:]: still(float(t))
