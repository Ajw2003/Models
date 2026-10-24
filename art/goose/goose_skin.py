"""Fuse the goose's soft parts into one closed skin (version 2, Models #18). Needs bpy.

The soft parts (spec "v2" -> "skin" -> "parts") are meshed as version 1 would mesh them, melted into
one surface by a voxel remesh, smoothed only near the joins so each join becomes a wide curve, and
decimated to the skin's triangle cap. Each new face then takes its material, pattern and texture
coordinates from the nearest face of the unfused parts, so the version 1 bake reads it as before.
That carry-over is a stand-in until Models #20 re-bakes colour across the joins.
"""
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

import goose_design as g


def fuse(soft_parts, skin_spec):
    """Returns (skin, shells): a goose_design.Mesh of the fused skin and its count of separate pieces."""
    source = g.mesh_parts(soft_parts)
    obj = _remeshed_object(source, skin_spec["voxel_m"])
    per_part = [BVHTree.FromPolygons(m.verts, m.faces) for m in (g.mesh_parts([p]) for p in soft_parts)]
    _smooth_joins(obj.data, per_part, skin_spec["join_width_m"], skin_spec["smooth_passes"])
    _decimate(obj, skin_spec["triangle_cap"])
    shells = _count_shells(obj.data)
    skin = _carry_over(obj.data, source)
    mesh = obj.data
    bpy.data.objects.remove(obj)
    bpy.data.meshes.remove(mesh)
    return skin, shells


def _remeshed_object(source, voxel_m):
    mesh = bpy.data.meshes.new("skin")
    mesh.from_pydata(source.verts, [], source.faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)  # the remesh needs outward faces to tell inside from out
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("skin", mesh)
    bpy.context.scene.collection.objects.link(obj)
    remesh = obj.modifiers.new("remesh", "REMESH")
    remesh.mode = "VOXEL"
    remesh.voxel_size = voxel_m
    _apply(obj, remesh)
    return obj


def _smooth_joins(mesh, per_part, width_m, passes):
    """Relax only vertices near a second soft part, weighted by closeness, so the crease the remesh
    leaves where two parts cross fills into a curve about width_m wide and the rest keeps its shape."""
    weights = []
    for v in mesh.vertices:
        distances = sorted(tree.find_nearest(v.co)[3] for tree in per_part)
        weights.append(max(0.0, 1.0 - distances[1] / width_m))
    bm = bmesh.new()
    bm.from_mesh(mesh)
    moving = [v for v in bm.verts if weights[v.index] > 0]
    for _ in range(passes):
        targets = [sum((e.other_vert(v).co for e in v.link_edges), Vector()) / len(v.link_edges) for v in moving]
        for v, target in zip(moving, targets):
            v.co = v.co.lerp(target, 0.6 * weights[v.index])
    bm.to_mesh(mesh)
    bm.free()


def _decimate(obj, triangle_cap):
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    if tris <= triangle_cap:
        return
    decimate = obj.modifiers.new("decimate", "DECIMATE")
    decimate.ratio = triangle_cap / tris
    _apply(obj, decimate)


def _apply(obj, modifier):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def _carry_over(mesh, source):
    """Every new face copies the nearest source face's material and pattern, and maps its corners
    through that one face's texture coordinates. Mapping all corners through one face, rather than each
    corner through its own nearest face, keeps a face that straddles a part's wrap-around seam from
    smearing the whole texture across itself."""
    tree = BVHTree.FromPolygons(source.verts, source.faces)
    maps = {}
    skin = g.Mesh()
    skin.verts = [tuple(v.co) for v in mesh.vertices]
    for poly in mesh.polygons:
        k = tree.find_nearest(poly.center)[2]
        if k not in maps:
            maps[k] = _face_map(source, k)
        to_uv = maps[k]
        corners = [mesh.vertices[i].co for i in poly.vertices]
        skin.faces.append(tuple(poly.vertices))
        skin.materials.append(source.materials[k])
        skin.patterns.append(source.patterns[k])
        skin.pattern_uv.append(tuple(to_uv(c, source.pattern_uv[k]) for c in corners))
        skin.shape_uv.append(tuple(to_uv(c, source.shape_uv[k]) for c in corners))
    return skin


def _face_map(source, k):
    """A function (point, per-corner values) -> value: the least-squares plane fit of the face's corner
    values over the face, so a point slightly off the face extends it linearly."""
    pts = [Vector(source.verts[i]) for i in source.faces[k]]
    origin = sum(pts, Vector()) / len(pts)
    a = (pts[1] - pts[0]).normalized()
    normal = (pts[1] - pts[0]).cross(pts[-1] - pts[0])
    b = normal.cross(a).normalized() if normal.length > 1e-12 else Vector((0.0, 0.0, 0.0))
    xy = [((p - origin).dot(a), (p - origin).dot(b)) for p in pts]
    sxx = sum(x * x for x, _ in xy)
    syy = sum(y * y for _, y in xy)
    sxy = sum(x * y for x, y in xy)
    det = sxx * syy - sxy * sxy

    def to_uv(point, values):
        x, y = (point - origin).dot(a), (point - origin).dot(b)
        out = []
        for c in range(2):
            vals = [v[c] for v in values]
            mean = sum(vals) / len(vals)  # xy is centred on the corners, so the fit's constant is the mean
            if abs(det) < 1e-18:  # a degenerate face (a cap's pole): take the mean
                out.append(mean)
                continue
            sxv = sum(px * (v - mean) for (px, _), v in zip(xy, vals))
            syv = sum(py * (v - mean) for (_, py), v in zip(xy, vals))
            slope_x = (syy * sxv - sxy * syv) / det
            slope_y = (sxx * syv - sxy * sxv) / det
            out.append(mean + slope_x * x + slope_y * y)
        return tuple(out)

    return to_uv


def _count_shells(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    seen, shells = set(), 0
    for start in bm.verts:
        if start.index in seen:
            continue
        shells += 1
        stack = [start]
        seen.add(start.index)
        while stack:
            v = stack.pop()
            for e in v.link_edges:
                other = e.other_vert(v)
                if other.index not in seen:
                    seen.add(other.index)
                    stack.append(other)
    bm.free()
    return shells
