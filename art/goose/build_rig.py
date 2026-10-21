#!/usr/bin/env python3
"""Rig the eldritch goose: a 59-bone generic skeleton bound to the built mesh, plus a pose test.

  python3.11 art/goose/build_rig.py                                   # goose.blend -> goose_rigged.blend
  python3.11 art/goose/build_rig.py --pose-test POSED.blend           # pose goose_rigged.blend, check, save a copy

Opens goose.blend (never modified), adds the armature, skins the mesh and saves goose_rigged.blend.

Version 2 (--v2): the same 59 bones plus three bones per tongue (tongue_main_1..3, tongue_L_1..3,
tongue_R_1..3, parented to the head's jaw), 68 in all, with the tongue skinned softly along them and its
spikes rigid on their nearest tongue bone; written to goose_rigged_v2.blend. Version 1's files are never touched:

  python3.11 art/goose/build_rig.py --v2                              # goose.blend -> goose_rigged_v2.blend
  python3.11 art/goose/build_rig.py --v2 --pose-test POSED.blend      # jaws wide, tongues lolled out and down
  python3.11 art/goose/build_rig.py --v2 --closeup POSED.blend DIR    # close-up renders of the three heads
Bone joints come from spec.json through goose_design (neck control paths, wing and leg joints, head
bases and directions, tail root, the crown branch roots read off the built parts), so a rebuilt mesh
gives a rebuilt rig.

Side naming: bones use the goose's own point of view (Blender convention). It faces -Y, so +X is its
LEFT: .L / _L = +X, .R / _R = -X. goose_design tags its parts the other way round (side_neck_R is at
+X); BONE_SIDE below is the one table that maps across.

Weighting method: computed here, not Blender's bone-heat (slow and unreliable on 138,300 vertices of
1,072 separate closed shells). Every part is mapped by name to one of:
  soft  - per vertex: project onto the chain of bones (a polyline), take the arc-length position and
          blend neighbouring bones across each joint with a smoothstep (bodies, necks, heads, wing
          arms, legs, tail feathers). The first joint of a limb also blends a little with the body
          bone it grows from, so the root does not tear off the chest.
  root  - the whole part takes the blend at its root vertex (feathers, hackles, ribs, spines), so a
          feather bends with the limb but is never stretched.
  bone  - 100% on one bone (teeth, beak, jaw, tongue, eyes, brows, crown branches, finger bones
          split at their knuckle, claws, toes, webs, scutes).
Weights sum to 1 per vertex, at most 3 bones per vertex, and are checked against chain membership.
The pose test turns the main neck 40 degrees, bends the left neck down, raises the right wing 45
degrees, lifts the left knee and scales crown_main 1.5, then checks the lowest vertex is >= -0.01 m.
Review renders (from the repo root; render_views.py and review_sheet.py are the art-pipeline's):
  python3.11 SCRIPTS/render_views.py POSED.blend --out art/goose/rig_views --res 900 --background "#EDE6D6"
  python3.11 SCRIPTS/render_views.py art/goose/goose_rigged.blend --out REST --res 900 --background "#EDE6D6"
  (REST/three_quarter.png is kept as art/goose/rig_views/rest_three_quarter.png)
"""
import math, os, re, sys, time

try:
    import bpy
    import numpy as np
    from mathutils import Matrix, Vector
except ImportError:
    sys.exit("build_rig.py: cannot import bpy/numpy; run it with the interpreter from setup_bpy.sh")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import goose_design as g  # noqa: E402

V2 = "--v2" in sys.argv
BONE_COUNT = 59  # version 1; version 2 adds three tongue bones per head that has a tongue in spec.json
TONGUE_BONES = 3
OUT_NAME = "goose_rigged_v2.blend" if V2 else "goose_rigged.blend"
FLOOR_TOLERANCE_M = 0.01
GROUND_TOE_Z = 0.045  # goose_design's toe tip height
# goose_design's side tag -> bone side. Design "R" is +X, which is the goose's LEFT (it faces -Y).
BONE_SIDE = {"R": "L", "L": "R"}


def bs(tag):
    return BONE_SIDE[tag]


def die(msg):
    sys.exit(f"build_rig.py: {msg}")


