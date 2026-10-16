#!/usr/bin/env python3
"""Quantise RGBA renders to a fixed palette. Alpha -> 0/255 by threshold,
RGB -> nearest palette colour (no dithering). Verifies 0 out-of-palette pixels.

  python quantize.py --palette palette.txt  in1.png [in2.png ...] --out-dir q/
  python quantize.py --palette-from ref_sheet.png ...      # palette = colours in a reference sheet
  python quantize.py --check --palette palette.txt sheet.png   # verify only; exit 1 on failure
palette.txt: one #rrggbb per line (# comments allowed after whitespace).
"""
import argparse, os, sys
import numpy as np
from PIL import Image

def load_palette(path=None, from_img=None):
    if from_img:
        a = np.asarray(Image.open(from_img).convert("RGBA"))
        return np.unique(a[a[..., 3] > 0][:, :3], axis=0).astype(np.int32)
    cols = []
    for line in open(path):
        t = line.split()[0] if line.split() else ""
        if t.startswith("#") and len(t) == 7:
            cols.append([int(t[i:i + 2], 16) for i in (1, 3, 5)])
    return np.array(cols, dtype=np.int32)

def quantize(img, pal, alpha_thr=128):
    a = np.asarray(img.convert("RGBA")).astype(np.int32)
    rgb, al = a[..., :3], a[..., 3]
    # perceptual-ish weighted RGB distance
    w = np.array([2, 4, 3])
    d = (((rgb[..., None, :] - pal[None, None]) ** 2) * w).sum(-1)
    out = np.zeros_like(a)
    out[..., :3] = pal[d.argmin(-1)]
    out[..., 3] = np.where(al >= alpha_thr, 255, 0)
    out[out[..., 3] == 0] = 0
    return Image.fromarray(out.astype(np.uint8), "RGBA")

def check(img, pal):
    a = np.asarray(img.convert("RGBA"))
    bad_alpha = int(((a[..., 3] != 0) & (a[..., 3] != 255)).sum())
    vis = a[a[..., 3] == 255][:, :3].astype(np.int32)
    ok = (vis[:, None] == pal[None]).all(-1).any(-1) if len(vis) else np.array([], bool)
    return int((~ok).sum()), bad_alpha

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--palette"); g.add_argument("--palette-from")
    ap.add_argument("--out-dir", default="quantized")
    ap.add_argument("--alpha", type=int, default=128)
    ap.add_argument("--check", action="store_true")
    o = ap.parse_args()
    pal = load_palette(o.palette, o.palette_from)
    fail = 0
    if not o.check: os.makedirs(o.out_dir, exist_ok=True)
    for p in o.inputs:
        im = Image.open(p)
        if not o.check:
            im = quantize(im, pal, o.alpha)
            im.save(os.path.join(o.out_dir, os.path.basename(p)))
        oop, ba = check(im, pal)
        fail |= bool(oop or ba)
        print(f"{os.path.basename(p)}: out_of_palette={oop} semi_alpha={ba}")
    print(f"palette={len(pal)} colours; {'FAIL' if fail else 'OK'}")
    sys.exit(1 if fail else 0)
