# 3d-to-pixel-sprite

An agent skill, plus scripts, for rebuilding a pixel-art sprite as a 3D model in headless
Blender and rendering it back to pixel art that matches the original's palette and silhouette.
Once the model matches, you can generate 8 directions and new actions from it.

## Contents
| path | what |
|---|---|
| `SKILL.md` | the step-by-step recipe (frontmatter + steps) |
| `scripts/blender_render.py` | headless render: orthographic camera, transparent background, 8 directions × actions × frames. With no `--blend` file it builds a neutral demo creature |
| `scripts/quantize.py` | fixed-palette quantise, alpha hardened to 0/255, `--check` gate |
| `scripts/compare.py` | anchor-aligned silhouette IoU, paired key-feature error, 3-column compare sheet |
| `scripts/make_sheet.py` | packs frames into a sheet, a JSON index, and an N× nearest-neighbour preview |
| `templates/` | PROGRESS.md and LESSONS.md for short-turn handoff |
| `examples/` | neutral generated demo: palette, compare sheet, sheet with 2 actions × 8 directions × 4 frames |

## Quick start
```bash
pip install numpy pillow
blender -b -P scripts/blender_render.py -- --out renders --size 48 --frames 4 --dirs 8
python scripts/quantize.py --palette examples/palette.txt renders/*.png --out-dir q
python scripts/quantize.py --check --palette examples/palette.txt q/*.png
python scripts/compare.py --ref ref_idle.png --test q/idle_d0_f0.png --target 0.95 \
    --feature-color "#14161c" --sheet compare
python scripts/make_sheet.py q --out sheet --scale 4
```
Tested with Blender 4.2 LTS (EEVEE Next) and Python 3.13.

## License
MIT

## Reference materials needed

You need: one concept image, the existing sprite frames per state (1x and 8x nearest-neighbour), the palette, and the sprite size and pivot from the sheet JSON. A game screenshot, state timings and a short feature spec are recommended. Mark anything missing as a guess in `ref/spec.md`. See the full list and folder layout in [SKILL.md](SKILL.md#reference-materials-needed).