# ---------------------------------------------------------------- geometry helpers

def V(p):
    return np.array(p, dtype=float)


def resample(points, n):
    """n+1 points evenly spaced by arc length along the smooth curve through the control points."""
    dense, _ = g.smooth_path([tuple(p) for p in points], [(0.0,)] * len(points), 0.01)
    dense = np.array(dense)
    cum = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(dense, axis=0), axis=1))])
    return [np.array([np.interp(s, cum, dense[:, k]) for k in range(3)]) for s in np.linspace(0, cum[-1], n + 1)]


def project(P, pts):
    """Closest point on the polyline pts for each row of P: (arc-length position, distance)."""
    pts = np.array(pts)
    seg = np.diff(pts, axis=0)
    seglen = np.linalg.norm(seg, axis=1)
    cum = np.concatenate([[0], np.cumsum(seglen)])
    best_d2 = np.full(len(P), np.inf)
    best_s = np.zeros(len(P))
    for i in range(len(seg)):
        a, ab = pts[i], seg[i]
        t = np.clip(((P - a) @ ab) / (seglen[i] ** 2), 0, 1)
        d2 = ((P - (a + t[:, None] * ab)) ** 2).sum(axis=1)
        better = d2 < best_d2
        best_d2 = np.where(better, d2, best_d2)
        best_s = np.where(better, cum[i] + t * seglen[i], best_s)
    return best_s, np.sqrt(best_d2)


def smoothstep(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


class Chain:
    """Connected bones head to tail, optionally preceded by an anchor (a body bone and a point on it)."""

    def __init__(self, bones, pts, anchor=None, anchor_pt=None, hfrac=0.5, anchor_h=0.15):
        self.pts = [np.array(p) for p in pts]
        self.names = list(bones)
        if anchor:
            self.names = [anchor] + self.names
            self.pts = [np.array(anchor_pt)] + self.pts
        seg = np.linalg.norm(np.diff(np.array(self.pts), axis=0), axis=1)
        self.cum = np.concatenate([[0], np.cumsum(seg)])
        self.joint_s, self.joint_h = [], []
        for j in range(1, len(self.names)):
            h = hfrac * min(seg[j - 1], seg[j]) if j < len(seg) else 0
            if anchor and j == 1:
                h = min(anchor_h, h)
            self.joint_s.append(self.cum[j])
            self.joint_h.append(h)
        for j in range(len(self.joint_s) - 1):  # intervals must not overlap, or weights could go negative
            assert self.joint_s[j] + self.joint_h[j] <= self.joint_s[j + 1] - self.joint_h[j + 1] + 1e-9

    def weights(self, P):
        s, _ = project(P, self.pts)
        f = [smoothstep((s - sj + h) / (2 * h)) if h > 0 else (s > sj).astype(float)
             for sj, h in zip(self.joint_s, self.joint_h)]
        out = {}
        for k, name in enumerate(self.names):
            lo = 1.0 if k == 0 else f[k - 1]
            hi = 0.0 if k == len(self.names) - 1 else f[k]
            out[name] = lo - hi
        return out


# ---------------------------------------------------------------- the skeleton

def spine_point(rings, y):
    return np.array([0.0, y, float(np.interp(y, [r[0] for r in rings], [r[1] for r in rings]))])


def head_geometry(spec_head, mirror):
    h = dict(spec_head)
    if mirror:
        h["base"], h["dir"] = g.mirror(h["base"]), g.mirror(h["dir"])
    s = h["scale"]
    base, f = V(h["base"]), V(g.norm(h["dir"]))
    u = V(g.perpendicular(tuple(f), g.UP))
    side = V(g.cross(tuple(f), tuple(u)))
    jaw_dir = V(g.rotate(tuple(f), tuple(side), -h["jaw_open_deg"] * 0.7))
    beak_base = base + f * 0.36 * s
    jaw_head = beak_base + u * (-0.04 * s)
    return dict(base=base, f=f, u=u, s=s, head_tail=base + f * 0.40 * s, jaw_head=jaw_head,
                jaw_tail=jaw_head + jaw_dir * 0.37 * s)


def crown_root(parts_by_name, prefix):
    roots = [np.array(parts_by_name[f"{prefix}_branch{k}"]["sweep"]["path"][0]) for k in (0, 1)]
    return (roots[0] + roots[1]) / 2


def finger_joint(part):
    path = np.array(part["sweep"]["path"])
    cum = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))])
    return path, np.array([np.interp(0.55 * cum[-1], cum, path[:, c]) for c in range(3)])


