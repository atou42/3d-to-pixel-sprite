#!/usr/bin/env python3
"""Compare rendered pixel frames against reference frames.
Metrics: alpha-silhouette IoU (after aligning on an anchor) and key-feature offsets.
Writes a 3-column compare sheet: reference | render | silhouette diff
(grey = both, red = reference only, cyan = render only), at 1x and Nx nearest-neighbour.

  python compare.py --ref ref_idle.png ref_blink.png --test out_idle.png out_blink.png \
      --anchor bottom --target 0.95 --feature-color "#000000" --sheet compare
Anchor: 'bottom' aligns bottom-centre of the opaque bbox (feet line); 'bbox' aligns bbox
top-left; 'none' uses raw coordinates. Exit code 1 if any IoU < target or feature error > tol.
"""
import argparse, sys
import numpy as np
from PIL import Image

def rgba(p): return np.asarray(Image.open(p).convert("RGBA"))

def anchor_of(m, mode):
    ys, xs = np.nonzero(m)
    if not len(xs) or mode == "none": return 0, 0
    if mode == "bbox": return ys.min(), xs.min()
    return ys.max(), (xs.min() + xs.max()) // 2

def place(a, H, W, oy, ox):
    out = np.zeros((H, W, 4), np.uint8)
    h, w = a.shape[:2]
    out[oy:oy + h, ox:ox + w] = a
    return out

def align(r, t, mode):
    ar, at = anchor_of(r[..., 3] > 0, mode), anchor_of(t[..., 3] > 0, mode)
    pad = max(r.shape[0], r.shape[1], t.shape[0], t.shape[1])
    H = W = 3 * pad
    R = place(r, H, W, pad, pad)
    T = place(t, H, W, pad + ar[0] - at[0], pad + ar[1] - at[1])
    both = (R[..., 3] > 0) | (T[..., 3] > 0)
    ys, xs = np.nonzero(both)
    sl = (slice(ys.min(), ys.max() + 1), slice(xs.min(), xs.max() + 1))
    return R[sl], T[sl]

def iou(R, T):
    a, b = R[..., 3] > 0, T[..., 3] > 0
    u = (a | b).sum()
    return float((a & b).sum() / u) if u else 1.0

def feature_centroid(A, hexcol, tol=24):
    c = np.array([int(hexcol[i:i + 2], 16) for i in (1, 3, 5)])
    m = (A[..., 3] > 0) & (np.abs(A[..., :3].astype(int) - c).max(-1) <= tol)
    ys, xs = np.nonzero(m)
    if not len(xs): return None
    # split left/right halves for paired features (eyes)
    mid = A.shape[1] / 2
    pts = []
    for sel in (xs < mid, xs >= mid):
        if sel.any(): pts.append((xs[sel].mean(), ys[sel].mean()))
    return pts

def diff_img(R, T, bg=(38, 40, 52, 255)):
    a, b = R[..., 3] > 0, T[..., 3] > 0
    out = np.zeros(R.shape, np.uint8); out[:] = bg
    out[a & b] = (110, 110, 110, 255); out[a & ~b] = (230, 60, 60, 255); out[~a & b] = (60, 210, 230, 255)
    return out

def on_bg(A, bg=(38, 40, 52)):
    out = np.zeros(A.shape, np.uint8); out[..., :3] = bg; out[..., 3] = 255
    m = A[..., 3] > 0; out[m, :3] = A[m, :3]; return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", nargs="+", required=True)
    ap.add_argument("--test", nargs="+", required=True)
    ap.add_argument("--anchor", default="bottom", choices=["bottom", "bbox", "none"])
    ap.add_argument("--target", type=float, default=0.95)
    ap.add_argument("--feature-color", help="hex colour of a key feature (e.g. pupils)")
    ap.add_argument("--feature-tol", type=float, default=1.0, help="max px error")
    ap.add_argument("--sheet", help="output prefix for compare sheets")
    ap.add_argument("--scale", type=int, default=4)
    o = ap.parse_args()
    assert len(o.ref) == len(o.test), "need same number of ref and test frames"
    rows, ok = [], True
    for rp, tp in zip(o.ref, o.test):
        R, T = align(rgba(rp), rgba(tp), o.anchor)
        v = iou(R, T); msg = f"{tp}: IoU={v:.3f}"
        ok &= v >= o.target
        if o.feature_color:
            fr, ft = feature_centroid(R, o.feature_color), feature_centroid(T, o.feature_color)
            if fr and ft and len(fr) == len(ft):
                err = max(np.hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(fr, ft))
                msg += f" feature_err={err:.2f}px"; ok &= err <= o.feature_tol
            else:
                msg += " feature=MISSING"; ok = False
        print(msg); rows.append((R, T))
    if o.sheet:
        g = 2
        W = max(r.shape[1] for r, _ in rows); Hs = [r.shape[0] for r, _ in rows]
        sheet = np.zeros((sum(Hs) + g * (len(rows) + 1), 3 * W + 4 * g, 4), np.uint8)
        sheet[:] = (38, 40, 52, 255); y = g
        for (R, T), h in zip(rows, Hs):
            for i, img in enumerate((on_bg(R), on_bg(T), diff_img(R, T))):
                x = g + i * (W + g); sheet[y:y + h, x:x + img.shape[1]] = img
            y += h + g
        im = Image.fromarray(sheet)
        im.save(o.sheet + "_1x.png")
        im.resize((im.width * o.scale, im.height * o.scale), Image.NEAREST).save(o.sheet + f"_{o.scale}x.png")
    print("PASS" if ok else "FAIL"); sys.exit(0 if ok else 1)
