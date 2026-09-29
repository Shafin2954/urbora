"""Rough cut of the Urbora Round 1 video from the edit decision list below.

Each segment is cut from a Higgsfield clip (clips/cNN.mp4), a line-art scene (out/Sxx.mp4) or a
slate for a part not built yet, conformed to 1920x1080 at 30 fps, then joined in order.
Run from video/build:  python3 assemble.py [--labels]
"""
import subprocess, sys, os
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
CLIPS = os.environ.get('CLIPS', 'clips')
LABELS = '--labels' in sys.argv
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
from PIL import Image, ImageDraw, ImageFont


def text_png(path, txt, size, box=True, full=False):
    f = ImageFont.truetype(FONT, size)
    if full:
        im = Image.new('RGBA', (1920, 1080), (13, 59, 46, 255)); d = ImageDraw.Draw(im)
        w = d.textlength(txt, font=f); d.text(((1920 - w) / 2, 520), txt, font=f, fill=(250, 245, 234, 255))
    else:
        im = Image.new('RGBA', (1920, 1080), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        w = d.textlength(txt, font=f); d.rectangle([16, 16, 40 + w, 30 + size], fill=(0, 0, 0, 140))
        d.text((28, 20), txt, font=f, fill=(255, 255, 255, 255))
    im.save(path)

# (shot, source, start, length, speed, note). speed < 1 slows the clip down with frame blending.
EDL = [
    ('S01', 'c00', 1.5, 7.0, 1.0, 'dawn'),
    ('S02', 'c01', 0.0, 7.0, 0.5, 'dry shoot, first 3.5 s only (later frames grow spots)'),
    ('S03', 'freeze:c01@3.4', 0, 3.0, 1.0, 'hold on the dry shoot with a slow digital push-in'),
    ('S04', 'c02', 0.2, 2.25, 1.0, 'shop counter'),
    ('S04', 'c03', 1.0, 2.25, 1.0, 'tea glass'),
    ('S04', 'c04', 1.0, 2.25, 1.0, 'phone video'),
    ('S04', 'c05', 1.0, 2.25, 1.0, "father's sack"),
    ('S05', 'c06', 1.0, 3.0, 1.0, 'empty field'),
    ('S06', 'mg:S06', 0, 8.0, 1.0, 'far office'),
    ('S07', 'mg:S07', 0, 3.0, 1.0, 'mobile banking'),
    ('S08', 'mg:S08', 0, 5.0, 1.0, 'name'),
    ('S09', 'c07', 0.5, 3.0, 1.0, 'keypad'),
    ('S10', 'c08', 0.0, 16.0, 0.625, 'loudspeaker plate (call replica goes on the left later)'),
    ('S11', 'slate:S11 · three phones, app simulation (next, after the website is final)', 0, 8.0, 1.0, ''),
    ('S12', 'c09', 0.2, 4.0, 1.0, 'phone on counter (SMS composited later)'),
    ('S12', 'c10', 0.5, 4.0, 1.0, 'one bottle'),
    ('S13', 'c11', 1.0, 8.0, 1.0, 'sack before the rain (alert SMS later)'),
    ('S14', 'mg:S14', 0, 12.0, 1.0, 'trust'),
    ('S15', 'c12', 0.2, 2.3, 1.0, 'potato'),
    ('S15', 'c13', 1.0, 2.35, 1.0, 'mustard'),
    ('S15', 'c14', 1.0, 2.35, 1.0, 'pond'),
    ('S16', 'c15', 1.5, 7.0, 1.0, 'Tumpa'),
    ('S17', 'mg:S17', 0, 5.0, 1.0, 'end card'),
]
CONFORM = 'scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30,setsar=1'
ENC = ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', '-preset', 'medium', '-an']


def run(args):
    subprocess.run([FF, '-y', '-loglevel', 'error', *args], check=True)


def segment(i, shot, src, ss, dur, speed, note):
    out = f'seg/{i:02d}.mp4'
    base = out if not LABELS else f'seg/{i:02d}_base.mp4'
    if src.startswith('mg:'):
        run(['-i', f'out/{src[3:]}.mp4', '-t', str(dur), '-vf', CONFORM, *ENC, base])
    elif src.startswith('freeze:'):
        clip, at = src[7:].split('@')
        run(['-ss', at, '-i', f'{CLIPS}/{clip}.mp4', '-frames:v', '1', 'seg/freeze.png'])
        n = int(dur * 30)
        zoom = f"scale=3840:-2,zoompan=z='1+0.08*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1920x1080:fps=30"
        run(['-loop', '1', '-i', 'seg/freeze.png', '-vf', zoom + ',setsar=1', '-frames:v', str(n), *ENC, base])
    elif src.startswith('slate:'):
        text_png('seg/slate.png', src[6:], 40, full=True)
        run(['-loop', '1', '-framerate', '30', '-i', 'seg/slate.png', '-t', str(dur), '-vf', 'format=yuv420p', *ENC, base])
    else:
        slow = f',setpts={1/speed}*PTS,minterpolate=fps=30:mi_mode=blend' if speed != 1 else ''
        run(['-ss', str(ss), '-t', str(dur * speed), '-i', f'{CLIPS}/{src}.mp4',
             '-vf', CONFORM + slow, '-t', str(dur), *ENC, base])
    if LABELS:
        text_png('seg/label.png', f'{shot}  {note}', 26)
        run(['-i', base, '-i', 'seg/label.png', '-filter_complex', 'overlay=0:0', *ENC, out])
    return out


def main():
    os.makedirs('seg', exist_ok=True)
    parts = [segment(i, *row) for i, row in enumerate(EDL)]
    with open('seg/list.txt', 'w') as f:
        f.writelines(f"file '{os.path.basename(p)}'\n" for p in parts)
    name = 'out/urbora_roughcut_labels.mp4' if LABELS else 'out/urbora_roughcut.mp4'
    run(['-f', 'concat', '-safe', '0', '-i', 'seg/list.txt', '-c', 'copy', name])
    total = sum(r[3] for r in EDL)
    print(name, f'{total:.2f} s planned')


if __name__ == '__main__':
    main()