def build_skeleton(spec, parts):
    """bones: {name: (head, tail, parent)} in creation order, and chains keyed by design side tag."""
    D = spec["design"]
    by_name = {p["name"]: p for p in parts}
    bones, chains = {}, {}

    def bone(name, head, tail, parent):
        bones[name] = (np.array(head, dtype=float), np.array(tail, dtype=float), parent)

    rings = D["body_rings"]["rings"]
    bone("root", (0, 0, 0), (0, 0, 0.3), None)
    sp = [spine_point(rings, y) for y in [1.3, 0.5, -0.2, -0.8, -1.35]]
    spine = ["pelvis", "spine_1", "spine_2", "spine_3"]
    for i, name in enumerate(spine):
        bone(name, sp[i], sp[i + 1], "root" if i == 0 else spine[i - 1])
    chains["spine"] = Chain(spine, sp)

    T = D["tail"]
    tdir = V(g.norm((0.0, 1.0, T["rise"])))
    t0 = V(T["root"])
    t1, t2 = t0 + tdir * T["length"] * 0.5, t0 + tdir * T["length"]
    bone("tail_1", t0, t1, "pelvis")
    bone("tail_2", t1, t2, "tail_1")
    chains["tail"] = Chain(["tail_1", "tail_2"], [t0, t1, t2], "pelvis", spine_point(rings, 1.0))

    def neck_chain(key, nbones, path, hd, label, crown_prefix, tongue=False):
        pts = resample(path, nbones)
        names = [f"neck_{label}_{i + 1}" for i in range(nbones)]
        for i, n in enumerate(names):
            bone(n, pts[i], pts[i + 1], "spine_3" if i == 0 else names[i - 1])
        head_n, jaw_n, crown_n = f"head_{label}", f"jaw_{label}", f"crown_{label}"
        bone(head_n, hd["base"], hd["head_tail"], names[-1])
        bone(jaw_n, hd["jaw_head"], hd["jaw_tail"], head_n)
        root = crown_root(by_name, crown_prefix)
        bone(crown_n, root, root + hd["u"] * 0.3 * hd["s"], head_n)
        chains[key] = Chain(names + [head_n], pts + [hd["head_tail"]], "spine_3", spine_point(rings, -0.55),
                            anchor_h=0.2)
        if V2 and tongue:  # three bones along the tongue's own path, hanging off the jaw
            path_t = np.array(by_name[f"{crown_prefix}_tongue"]["sweep"]["path"])
            cum = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(path_t, axis=0), axis=1))])
            tp = [np.array([np.interp(f * cum[-1], cum, path_t[:, c]) for c in range(3)]) for f in np.linspace(0, 1, TONGUE_BONES + 1)]
            tn = [f"tongue_{label}_{i + 1}" for i in range(TONGUE_BONES)]
            for i, n in enumerate(tn):
                bone(n, tp[i], tp[i + 1], jaw_n if i == 0 else tn[i - 1])
            chains[f"tongue_{label}"] = Chain(tn, tp, jaw_n, tp[0] - (tp[1] - tp[0]), hfrac=0.5, anchor_h=0.05)

    neck_chain("neck_main", 7, D["main_neck"]["path"], head_geometry(D["main_head"], False), "main", "main",
               tongue=bool(D["main_head"].get("tongue")))
    for sign, tag in ((1, "R"), (-1, "L")):
        path = [p if sign > 0 else g.mirror(p) for p in D["side_neck"]["path"]]
        neck_chain(f"neck_{tag}", 6, path, head_geometry(D["side_head"], sign < 0), bs(tag), f"side_{tag}",
                   tongue=bool(D["side_head"].get("tongue")))

    for sign, tag in ((1, "R"), (-1, "L")):
        b = bs(tag)
        pick = (lambda p: V(p)) if sign > 0 else (lambda p: V(g.mirror(p)))
        W = D["wing"]
        sh, el, wr, tp = (pick(W[k]) for k in ("shoulder", "elbow", "wrist", "tip"))
        names = [f"wing_shoulder.{b}", f"wing_upper.{b}", f"wing_fore.{b}", f"wing_hand.{b}"]
        pts = [sh, sh + (el - sh) * 0.3, el, wr, tp]
        for i, n in enumerate(names):
            bone(n, pts[i], pts[i + 1], "spine_2" if i == 0 else names[i - 1])
        chains[f"wing_{tag}"] = Chain(names, pts, "spine_2", spine_point(rings, -0.55), hfrac=0.4)
        for k in range(W["finger_bones"]):
            path, joint = finger_joint(by_name[f"finger_bone{k}_{tag}"])
            first, second = f"wing_finger_{2 * k + 1}.{b}", f"wing_finger_{2 * k + 2}.{b}"
            bone(first, path[0], joint, f"wing_hand.{b}")
            bone(second, joint, path[-1], first)

        L = D["legs"]
        hip, knee, ankle, foot = (pick(L[k]) for k in ("hip", "knee", "ankle", "foot"))
        toe_end = foot + V((0.0, -1.0, 0.0)) * L["toe_length"]
        toe_end[2] = GROUND_TOE_Z
        lnames = [f"leg_thigh.{b}", f"leg_shin.{b}", f"leg_tarsus.{b}", f"leg_toes.{b}"]
        lpts = [hip, knee, ankle, foot, toe_end]
        for i, n in enumerate(lnames):
            bone(n, lpts[i], lpts[i + 1], "pelvis" if i == 0 else lnames[i - 1])
        chains[f"leg_{tag}"] = Chain(lnames, lpts, "spine_1", spine_point(rings, -0.15), hfrac=0.4, anchor_h=0.1)
    return bones, chains


