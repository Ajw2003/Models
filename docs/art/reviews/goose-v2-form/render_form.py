# Close-ups of the #19 form on the textured goose_v2, from the throwaway test's cameras.
# usage: python3.11 render_form.py OUTDIR   (run from the repo root)
import bpy, math, sys
from mathutils import Vector
out = sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath="art/goose/goose_v2.blend")
sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.samples = 24; sc.cycles.device = "CPU"
sc.render.resolution_x = sc.render.resolution_y = 700
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.9, 0.87, 0.8, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 1.2
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun)
sun.rotation_euler = (math.radians(50), 0, math.radians(30)); sun.data.energy = 3
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 50
def shot(name, target, loc):
    cam.location = Vector(loc); d = Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = f"{out}/{name}.png"; bpy.ops.render.render(write_still=True)
shot("chest_front", (0, -1.0, 2.4), (1.6, -5.6, 2.9))
shot("flank_side", (0.3, 0.0, 1.9), (4.8, -0.6, 2.2))
shot("hip", (0.5, 0.1, 1.3), (3.2, -2.4, 1.2))
