#!/usr/bin/env python3
"""Redraws the gold radio-tower icon:  icon.ico, icon.png and icon_small.png in the project folder.

    python3 tools/make_icon.py          (needs Pillow:  pip install pillow)
"""
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD_TOP, GOLD_BOT, EDGE, INK = (255, 226, 110), (222, 158, 0), (110, 72, 0), (24, 28, 40)


def render(size):
    ss = 4
    S = size * ss
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    grad = Image.new('RGBA', (S, S))
    gd = ImageDraw.Draw(grad)
    for y in range(S):
        t = y / (S - 1)
        gd.line([(0, y), (S, y)], fill=tuple(int(GOLD_TOP[i] + (GOLD_BOT[i] - GOLD_TOP[i]) * t) for i in range(3)) + (255,))
    m, r = S * 0.03, S * 0.22
    mask = Image.new('L', (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([m, m, S - m, S - m], r, fill=255)
    img.paste(grad, (0, 0), mask)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([m, m, S - m, S - m], r, outline=EDGE, width=max(int(S * 0.035), ss))

    small = size <= 24
    lw = S * (0.085 if small else 0.06)
    cx, cy = S * 0.5, S * 0.36
    base_y, half, top_y = S * 0.86, S * (0.17 if small else 0.15), cy + S * 0.04
    d.line([(cx, top_y), (cx - half, base_y)], fill=INK, width=int(lw))
    d.line([(cx, top_y), (cx + half, base_y)], fill=INK, width=int(lw))
    if not small:
        for f in (0.45, 0.75):
            y = top_y + (base_y - top_y) * f
            d.line([(cx - half * f, y), (cx + half * f, y)], fill=INK, width=int(lw * 0.75))
    br = S * (0.085 if small else 0.07)
    d.ellipse([cx - br, cy - br, cx + br, cy + br], fill=INK)
    ww = int(S * (0.075 if small else 0.055))
    for rr in ([0.24] if small else [0.18, 0.29]):
        R = S * rr
        box = [cx - R, cy - R, cx + R, cy + R]
        d.arc(box, 145, 215, fill=INK, width=ww)
        d.arc(box, -35, 35, fill=INK, width=ww)
    return img.resize((size, size), Image.LANCZOS)


def main():
    sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    imgs = [render(s) for s in sizes]
    imgs[-1].save(os.path.join(ROOT, 'icon.ico'), format='ICO', sizes=[(s, s) for s in sizes], append_images=imgs[:-1])
    render(512).save(os.path.join(ROOT, 'icon.png'))
    render(64).save(os.path.join(ROOT, 'icon_small.png'))
    print('Wrote icon.ico, icon.png, icon_small.png')


if __name__ == '__main__':
    main()