# ---------------------------------------------------------------- mapping parts to bones

def classify(name):
    """How a part is skinned: ('soft', chain) | ('root', chain) | ('bone', bone) | ('fingers', tag, k) | None.
    Chains are keyed by goose_design's side tag; bone names use bs(tag)."""
    m = re.fullmatch(r"(main|side_R|side_L)_(.+)", name)
    if m:
        p, rest = m.groups()
        label = "main" if p == "main" else bs(p[-1])
        chain = "neck_main" if p == "main" else f"neck_{p[-1]}"
        if rest == "head":
            return ("soft", chain)
        if V2 and rest == "tongue":
            return ("soft", f"tongue_{label}")
        if V2 and re.fullmatch(r"tongue_spike\d+_-?\d+", rest):
            return ("nearest", f"tongue_{label}")
        if re.fullmatch(r"(brow_[RL]|eye_[RL]|upper_beak|upper_tooth\d+_-?\d+|cheek_split_[RL]|"
                        r"cheek_tooth\d+_[RL]_-?\d+|mouth)", rest):
            return ("bone", f"head_{label}")
        if re.fullmatch(r"(lower_beak|lower_tooth\d+_-?\d+|tongue|tongue_spike\d+_-?\d+)", rest):
            return ("bone", f"jaw_{label}")
        if rest.startswith("branch") or rest.startswith("torn_skin"):
            return ("bone", f"crown_{label}")
    if name == "body":
        return ("soft", "spine")
    if re.fullmatch(r"rib\d+_[RL]|back_spine\d+_\d+|breast_feather\d+_\d+", name):
        return ("root", "spine")
    if name == "main_neck":
        return ("soft", "neck_main")
    if re.fullmatch(r"main_neck_hackle\d+|neck_spine\d+", name):
        return ("root", "neck_main")
    m = re.fullmatch(r"side_neck_([RL])", name)
    if m:
        return ("soft", f"neck_{m.group(1)}")
    m = re.fullmatch(r"side_neck_([RL])_hackle\d+", name)
    if m:
        return ("root", f"neck_{m.group(1)}")
    m = re.fullmatch(r"wing_arm_([RL])", name)
    if m:
        return ("soft", f"wing_{m.group(1)}")
    m = re.fullmatch(r"(?:primary|secondary|tertial|covert|lesser_covert)\d+_([RL])", name)
    if m:
        return ("root", f"wing_{m.group(1)}")
    m = re.fullmatch(r"finger_bone(\d)_([RL])", name)
    if m:
        return ("fingers", m.group(2), int(m.group(1)))
    m = re.fullmatch(r"(?:knuckle|finger_claw)(\d)_([RL])", name)
    if m:
        return ("bone", f"wing_finger_{2 * int(m.group(1)) + 2}.{bs(m.group(2))}")
    m = re.fullmatch(r"leg_([RL])", name)
    if m:
        return ("soft", f"leg_{m.group(1)}")
    m = re.fullmatch(r"scute\d+_([RL])", name)
    if m:
        return ("bone", f"leg_tarsus.{bs(m.group(1))}")
    m = re.fullmatch(r"(?:toe\d|claw\d|web\d|hallux)_([RL])", name)
    if m:
        return ("bone", f"leg_toes.{bs(m.group(1))}")
    if re.fullmatch(r"tail\d+", name):
        return ("soft", "tail")
    return None


