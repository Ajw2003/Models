# Throwaway prototype: fuse the goose's soft parts into one skin (voxel union + smoothing at the joins).
import sys, time, math
sys.path.insert(0, "/home/claude/models/art/goose")
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import goose_design as g

FORK = "--fork" in sys.argv
VOXEL = 0.022
spec = g.load_spec(); D = spec["design"]
if FORK:  # one root rising from the chest, splitting at ~3.1 m
    root_top = (0.0, -1.16, 3.05)
    D["main_neck"]["path"] = [[0, -0.85, 2.0], [0, -1.02, 2.6], list(root_top)] + D["main_neck"]["path"][2:]
    D["main_neck"]["radii"] = [0.78, 0.68, 0.40] + D["main_neck"]["radii"][2:]
    sp = D["side_neck"]["path"]
    D["side_neck"]["path"] = [[0.12, -1.10, 2.85], [0.45, -1.17, 3.15]] + sp[2:]
    D["side_neck"]["radii"] = [0.30, 0.22] + D["side_neck"]["radii"][2:]
parts = g.build_parts(spec)
SOFT = {"body", "main_neck", "side_neck_R", "side_neck_L", "wing_arm_R", "wing_arm_L", "leg_R", "leg_L"}
soft = [p for p in parts if p["name"] in SOFT]
hard = [p for p in parts if p["name"] not in SOFT]
bpy.ops.wm.read_factory_settings(use_empty=True)

def make(name, plist):
    m = g.mesh_parts(plist)
    me = bpy.data.meshes.new(name); me.from_pydata(m.verts, [], m.faces); me.update()
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); return o

t0 = time.time()
bvhs = []
for p in soft:
    m = g.mesh_parts([p]); bvhs.append(BVHTree.FromPolygons(m.verts, m.faces))
skin = make("skin", soft)
mod = skin.modifiers.new("v", "REMESH"); mod.mode = "VOXEL"; mod.voxel_size = VOXEL; mod.use_smooth_shade = True
bpy.context.view_layer.objects.active = skin; bpy.ops.object.modifier_apply(modifier="v")
print("remeshed", len(skin.data.polygons), "faces", round(time.time() - t0, 1), "s")

# join weight: how close a vertex is to a second soft part's surface
R = 0.30
me = skin.data
w = []
for v in me.vertices:
    ds = sorted((b.find_nearest(v.co)[3] for b in bvhs))
    w.append(max(0.0, 1.0 - ds[1] / R) if len(ds) > 1 else 0.0)
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
for it in range(40):
    new = []
    for v in bm.verts:
        if w[v.index] <= 0: new.append(None); continue
        avg = sum((e.other_vert(v).co for e in v.link_edges), Vector()) / len(v.link_edges)
        new.append(v.co.lerp(avg, 0.6 * w[v.index]))
    for v, c in zip(bm.verts, new):
        if c is not None: v.co = c
bm.to_mesh(me); bm.free()
mod = skin.modifiers.new("d", "DECIMATE"); mod.ratio = min(1.0, 75000 / (2 * len(me.polygons)))
bpy.ops.object.modifier_apply(modifier="d")
tris = sum(len(p.vertices) - 2 for p in skin.data.polygons)
bm = bmesh.new(); bm.from_mesh(skin.data)
nonman = sum(1 for e in bm.edges if not e.is_manifold); bm.free()
print("skin tris", tris, "non-manifold edges", nonman, round(time.time() - t0, 1), "s")
hardo = make("hard", hard)
for o, col in ((skin, (0.25, 0.22, 0.2, 1)), (hardo, (0.6, 0.57, 0.5, 1))):
    mat = bpy.data.materials.new(o.name); mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = col
    o.data.materials.append(mat)
    for p in o.data.polygons: p.use_smooth = True
sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.samples = 16; sc.cycles.device = "CPU"; sc.render.resolution_x = sc.render.resolution_y = 700
w_ = bpy.data.worlds.new("w"); sc.world = w_; w_.use_nodes = True
w_.node_tree.nodes["Background"].inputs[0].default_value = (0.9, 0.87, 0.8, 1)
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun)
sun.rotation_euler = (math.radians(50), 0, math.radians(30)); sun.data.energy = 3
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam; cam.data.lens = 50
out = sys.argv[-1]
def shot(name, target, loc):
    cam.location = Vector(loc); d = Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = f"{out}/{name}.png"; bpy.ops.render.render(write_still=True)
shot("neck_base_front", (0, -1.3, 2.9), (1.8, -5.2, 3.4))
shot("wing_root", (1.0, -0.6, 2.6), (3.6, -3.4, 3.2))
shot("leg_hip", (0.5, 0.1, 1.3), (3.2, -2.4, 1.2))
shot("whole", (0, -0.3, 3.0), (7.5, -10.5, 4.0))
print("done", round(time.time() - t0, 1), "s")
