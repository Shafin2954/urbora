"""The smartphone demo (PLAN_v5 §2 scene 14): real website captures (web/check, web/chat_rain) shown inside the
smartphone product photo (assets/smart.png, chroma-green screen). smart_scene(t, t0) draws the frame at time t
for a scene starting at t0. Timings inside the scene are relative (SEG)."""
import glob, os
from functools import lru_cache
import numpy as np
from PIL import Image, ImageFilter, ImageDraw

W, H = 1920, 1080
S = 1.55                                   # photo scale: the phone is about 1000 px tall on screen
OX, OY = -586, -32                         # photo offset: the phone sits in the left third


@lru_cache(1)
def base():
    im = Image.open('assets/smart.png').convert('RGB')
    im = im.resize((int(im.width * S), int(im.height * S)), Image.LANCZOS)
    a = np.asarray(im).astype(int)
    g = (a[:, :, 1] > 150) & (a[:, :, 0] < 140) & (a[:, :, 2] < 140) & (a[:, :, 1] - a[:, :, 0] > 60)
    mask = Image.fromarray((g * 255).astype('uint8')).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1))
    ys, xs = np.where(g)
    box = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    canvas = Image.new('RGB', (W, H), (235, 217, 180)); canvas.paste(im, (OX, OY))
    m = Image.new('L', (W, H), 0); m.paste(mask, (OX, OY))
    return canvas, m, (box[0] + OX, box[1] + OY, box[2] + OX, box[3] + OY)


@lru_cache(64)
def page(path, scroll=0.0):
    """A website capture fitted to the phone screen (width-fit, top-aligned, optional scroll 0..1)."""
    _, _, (x0, y0, x1, y1) = base()
    sw, sh = x1 - x0, y1 - y0
    im = Image.open(path).convert('RGB'); k = sw / im.width
    im = im.resize((sw, max(sh, int(im.height * k))), Image.LANCZOS)
    top = int((im.height - sh) * scroll)
    scr = Image.new('RGB', (sw, sh), (247, 242, 232)); scr.paste(im.crop((0, top, sw, top + sh)), (0, 0))
    return scr


CHECK = sorted(glob.glob('web/check/0*.png'))
RESULT = 'web/check/91.png'
CHAT = sorted(glob.glob('web/chat_rain/*.png'))
# relative timeline (s): crop check taps, the result card, then the chat
SEG = dict(whip=0.25, check0=0.25, step=0.2, result=1.75, chat0=2.55, chat1=4.3, end=4.6)


def screen_at(r):
    if r < SEG['result']:
        i = min(len(CHECK) - 1, max(0, int((r - SEG['check0']) / SEG['step'])))
        return page(CHECK[i]), 'check'
    if r < SEG['chat0']:
        return page(RESULT), 'result'
    f = min(1.0, (r - SEG['chat0']) / (SEG['chat1'] - SEG['chat0']))
    i = min(len(CHAT) - 1, int(f ** 0.8 * (len(CHAT) - 1)))
    return page(CHAT[i]), 'chat'


def smart_scene(t, t0):
    r = t - t0
    canvas, m, (x0, y0, x1, y1) = base()
    fr = canvas.copy()
    scr, kind = screen_at(r)
    layer = Image.new('RGB', (W, H)); layer.paste(scr, (x0, y0))
    fr.paste(layer, (0, 0), m)
    if r < SEG['whip']:                                          # whip-pan in from the right
        k = 1 - r / SEG['whip']; dx = int(k * 700)
        fr = fr.transform((W, H), Image.AFFINE, (1, 0, -dx, 0, 1, 0), fillcolor=(235, 217, 180))
        fr = fr.filter(ImageFilter.BoxBlur(int(6 + 30 * k)))
    return fr.convert('RGBA'), kind