def chain_id(bone_name):
    """Which anatomical chain a bone belongs to, for the cross-chain check."""
    if re.fullmatch(r"root|pelvis|spine_\d", bone_name):
        return "axial"
    if bone_name.startswith("tail_"):
        return "tail"
    m = re.fullmatch(r"(?:neck_(main|R|L)_\d+|head_(main|R|L)|jaw_(main|R|L)|crown_(main|R|L)|tongue_(main|R|L)_\d+)", bone_name)
    if m:
        return "neck_" + next(x for x in m.groups() if x)
    m = re.fullmatch(r"wing_\w+\.([RL])", bone_name)
    if m:
        return "wing_" + m.group(1)
    m = re.fullmatch(r"leg_\w+\.([RL])", bone_name)
    if m:
        return "leg_" + m.group(1)
    die(f"bone {bone_name} has no chain")


def compute_weights(parts, bones, chains, nverts):
    names = list(bones)
    col = {n: i for i, n in enumerate(names)}
    W = np.zeros((nverts, len(names)))
    scratch = g.Mesh()
    ranges = []
    for part in parts:
        if part["kind"] == "decal":
            continue
        a = len(scratch.verts)
        (g._mesh_ellipsoid if part["kind"] == "ellipsoid" else g._mesh_loft)(part, scratch)
        ranges.append((part, a, len(scratch.verts)))
    if len(scratch.verts) != nverts:
        die(f"design meshes to {len(scratch.verts)} vertices but goose.blend has {nverts}: rebuild goose.blend first")
    P_all = np.array(scratch.verts, dtype=float)
    stats = {"soft": 0, "root": 0, "bone": 0, "fingers": 0, "nearest": 0}
    for part, a, b in ranges:
        P = P_all[a:b]
        how = classify(part["name"])
        if how is None:
            die(f"no skinning rule for part '{part['name']}'")
        kind = how[0]
        stats[kind] += 1
        if kind == "bone":
            if how[1] not in col:
                die(f"part '{part['name']}' maps to missing bone {how[1]}")
            W[a:b, col[how[1]]] = 1.0
        elif kind == "soft":
            for n, w in chains[how[1]].weights(P).items():
                W[a:b, col[n]] = w
        elif kind == "nearest":  # rigid on the nearest bone of the chain (the tongue spikes)
            ch = chains[how[1]]
            _, d = project(P, ch.pts)
            root = P[int(np.argmin(d))][None, :]
            sroot, _ = project(root, ch.pts)
            i = int(np.searchsorted(ch.cum, sroot[0], side="right")) - 1
            bone_name = ch.names[min(max(i, 1), len(ch.names) - 1)]  # index 0 is the anchor, not a tongue bone
            W[a:b, col[bone_name]] = 1.0
        elif kind == "root":
            ch = chains[how[1]]
            _, d = project(P, ch.pts)
            root = P[int(np.argmin(d))][None, :]
            for n, w in ch.weights(root).items():
                W[a:b, col[n]] = w[0]
        else:  # fingers: hard split at the knuckle
            _, tag, k = how
            path, joint = finger_joint(part)
            first, second = f"wing_finger_{2 * k + 1}.{bs(tag)}", f"wing_finger_{2 * k + 2}.{bs(tag)}"
            s, _ = project(P, [path[0], joint, path[-1]])
            seg0 = np.linalg.norm(joint - path[0])
            W[a:b, col[first]] = (s <= seg0).astype(float)
            W[a:b, col[second]] = (s > seg0).astype(float)
    return W, names, stats, P_all


