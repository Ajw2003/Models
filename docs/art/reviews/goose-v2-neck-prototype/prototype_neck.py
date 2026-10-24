# Throwaway: goose v2 necks with an S-curve and vertebrae. argv: mode (bulge|exposed|straight) outdir
import sys, math, copy
sys.path.insert(0, "/home/claude/models/art/goose")
import bpy, bmesh
from mathutils import Vector
import goose_design as g, goose_skin

mode, out = sys.argv[-2], sys.argv[-1]
spec = g.load_spec()
V = spec["v2"]["design"]
if mode != "straight":
    # alert S-curve (Boas: lower neck bends forward, middle back and up, top forward to the head); heads fixed
    V["main_neck"]["path"] = [[0, -0.85, 2.0], [0, -1.02, 2.6], [0, -1.22, 3.05], [0, -1.42, 3.45],
                              [0, -1.30, 3.95], [0, -1.08, 4.4], [0, -1.18, 4.75], [0, -1.4, 4.95]]
    V["main_neck"]["radii"] = [0.78, 0.68, 0.4, 0.27, 0.22, 0.19, 0.175, 0.165]
    V["side_neck"]["path"] = [[0.12, -1.1, 2.85], [0.45, -1.2, 3.15], [0.8, -1.38, 3.42], [1.0, -1.2, 3.72],
                              [1.08, -1.22, 3.93], [1.15, -1.45, 4.05]]
    V["side_neck"]["radii"] = [0.3, 0.22, 0.17, 0.15, 0.135, 0.13]
parts = g.build_parts(spec, version=2)
NECKS = {"main_neck": (15, 0.22), "side_neck_R": (12, 0.12), "side_neck_L": (12, 0.12)}

def vertebrae(part, count, start_frac):
    sw = part["sweep"]; path = sw["path"]
    s = [0.0]
    for a, b in zip(path, path[1:]): s.append(s[-1] + g.length(g.sub(b, a)))
    L = s[-1]; s0 = start_frac * L
    seg = len(part["rings"][0])
    for i, ring in enumerate(part["rings"]):
        if s[i] < s0: continue
        t = (s[i] - s0) / (L - s0) * count
        ph = t - math.floor(t)
        joint = math.cos(math.pi * ph) ** 6           # swelling at each joint between vertebrae
        waist = math.sin(math.pi * ph) ** 2           # pinch in the middle of each vertebra
        c = path[i]
        for j, p in enumerate(ring):
            a = 2 * math.pi * j / seg
            dorsal = max(0.0, math.cos(a)) ** 6        # a=0 is the back of the neck (ref +Y)
            lateral = max(0.0, abs(math.sin(a)) * max(0.0, math.cos(a) + 0.35)) ** 4  # transverse processes
            r = g.sub(p, c)
            ramp = min(1.0, (s[i] - s0) / (0.08 * L))
            k = 1.0 + ramp * (0.025 * joint - 0.035 * waist + 0.30 * dorsal * joint + 0.12 * lateral * joint)
            ring[j] = g.add(c, g.mul(r, k))

for p in parts:
    if p["name"] in NECKS and mode != "straight":
        n, f = NECKS[p["name"]]
        vertebrae(p, n, f)

if mode == "exposed":  # bone vertebra processes breaking through torn skin along the back
    for p in list(parts):
        if p["name"].startswith("neck_spine"): parts.remove(p)
    for name, (n, f) in NECKS.items():
        neck = next(p for p in parts if p["name"] == name)
        for k in range(n):
            t = f + (1 - f) * (k + 0.5) / n
            if t > 0.92: continue
            pt, nrm, r = g.surface(neck, t, 0)
            i = int(t * (len(neck["sweep"]["path"]) - 1)); tan = neck["sweep"]["frames"][i][0]
            size = 0.16 * r / 0.2
            parts.append(g.cone(f"vert{name}{k}", g.add(pt, g.mul(nrm, -0.04)),
                                g.combine((pt, 1), (nrm, size), (tan, size * 0.7)), 0.05 * r / 0.2 + 0.015, "ToothBone"))

bpy.ops.wm.read_factory_settings(use_empty=True)
names = set(spec["v2"]["skin"]["parts"])
skin, shells = goose_skin.fuse([p for p in parts if p["name"] in names], spec["v2"]["skin"])
hard = g.mesh_parts([p for p in parts if p["name"] not in names])
print("shells", shells, "skin tris", g.triangle_count(skin.faces), "hard tris", g.triangle_count(hard.faces))
def obj(name, m, col):
    me = bpy.data.meshes.new(name); me.from_pydata(m.verts, [], m.faces); me.update()
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    mat = bpy.data.materials.new(name); mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = col
    me.materials.append(mat)
    for poly in me.polygons: poly.use_smooth = True
obj("skin", skin, (0.08, 0.075, 0.07, 1)); obj("hard", hard, (0.6, 0.57, 0.5, 1))
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
shot("neck_side", (0, -1.2, 3.8), (5.5, -1.6, 3.9))
shot("neck_three_quarter", (0.3, -1.2, 3.7), (3.6, -5.0, 4.4))
