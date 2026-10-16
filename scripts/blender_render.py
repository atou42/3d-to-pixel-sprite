"""Headless Blender: build a simple rigged demo creature (or load a .blend),
animate states, and render 8 directions x N actions with an orthographic camera
at sprite resolution (no anti-aliasing, transparent background).

Usage:
  blender -b -P scripts/blender_render.py -- --out renders --size 48 [--blend model.blend]
         [--actions idle,hop] [--frames 4] [--dirs 8] [--elev 30]
Output: renders/<action>_d<dir>_f<frame>.png   (dir 0 = facing camera/south, clockwise)
With --blend, the file must contain an object named "Root" (rotated for directions)
and optional NLA/actions named like the --actions list.
"""
import argparse, math, os, sys
import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="renders")
ap.add_argument("--size", type=int, default=48)
ap.add_argument("--blend")
ap.add_argument("--actions", default="idle,hop")
ap.add_argument("--frames", type=int, default=4)
ap.add_argument("--dirs", type=int, default=8)
ap.add_argument("--elev", type=float, default=30.0, help="camera pitch down, degrees")
ap.add_argument("--ortho", type=float, default=2.6, help="ortho_scale (world units across)")
a = ap.parse_args(argv)
os.makedirs(a.out, exist_ok=True)

def mat(name, rgb):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = 1.0
    return m

def build_demo():
    """Neutral demo: round blob body, two eyes, two feet. Root drives hop/squash."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    root = bpy.data.objects.new("Root", None); bpy.context.scene.collection.objects.link(root)
    def add(op, name, m, loc, scale, **kw):
        op(location=loc, **kw); o = bpy.context.active_object
        o.name = name; o.scale = scale; o.data.materials.append(m); o.parent = root
        bpy.ops.object.shade_smooth(); return o
    body = add(bpy.ops.mesh.primitive_uv_sphere_add, "Body", mat("body", (0.25, 0.55, 0.35)),
               (0, 0, 0.7), (0.75, 0.7, 0.65), segments=24, ring_count=12)
    for s in (-1, 1):
        add(bpy.ops.mesh.primitive_uv_sphere_add, f"Eye{s}", mat("eye", (0.95, 0.95, 0.9)),
            (0.28 * s, -0.6, 0.85), (0.16, 0.08, 0.16))
        add(bpy.ops.mesh.primitive_uv_sphere_add, f"Pupil{s}", mat("pupil", (0.03, 0.03, 0.05)),
            (0.28 * s, -0.66, 0.85), (0.08, 0.05, 0.08))
        add(bpy.ops.mesh.primitive_cube_add, f"Foot{s}", mat("foot", (0.85, 0.6, 0.2)),
            (0.35 * s, -0.15, 0.1), (0.18, 0.25, 0.1))
    # animate: idle = gentle squash, hop = jump arc
    sc = bpy.context.scene
    act_idle = bpy.data.actions.new("idle"); act_hop = bpy.data.actions.new("hop")
    root.animation_data_create()
    for act, keys in ((act_idle, [(1, 0, 1.0), (3, 0, 0.94), (5, 0, 1.0)]),
                      (act_hop, [(1, 0, 1.0), (2, 0.35, 1.05), (3, 0.5, 1.0), (4, 0.2, 0.95), (5, 0, 1.0)])):
        root.animation_data.action = act
        for f, z, s in keys:
            root.location = (0, 0, z); root.scale = (1 / math.sqrt(s), 1 / math.sqrt(s), s)
            root.keyframe_insert("location", frame=f); root.keyframe_insert("scale", frame=f)
    return root

if a.blend:
    bpy.ops.wm.open_mainfile(filepath=a.blend)
    root = bpy.data.objects["Root"]
else:
    root = build_demo()

sc = bpy.context.scene
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "BLENDER_WORKBENCH"):
    try: sc.render.engine = eng; break
    except TypeError: pass
sc.render.resolution_x = sc.render.resolution_y = a.size
sc.render.resolution_percentage = 100
sc.render.film_transparent = True
sc.render.filter_size = 0.01            # ~no AA; quantise step hardens alpha anyway
sc.render.image_settings.color_mode = "RGBA"
sc.view_settings.view_transform = "Standard"
# single key light from upper-left (NW), in camera-relative terms
sun = bpy.data.objects.new("Key", bpy.data.lights.new("Key", "SUN"))
sun.data.energy = 3.0; sc.collection.objects.link(sun)
if sc.world is None: sc.world = bpy.data.worlds.new("W")
sc.world.use_nodes = True
sc.world.node_tree.nodes["Background"].inputs[1].default_value = 0.6
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
cam.data.type = "ORTHO"; cam.data.ortho_scale = a.ortho
sc.collection.objects.link(cam); sc.camera = cam
el = math.radians(a.elev); d = 10
cam.location = (0, -d * math.cos(el), 0.7 + d * math.sin(el))
cam.rotation_euler = (math.pi / 2 - el, 0, 0)
sun.rotation_euler = (math.radians(50), math.radians(-35), math.radians(-30))

for act in a.actions.split(","):
    if act in bpy.data.actions and root.animation_data:
        root.animation_data.action = bpy.data.actions[act]
        f0, f1 = bpy.data.actions[act].frame_range
    else:
        f0, f1 = 1, 1
    for di in range(a.dirs):
        for fi in range(a.frames):
            f = f0 + (f1 - f0) * fi / max(1, a.frames - 1) if a.frames > 1 else f0
            sc.frame_set(int(round(f)))
            # rotate model, not camera, so lighting stays screen-fixed (NW)
            root.rotation_euler = (0, 0, -2 * math.pi * di / a.dirs)
            sc.render.filepath = os.path.join(a.out, f"{act}_d{di}_f{fi}.png")
            bpy.ops.render.render(write_still=True)
print("RENDER_DONE", a.out)
