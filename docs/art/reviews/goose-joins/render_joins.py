import bpy, bmesh, math, sys
from mathutils import Vector
out=sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath="art/goose/goose.blend")
obj=[o for o in bpy.data.objects if o.type=='MESH'][0]
bm=bmesh.new(); bm.from_mesh(obj.data); bm.verts.ensure_lookup_table()
# count connected shells
seen=set(); shells=0
for v in bm.verts:
    if v.index in seen: continue
    shells+=1; stack=[v]; seen.add(v.index)
    while stack:
        x=stack.pop()
        for e in x.link_edges:
            o=e.other_vert(x)
            if o.index not in seen: seen.add(o.index); stack.append(o)
print("SHELLS", shells, "VERTS", len(bm.verts), "MATERIAL SLOTS", len(obj.data.materials))
sc=bpy.context.scene; sc.render.engine='CYCLES'; sc.cycles.samples=24; sc.cycles.device='CPU'
sc.render.resolution_x=sc.render.resolution_y=700
w=bpy.data.worlds.new("w"); sc.world=w; w.use_nodes=True; w.node_tree.nodes["Background"].inputs[0].default_value=(0.9,0.87,0.8,1); w.node_tree.nodes["Background"].inputs[1].default_value=1.2
sun=bpy.data.objects.new("sun",bpy.data.lights.new("sun",'SUN')); sc.collection.objects.link(sun); sun.rotation_euler=(math.radians(50),0,math.radians(30)); sun.data.energy=3
cam=bpy.data.objects.new("cam",bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera=cam; cam.data.lens=50
def shot(name, target, loc):
    cam.location=Vector(loc); d=Vector(target)-cam.location; cam.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=f"{out}/{name}.png"; bpy.ops.render.render(write_still=True)
shot("neck_base_front",(0,-1.3,2.9),(1.8,-5.2,3.4))
shot("neck_base_side",(0,-1.2,3.0),(4.6,-1.6,3.3))
shot("wing_root",(1.0,-0.6,2.6),(3.6,-3.4,3.2))
shot("leg_hip",(0.5,0.1,1.3),(3.2,-2.4,1.2))
shot("side_neck_join",(0.6,-1.2,3.6),(3.0,-3.8,4.4))
