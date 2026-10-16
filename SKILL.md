---
name: 3d-to-pixel-sprite
description: >-
  Use when you must turn a painted concept frame plus an existing pixel sprite sheet into a
  3D model (Blender, headless Python) and re-render it as matching pixel-art sprites: a fixed
  palette, silhouette IoU ≥ 0.95 against the reference frames, 8 directions × several actions,
  and 4× nearest-neighbour preview sheets. Built for long jobs split into short agent turns.
---
# 3D-to-pixel sprite

Goal: a 3D stand-in for a hand-made sprite that **matches the existing pixel frames first**
(front view, same size, same anchor, same palette). Only then use it to make new views (8
directions) and new actions. Scripts live in `scripts/`. They need Python 3 with numpy and Pillow, plus Blender 3.6+ for rendering.

## 0. Set up for handoff (every turn)
- Keep every turn short. Each turn does one step and ends with files on disk.
- Keep `PROGRESS.md` in the work folder: checklist of steps, current metrics (IoU per frame, out-of-palette count), the next action, and the exact commands to re-run. Update it before you end the turn.
- Keep `LESSONS.md`: things that failed and why (wrong camera pitch, AA fringe, palette drift). Read both files at the start of every turn. Templates are in `templates/`.
- Don't rebuild finished work. Keep each step as a script you can re-run (`src/build_*.py`), not as manual edits.

## 1. Gather the reference
1. Collect the **painted concept frame** (for anatomy, materials, and light direction) and the **existing sprite sheet plus its metadata** (frame size, anchor or feet row, frame list, feature positions such as eyes).
2. Cut each reference frame out to its own 1× PNG. Make 8× nearest-neighbour copies for viewing.
3. Pull the palette from the sheet: `quantize.py --palette-from sheet.png` or a `palette.txt`. Check that alpha is only ever 0 or 255.
4. Write a short spec covering frame size, anchor, palette, light (usually a single key light from the upper left), camera (front or ¾ view, pitch), states and what changes in each, and the acceptance criteria. Mark anything you guessed as a guess.

## 2. Model in Blender (headless)
- Run Blender headless: `blender -b -P build.py -- args`. Build everything in code: primitives, modifiers, and materials with flat or toon colours that sit close to the palette ramps.
- Put the whole model under an empty called `Root`. Directions rotate `Root`, not the camera, so the light stays fixed on screen.
- Match proportions to the **pixel frames**, not the painting. The sprite's silhouette is the target.

## 3. Rig and animate
- Rig only what the states need: body bob or squash, limb chains, eyelids (blink), pupil scale (alert), and a whole-body pose for states like hide or curl.
- Make one Blender action per game state, named after the state (`idle`, `blink`, `walk`, ...). Keep the frame count equal to the game's frame count.

## 4. Render at sprite size
- Use an orthographic camera at the target pitch, with resolution equal to the sprite frame size (or 2× for a later downsample), `film_transparent`, the Standard view transform, and AA as low as possible.
- `scripts/blender_render.py` shows the full setup and writes `<action>_d<dir>_f<frame>.png`. Tune `--ortho`, `--elev`, and the size until the front frame lines up with the reference.

## 5. Quantise to the fixed palette
- `python scripts/quantize.py --palette palette.txt renders/*.png --out-dir q/`. Pixels snap to the nearest palette colour, with no dithering. Alpha is thresholded to 0 or 255.
- **Gate:** `quantize.py --check` must report `out_of_palette=0 semi_alpha=0` for every frame.
- If a colour comes out wrong, fix the material colour or lighting in 3D. Don't patch pixels by hand.

## 6. Compare against the reference
- `python scripts/compare.py --ref ref_*.png --test q/<front frames> --anchor bottom --target 0.95 --feature-color "#rrggbb" --feature-tol 1 --sheet compare`
- **Gates:** silhouette IoU ≥ 0.95 on every reference frame, key features (eyes) within 1px, the same anchor row, and every limb present.
- Read the diff column. Red means pixels only in the reference and cyan means pixels only in the render. Change the model or camera to fix them, re-render, and compare again. Log each iteration's IoU in PROGRESS.md. If you're stuck after about 3 iterations, write it down in LESSONS.md and change approach (pitch, proportions, or limb pose) rather than nudging the same thing.
- A human sign-off on the 4× compare sheet is the final gate. IoU alone can't judge readability.

## 7. Produce directions, actions, and previews
- Render 8 directions (`--dirs 8`; d0 faces the viewer, then clockwise) for every action. Quantise and run `--check` again.
- `python scripts/make_sheet.py q/ --out sheet --scale 4` writes `sheet.png`, `sheet.json` (row index), and `sheet_4x.png` (nearest-neighbour preview on a dark background).
- Deliver: the sheet(s), the JSON, the compare sheets (1× and 4×), the build scripts, and the final metrics.

## Pitfalls (generic lessons)
- If you don't harden the alpha, AA fringes produce semi-transparent and off-palette edge pixels.
- Filmic or AgX view transforms shift colours. Use Standard.
- A camera pitch that doesn't match the art is the most common cause of IoU stalling around 0.85–0.9.
- Thin parts (bristles, claws, antennae) vanish at 1×. Exaggerate them in 3D, or add them as a scripted post-pass that only uses palette colours.
- A rotating camera moves the light, so rotate the model instead.
- Check your new directions against the light rule (lit from the upper left) on the 4× sheet.

## Reference materials needed

Collect these before modelling. Put them in a `ref/` folder next to your working files.

**Required**
- **Original painted or concept image**: the main source for shape, fur and colour. Ideally a front or three-quarter view with a clean subject at high resolution.
- **Existing pixel sprite frames for each state**: at 1x, plus 8x nearest-neighbour upscales. These are the silhouette and IoU target.
- **Palette**: can be extracted from the sprite sheet (see `scripts/quantize.py`).
- **Sprite size and anchor or pivot info**: read from the sheet JSON.

**Recommended**
- An in-game screenshot for scale and camera angle.
- Close-ups of each state.
- A state list with timing, from the game code or design doc.
- A text spec of key features: eye count and position, leg count, and what must stay readable at 1x.

**Optional**
- Extra angles or a turnaround.
- A motion reference video or frames.

**When something is missing**: carry on, but mark the affected value as a guess in `ref/spec.md` (for example `eye position: GUESS, based on concept art only`) so it can be checked later.

**Example layout**
```
ref/
  concept.png
  frames/<state>_1x.png
  frames/<state>_8x.png
  palette.txt
  spec.md
```
