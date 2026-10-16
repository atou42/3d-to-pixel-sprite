#!/usr/bin/env python3
"""Pack frames named <action>_d<dir>_f<frame>.png into a sheet (rows = action x dir,
cols = frames) plus a JSON index, and an Nx nearest-neighbour preview on a dark background.

  python make_sheet.py quantized/ --out sheet --scale 4
"""
import argparse, glob, json, os, re
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("dir"); ap.add_argument("--out", default="sheet")
ap.add_argument("--scale", type=int, default=4); ap.add_argument("--gap", type=int, default=1)
o = ap.parse_args()
pat = re.compile(r"(.+)_d(\d+)_f(\d+)\.png$")
fr = {}
for p in glob.glob(os.path.join(o.dir, "*.png")):
    m = pat.search(os.path.basename(p))
    if m: fr[(m[1], int(m[2]), int(m[3]))] = p
acts = sorted({k[0] for k in fr}); dirs = sorted({k[1] for k in fr}); fs = sorted({k[2] for k in fr})
w, h = Image.open(next(iter(fr.values()))).size
g = o.gap
sheet = Image.new("RGBA", (len(fs) * (w + g) - g, len(acts) * len(dirs) * (h + g) - g), (0, 0, 0, 0))
index = {"frame_w": w, "frame_h": h, "gap": g, "rows": []}
r = 0
for a in acts:
    for d in dirs:
        for f in fs:
            if (a, d, f) in fr: sheet.paste(Image.open(fr[(a, d, f)]), (f * (w + g), r * (h + g)))
        index["rows"].append({"action": a, "dir": d, "y": r * (h + g), "frames": len(fs)}); r += 1
sheet.save(o.out + ".png"); json.dump(index, open(o.out + ".json", "w"), indent=1)
bg = Image.new("RGBA", sheet.size, (38, 40, 52, 255)); bg.alpha_composite(sheet)
bg.resize((sheet.width * o.scale, sheet.height * o.scale), Image.NEAREST).save(o.out + f"_{o.scale}x.png")
print(f"{len(acts)} actions x {len(dirs)} dirs x {len(fs)} frames -> {o.out}.png")