def validate_weights(W, names, bones, P):
    """Sum to 1, at most 3 influences, and cross-chain weight only near the other chain."""
    sums = W.sum(axis=1)
    if np.abs(sums - 1).max() > 1e-6 or W.min() < -1e-9:
        die(f"weights do not sum to 1 (worst {np.abs(sums - 1).max():.2e}) or are negative ({W.min():.2e})")
    infl = (W > 1e-4).sum(axis=1)
    if infl.max() > 3:
        die(f"{int((infl > 3).sum())} vertices have more than 3 bone influences (max {infl.max()})")
    cid = np.array([chain_id(n) for n in names])
    primary = cid[np.argmax(W, axis=1)]
    cross = np.zeros(len(W))
    for c in set(cid):
        cross += np.where(primary != c, W[:, cid == c].sum(axis=1), 0.0)
    crossers = np.where(cross > 1e-4)[0]
    worst = 0.0
    for c in set(cid):  # distance from a cross-weighted vertex to the nearest bone of the chain it leaks into
        in_c = np.where(cid == c)[0]
        rows = crossers[(primary[crossers] != c) & (W[crossers][:, in_c].sum(axis=1) > 1e-4)]
        if not len(rows):
            continue
        d = np.full(len(rows), np.inf)
        for i in in_c:
            h, t, _ = bones[names[i]]
            d = np.minimum(d, project(P[rows], [h, t])[1])
        worst = max(worst, d.max())
    frac = len(crossers) / len(W)
    if worst > 1.25 or frac > 0.06:
        die(f"cross-chain weights too wide: {len(crossers)} vertices ({frac:.1%}), up to {worst:.2f} m from the other chain")
    return infl.max(), len(crossers), frac, worst, cross.max()


# ---------------------------------------------------------------- Blender side

