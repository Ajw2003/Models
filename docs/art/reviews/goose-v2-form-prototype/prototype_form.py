# Throwaway: #19 form on goose v2: muscle, sag, folds, ribs under skin, feathers over joins. argv: ribs(under|torn) outdir
import sys, math, random
sys.path.insert(0, "/home/claude/models/art/goose")
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import goose_design as g, goose_skin

ribmode, out = sys.argv[-2], sys.argv[-1]
spec = g.load_spec()
parts = g.build_parts(spec, version=2)
by = {p["name"]: p for p in parts}
rng = random.Random(7)
X, Y, Z = (1.0, 0, 0), (0, 1.0, 0), (0, 0, 1.0)
extra_soft = []
for s in (1, -1):
    t = "R" if s > 0 else "L"
    extra_soft += [g.ellipsoid(f"pec_{t}", (0.36 * s, -0.98, 2.3), (Z, X, Y), (0.42, 0.3, 0.26), "PlumageBrown"),
                   g.ellipsoid(f"shoulder_{t}", (0.55 * s, -0.5, 2.5), (X, Y, Z), (0.3, 0.3, 0.22), "PlumageBrown"),
                   g.ellipsoid(f"thigh_{t}", (0.42 * s, -0.12, 1.42), (Z, X, Y), (0.34, 0.22, 0.26), "PlumageBrown")]
extra_soft.append(g.ellipsoid("belly", (0, 0.05, 1.28), (Y, X, Z), (0.75, 0.55, 0.28), "BreastPale"))
for k, z in enumerate((2.45, 2.62, 2.8)):  # skin folds round the neck root
    c = g.lerp((0, -0.92, 2.3), (0, -1.1, 2.85), (z - 2.3) / 0.55)
    r = 0.74 - 0.12 * k
    ring = [g.add(c, (r * math.cos(2 * math.pi * j / 20), 0.75 * r * math.sin(2 * math.pi * j / 20), 0.03 * math.sin(4 * math.pi * j / 20))) for j in range(20)]
    extra_soft.append(g.tube(f"fold{k}", ring, [0.05] * 20, "GooseBlack", step=0.05, segments=10, closed=True))
ribs = [p for p in parts if p["name"].startswith("rib")]
soft_ribs = []
for p in ribs:  # the rib under the skin: the same path, pushed in so only a ridge shows
    sw = p["sweep"]
    soft_ribs.append(g.tube(p["name"] + "_under", sw["path"][::3] + [sw["path"][-1]], [0.05] * len(sw["path"][::3] + [sw["path"][-1]]), "PlumageBrown", step=0.04, segments=10))
parts = [p for p in parts if not p["name"].startswith("scute")]
if ribmode == "under":
    parts = [p for p in parts if not p["name"].startswith("rib")]
else:  # torn: keep the middle third of each rib as bare bone breaking through
    keep = []
    for p in parts:
        if p["name"].startswith("rib"):
            sw = p["sweep"]; n = len(sw["path"]); a, b = n // 3, 2 * n // 3
            q = g.tube(p["name"], sw["path"][a:b + 1], [0.032] * (b - a + 1), "ToothBone", step=0.04, segments=10)
            keep.append(q)
        else:
            keep.append(p)
    parts = keep
# feathers over the joins
def surface_feathers(prefix, centre, count, radius, up_bias, lengths, mat):
    out = []
    for k in range(count):
        a = 2 * math.pi * k / count + rng.uniform(-0.2, 0.2)
        root = g.add(centre, (radius * math.cos(a), 0.8 * radius * math.sin(a), rng.uniform(-0.05, 0.08)))
        n = g.norm(g.sub(root, centre))
        d = g.norm(g.combine((n, 0.35), (Z, -1.0)))
        out.append(g.feather(f"{prefix}{k}", root, d, n, rng.uniform(*lengths), 0.09, mat, rng, curl=0.1, ragged=0.6, stations=6))
    return out
feathers = surface_feathers("root_hackle", (0, -1.05, 2.95), 22, 0.42, 0, (0.4, 0.65), "GooseBlack")
for s in (1, -1):
    t = "R" if s > 0 else "L"
    feathers += [g.feather(f"shoulder_covert{k}_{t}", (s * (0.55 + 0.05 * k), -0.62 + 0.03 * (k % 3), 2.72 - 0.02 * k),
                           g.norm((s * 0.35, 0.25, -1.0)), g.norm((s * 1.0, -0.3, 0.2)), rng.uniform(0.3, 0.42), 0.12,
                           "PlumageBrown", rng, curl=0.06, ragged=0.4, stations=6) for k in range(9)]
    feathers += surface_feathers(f"thigh_{t}", (0.42 * s, -0.12, 1.32), 13, 0.27, 0, (0.38, 0.55), "PlumageBrown")
parts += feathers
names = set(spec["v2"]["skin"]["parts"])
soft = [p for p in parts if p["name"] in names] + extra_soft + soft_ribs
hard = [p for p in parts if p["name"] not in names]
bpy.ops.wm.read_factory_settings(use_empty=True)
# smoothing joins only between the original soft parts: pass those as the join reference
orig = goose_skin._smooth_joins
skin_names = names
def smooth_only_main(mesh, per_part, width, passes):
    orig(mesh, per_part[:len(skin_names)], width, passes)
goose_skin._smooth_joins = smooth_only_main
skin, shells = goose_skin.fuse(soft, spec["v2"]["skin"])
hm = g.mesh_parts(hard)
print("shells", shells, "skin", g.triangle_count(skin.faces), "hard", g.triangle_count(hm.faces),
      "total", g.triangle_count(skin.faces) + g.triangle_count(hm.faces), "feathers", g.triangle_count(g.mesh_parts(feathers).faces))
def obj(name, m, col):
    me = bpy.data.meshes.new(name); me.from_pydata(m.verts, [], m.faces); me.update()
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    mat = bpy.data.materials.new(name); mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = col
    me.materials.append(mat)
    for poly in me.polygons: poly.use_smooth = True
obj("skin", skin, (0.32, 0.29, 0.26, 1)); obj("hard", hm, (0.6, 0.57, 0.5, 1))
sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.samples = 16; sc.cycles.device = "CPU"
sc.render.resolution_x = sc.render.resolution_y = 700
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.9, 0.87, 0.8, 1)
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun)
sun.rotation_euler = (math.radians(50), 0, math.radians(30)); sun.data.energy = 3
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam; cam.data.lens = 50
def shot(name, target, loc):
    cam.location = Vector(loc); d = Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = f"{out}/{name}.png"; bpy.ops.render.render(write_still=True)
shot("chest_front", (0, -1.0, 2.4), (1.6, -5.6, 2.9))
shot("flank_side", (0.3, 0.0, 1.9), (4.8, -0.6, 2.2))
shot("hip", (0.5, 0.1, 1.3), (3.2, -2.4, 1.2))