def make_armature(bones):
    arm_data = bpy.data.armatures.new("goose_rig")
    arm = bpy.data.objects.new("goose_rig", arm_data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for name, (head, tail, _) in bones.items():
        eb = arm_data.edit_bones.new(name)
        eb.head, eb.tail = Vector(head), Vector(tail)
        if eb.length < 1e-4:
            die(f"bone {name} has zero length")
    for name, (_, _, parent) in bones.items():
        if parent:
            arm_data.edit_bones[name].parent = arm_data.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm


def build():
    t0 = time.time()
    spec = g.load_spec()
    src = os.path.join(HERE, "goose.blend")
    if not os.path.isfile(src):
        die(f"{src} not found; run build_goose.py first")
    bpy.ops.wm.open_mainfile(filepath=src)
    obj = bpy.data.objects.get(spec["slug"])
    if obj is None:
        die(f"goose.blend has no object '{spec['slug']}'")
    parts = g.build_parts(spec)
    bones, chains = build_skeleton(spec, parts)
    expected = BONE_COUNT + (TONGUE_BONES * sum(1 for h in ("main_head", "side_head", "side_head") if spec["design"][h].get("tongue")) if V2 else 0)
    if len(bones) != expected:
        die(f"{len(bones)} bones built, expected {expected}")
    print(f"build_rig: {len(bones)} bones")
    mesh = obj.data
    nv = len(mesh.vertices)
    W, names, stats, P_design = compute_weights(parts, bones, chains, nv)
    P = np.array([v.co[:] for v in mesh.vertices])
    if np.abs(P_design - P).max() > 1e-4:
        die("goose.blend vertices differ from the design: rebuild goose.blend first")
    infl, ncross, frac, worst, maxcross = validate_weights(W, names, bones, P)

    arm = make_armature(bones)
    for n in names:
        obj.vertex_groups.new(name=n)
    rows, cols = np.nonzero(W > 1e-6)
    for r, c in zip(rows.tolist(), cols.tolist()):
        obj.vertex_groups[c].add([r], float(W[r, c]), "REPLACE")
    worst_sum = max(abs(sum(gr.weight for gr in v.groups) - 1) for v in mesh.vertices)  # read back
    obj.parent = arm
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    print(f"build_rig: parts skinned {stats}")
    print(f"build_rig: weight check: {nv} vertices, sums to 1 (worst read-back error {worst_sum:.2e}), "
          f"max {infl} influences, cross-chain weight on {ncross} vertices ({frac:.2%}, "
          f"max {maxcross:.2f}, within {worst:.2f} m of the other chain)")
    out = os.path.join(HERE, OUT_NAME)
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    print(f"build_rig: wrote {out} in {time.time() - t0:.1f} s")


def rot_world(arm, bone_names, axis, degrees):
    for n in bone_names:
        pb = arm.pose.bones[n]
        head = arm.matrix_world @ pb.head
        rot = Matrix.Translation(head) @ Matrix.Rotation(math.radians(degrees), 4, axis) @ Matrix.Translation(-head)
        pb.matrix = rot @ pb.matrix
        bpy.context.view_layer.update()


def pose_test(out_path):
    t0 = time.time()
    src = os.path.join(HERE, "goose_rigged.blend")
    if not os.path.isfile(src):
        die(f"{src} not found; run build_rig.py first")
    bpy.ops.wm.open_mainfile(filepath=src)
    arm = bpy.data.objects["goose_rig"]
    obj = bpy.data.objects[g.load_spec()["slug"]]
    if len(arm.data.bones) != BONE_COUNT:
        die(f"{len(arm.data.bones)} bones in goose_rigged.blend, expected {BONE_COUNT}")
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
    neck = [f"neck_main_{i}" for i in range(1, 8)]
    rot_world(arm, neck, "Z", 40 / 7)  # main neck turned 40 degrees in total
    rot_world(arm, neck, "X", 2)
    rot_world(arm, [f"neck_L_{i}" for i in range(1, 7)], "X", 15)  # left (+X) neck bent down and forward
    rot_world(arm, ["wing_shoulder.R"], "Y", 45)  # right (-X) wing raised 45 degrees
    rot_world(arm, ["leg_thigh.L"], "X", -55)  # left (+X) knee lifted
    rot_world(arm, ["leg_shin.L"], "X", 100)
    arm.pose.bones["crown_main"].scale = (1.5, 1.5, 1.5)
    bpy.context.view_layer.update()
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m = ev.to_mesh()
    co = np.array([v.co[:] for v in m.vertices])
    ev.to_mesh_clear()
    zmin = float(co[:, 2].min())
    print(f"pose_test: evaluated {len(co)} vertices, min z {zmin:.4f} m, max z {co[:, 2].max():.3f} m, "
          f"x {co[:, 0].min():.2f}..{co[:, 0].max():.2f}")
    if zmin < -FLOOR_TOLERANCE_M:
        die(f"posed mesh goes below the floor: min z {zmin:.4f} m")
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out_path), compress=True)
    print(f"pose_test: saved {out_path} in {time.time() - t0:.1f} s")


def pose_test_v2(out_path):
    """Jaws wide open and the tongues lolled out and down over the lower beaks."""
    t0 = time.time()
    src = os.path.join(HERE, "goose_rigged_v2.blend")
    if not os.path.isfile(src):
        die(f"{src} not found; run build_rig.py --v2 first")
    bpy.ops.wm.open_mainfile(filepath=src)
    arm = bpy.data.objects["goose_rig"]
    obj = bpy.data.objects[g.load_spec()["slug"]]
    names = [b.name for b in arm.data.bones]
    if len(names) != 68:
        die(f"{len(names)} bones in goose_rigged_v2.blend, expected 68")
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
    # heads tipped up a little so the open mouths show, jaws wide, tongues drooping over the lower beak
    for lab in ("main", "L", "R"):
        rot_world(arm, [f"head_{lab}"], "X", -14)
        rot_world(arm, [f"jaw_{lab}"], "X", 38)
        rot_world(arm, [f"tongue_{lab}_{i}" for i in (1, 2, 3)], "X", 34)
    bpy.context.view_layer.update()
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m = ev.to_mesh()
    co = np.array([v.co[:] for v in m.vertices])
    ev.to_mesh_clear()
    zmin = float(co[:, 2].min())
    print(f"pose_test_v2: evaluated {len(co)} vertices, min z {zmin:.4f} m, max z {co[:, 2].max():.3f} m")
    if zmin < -FLOOR_TOLERANCE_M:
        die(f"posed mesh goes below the floor: min z {zmin:.4f} m")
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out_path), compress=True)
    print(f"pose_test_v2: saved {out_path} in {time.time() - t0:.1f} s")


def closeups(posed, outdir):
    """Close-up renders of the three heads from the side and three-quarter (render_views.py frames the whole goose)."""
    from PIL import Image
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(posed))
    arm = bpy.data.objects["goose_rig"]
    sc = bpy.context.scene
    for o in [o for o in bpy.data.objects if o.type in ("CAMERA", "LIGHT")]:
        bpy.data.objects.remove(o)
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 24
    sc.cycles.use_denoising = True
    sc.render.resolution_x = sc.render.resolution_y = 700
    sc.view_settings.view_transform = "AgX"
    sc.render.film_transparent = True
    w = bpy.data.worlds.new("W")
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.03, 0.022, 0.015, 1)
    os.makedirs(outdir, exist_ok=True)
    arm.update_tag()
    bpy.context.view_layer.update()
    for lab in ("main", "L", "R"):
        head = arm.pose.bones[f"head_{lab}"].head.copy()
        jaw = arm.pose.bones[f"jaw_{lab}"]
        centre = (head + jaw.tail) / 2
        for view, yaw in (("side", 90.0), ("threequarter", -40.0)):
            for o in [o for o in bpy.data.objects if o.type in ("CAMERA", "LIGHT")]:
                bpy.data.objects.remove(o)
            yawr, pit = math.radians(yaw), math.radians(12)
            toward = Vector((math.sin(yawr) * math.cos(pit), -math.cos(yawr) * math.cos(pit), math.sin(pit)))
            cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
            cam.data.type = "ORTHO"
            cam.data.ortho_scale = 1.6
            cam.data.clip_start, cam.data.clip_end = 0.01, 200
            cam.location = centre + toward * 20
            cam.rotation_euler = (-toward).to_track_quat("-Z", "Y").to_euler()
            sc.collection.objects.link(cam)
            sc.camera = cam
            for nm, pos, en in (("Key", (0.8, -1.0, 0.9), 1500.0), ("Fill", (-1.0, -0.6, 0.3), 400.0)):
                ld = bpy.data.lights.new(nm, "AREA")
                ld.energy, ld.size = en, 6.0
                lo = bpy.data.objects.new(nm, ld)
                lo.location = centre + Vector(pos) * 8
                lo.rotation_euler = (centre - lo.location).to_track_quat("-Z", "Y").to_euler()
                sc.collection.objects.link(lo)
            path = os.path.join(outdir, f"closeup_{lab}_{view}.png")
            sc.render.filepath = path
            bpy.ops.render.render(write_still=True)
            flat = Image.new("RGBA", (700, 700), (0xED, 0xE6, 0xD6, 255))
            Image.alpha_composite(flat, Image.open(path).convert("RGBA")).convert("RGB").save(path)
            bpy.data.objects.remove(cam)
    print(f"closeups: wrote 6 renders to {outdir}")


def main():
    if "--closeup" in sys.argv:
        i = sys.argv.index("--closeup")
        if i + 2 >= len(sys.argv):
            die("--closeup needs POSED.blend and an output folder")
        closeups(sys.argv[i + 1], sys.argv[i + 2])
    elif V2 and "--pose-test" in sys.argv:
        i = sys.argv.index("--pose-test")
        if i + 1 >= len(sys.argv):
            die("--pose-test needs an output .blend path")
        pose_test_v2(sys.argv[i + 1])
    elif "--pose-test" in sys.argv:
        i = sys.argv.index("--pose-test")
        if i + 1 >= len(sys.argv):
            die("--pose-test needs an output .blend path")
        pose_test(sys.argv[i + 1])
    else:
        build()


main()
