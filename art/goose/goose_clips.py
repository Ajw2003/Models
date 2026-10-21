#!/usr/bin/env python3
"""The goose's supporting clips: idle, walk, turn_in_place, stagger, death, as Blender Actions.

  python3.11 art/goose/goose_clips.py build            # goose_rigged.blend -> goose_animated.blend + clips/metrics.json
  python3.11 art/goose/goose_clips.py render [CLIP..]  # per clip: 8-still contact sheet + MP4 under art/goose/clips/

Loads goose_rigged.blend (mesh and rig untouched) and writes goose_animated.blend with five Actions
(fake user set), 30 fps. A pose is a dict {bone: entry} where an entry is a dict of
  rot   (rx, ry, rz) degrees about the WORLD axes through the bone's head, applied to the rest pose
  t     (x, y, z) world translation in metres
  aim   a world direction the bone is turned to point along (used for the leg IK)
  scale uniform scale (crowns)
World axes: +X is the goose's left, it faces -Y, +Z up. Rotation about X with a positive angle tips an
upright bone forward and down; about Y it tips +X down; about Z it turns left (counter-clockwise).
Legs are solved with a two-bone IK onto foot targets, so planted feet stay planted while the body
moves; each pose is converted to local bone channels and keyed (Bezier, auto-clamped handles, which
ease in and out), with extra keys placed for anticipation and overshoot.

Clips (frame 0 is the first pose; loops end on a duplicate of frame 0):
  idle           loop, 4.0 s: breathing, neck sway, crowns creaking, wings settling
  walk           loop, 1.6 s, in place: the root never moves, planted feet slide backward at the
                 implied ground speed (stride / stance time), which the metrics measure
  turn_in_place  one-shot, 1.5 s: 90 degrees to the right (-X) with three/two stepping feet
  stagger        one-shot, 1.2 s: recoil, heads reel back, recover to the idle pose
  death          one-shot, 4.0 s: legs buckle, collapse onto its left side, necks fall last
"""
import json, math, os, sys, time

try:
    import bpy
    import numpy as np
    from mathutils import Matrix, Vector
except ImportError:
    sys.exit("goose_clips.py: cannot import bpy/numpy; run it with the interpreter from setup_bpy.sh")

HERE = os.path.dirname(os.path.abspath(__file__))
CLIPS_DIR = os.path.join(HERE, "clips")
FPS = 30
FLOOR_TOL = 0.01
UP = Vector((0, 0, 1))
FWD = Vector((0, -1, 0))
SLUG = "eldritch_goose"


def die(msg):
    sys.exit(f"goose_clips.py: {msg}")


# ---------------------------------------------------------------- curves

def pchip(points, t):
    """Smooth monotone-ish curve through (time, value) points, flat at both ends (Catmull-Rom tangents)."""
    ts = [p[0] for p in points]
    vs = [p[1] for p in points]
    if t <= ts[0]:
        return vs[0]
    if t >= ts[-1]:
        return vs[-1]
    i = max(k for k in range(len(ts) - 1) if ts[k] <= t)
    h = ts[i + 1] - ts[i]

    def tangent(k):
        if k == 0 or k == len(ts) - 1:
            return 0.0
        m = (vs[k + 1] - vs[k - 1]) / (ts[k + 1] - ts[k - 1])
        return m

    u = (t - ts[i]) / h
    h00, h10, h01, h11 = 2 * u**3 - 3 * u**2 + 1, u**3 - 2 * u**2 + u, -2 * u**3 + 3 * u**2, u**3 - u**2
    return h00 * vs[i] + h10 * h * tangent(i) + h01 * vs[i + 1] + h11 * h * tangent(i + 1)


def smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


# ---------------------------------------------------------------- pose arithmetic

def P(**kw):
    return kw


def add_pose(a, b, w=1.0):
    """a + w * b over rot / t / scale entries."""
    out = {k: dict(v) for k, v in a.items()}
    for bone, e in b.items():
        o = out.setdefault(bone, {})
        for key in ("rot", "t", "brot"):
            if key in e:
                cur = o.get(key, (0.0, 0.0, 0.0))
                o[key] = tuple(c + w * x for c, x in zip(cur, e[key]))
        if "scale" in e:
            o["scale"] = o.get("scale", 1.0) + w * (e["scale"] - 1.0)
    return out


def side_sign(side):
    return 1 if side == "L" else -1  # .L is +X


# ---------------------------------------------------------------- the rig in Blender

class Rig:
    def __init__(self, path):
        bpy.ops.wm.open_mainfile(filepath=path)
        self.arm = bpy.data.objects["goose_rig"]
        self.obj = bpy.data.objects[SLUG]
        self.mod = [m for m in self.obj.modifiers if m.type == "ARMATURE"][0]
        self.names = [b.name for b in self.arm.data.bones]  # parents before children
        bpy.context.view_layer.objects.active = self.arm
        bpy.ops.object.mode_set(mode="POSE")
        for pb in self.arm.pose.bones:
            pb.rotation_mode = "QUATERNION"
        self.len = {b.name: b.length for b in self.arm.data.bones}
        self.mod.show_viewport = False  # posing is cheap while the mesh does not follow
        self.reset()
        self.rest_hip = {s: self.arm.pose.bones[f"leg_thigh.{s}"].head.copy() for s in "LR"}
        self.rest_foot = {s: self.arm.pose.bones[f"leg_toes.{s}"].head.copy() for s in "LR"}

    def update(self):
        bpy.context.view_layer.update()

    def reset(self):
        for pb in self.arm.pose.bones:
            pb.location = (0, 0, 0)
            pb.rotation_quaternion = (1, 0, 0, 0)
            pb.scale = (1, 1, 1)
        self.update()

    def apply_entry(self, name, e):
        pb = self.arm.pose.bones[name]
        head = pb.head.copy()
        M = Matrix.Identity(4)
        if "aim" in e:
            cur = (pb.tail - pb.head).normalized()
            q = cur.rotation_difference(Vector(e["aim"]).normalized())
            M = Matrix.Translation(head) @ q.to_matrix().to_4x4() @ Matrix.Translation(-head)
        if "orient" in e:  # full world orientation relative to the rest bone, so roll is controlled too
            rest3 = self.arm.data.bones[name].matrix_local.to_3x3()
            cur3 = pb.matrix.to_3x3().normalized()
            delta = (e["orient"] @ rest3) @ cur3.inverted()
            M = Matrix.Translation(head) @ delta.to_4x4() @ Matrix.Translation(-head)
        if "brot" in e:  # rotation about the BODY's axes (the pelvis frame), e.g. to fold a wing on a body lying on its side
            rx, ry, rz = (math.radians(a) for a in e["brot"])
            R = Matrix.Rotation(rz, 3, "Z") @ Matrix.Rotation(ry, 3, "Y") @ Matrix.Rotation(rx, 3, "X")
            B = self.body_matrix().to_3x3().normalized()
            M = Matrix.Translation(head) @ (B @ R @ B.inverted()).to_4x4() @ Matrix.Translation(-head) @ M
        if "rot" in e:
            rx, ry, rz = (math.radians(a) for a in e["rot"])
            R = Matrix.Rotation(rz, 4, "Z") @ Matrix.Rotation(ry, 4, "Y") @ Matrix.Rotation(rx, 4, "X")
            M = Matrix.Translation(head) @ R @ Matrix.Translation(-head) @ M
        if "t" in e:
            M = Matrix.Translation(Vector(e["t"])) @ M
        pb.matrix = M @ pb.matrix
        if "scale" in e:
            s = e["scale"]
            pb.scale = (s, s, s)
        self.update()

    def apply_pose(self, pose, legs=None):
        self.reset()
        for n in self.names:
            if n in pose:
                self.apply_entry(n, pose[n])
        if legs:
            aims = legs(self)
            for n in self.names:
                if n in aims:
                    self.apply_entry(n, aims[n])

    def channels(self):
        return {pb.name: (tuple(pb.location), tuple(pb.rotation_quaternion), tuple(pb.scale))
                for pb in self.arm.pose.bones}

    def body_matrix(self):
        """Rigid motion of the body relative to rest: the pelvis bone's pose matrix times the inverse of its rest."""
        b = self.arm.data.bones["pelvis"]
        rest = self.arm.matrix_world @ b.matrix_local
        return self.arm.pose.bones["pelvis"].matrix @ rest.inverted()

    def min_z(self):
        self.mod.show_viewport = True
        dg = bpy.context.evaluated_depsgraph_get()
        ev = self.obj.evaluated_get(dg)
        m = ev.to_mesh()
        co = np.empty(len(m.vertices) * 3)
        m.vertices.foreach_get("co", co)
        ev.to_mesh_clear()
        self.mod.show_viewport = False
        return float(co[2::3].min())

    # --- two-bone leg IK onto a foot target
    def leg_aims(self, side, foot, facing, phi_deg=10.0, toe_deg=7.0):
        th = self.arm.pose.bones[f"leg_thigh.{side}"]
        hip = th.head.copy()
        L1, L2, Lt = self.len[f"leg_thigh.{side}"], self.len[f"leg_shin.{side}"], self.len[f"leg_tarsus.{side}"]
        phi = math.radians(phi_deg)
        tvec = (facing * math.sin(phi) - UP * math.cos(phi)) * Lt
        ankle = Vector(foot) - tvec
        d = ankle - hip
        dist = d.length
        reach = L1 + L2 - 1e-3
        err = max(0.0, dist - reach)
        dist = min(max(dist, abs(L1 - L2) + 1e-3), reach)
        e = d.normalized()
        a = (L1 * L1 - L2 * L2 + dist * dist) / (2 * dist)
        h = math.sqrt(max(L1 * L1 - a * a, 0.0))
        n = facing - e * facing.dot(e)
        n = n.normalized() if n.length > 1e-6 else facing
        knee = hip + e * a + n * h
        ankle = hip + e * dist
        tp = math.radians(toe_deg)
        self.reach_err = max(getattr(self, "reach_err", 0.0), err)
        return {f"leg_thigh.{side}": {"aim": tuple(knee - hip)},
                f"leg_shin.{side}": {"aim": tuple(ankle - knee)},
                f"leg_tarsus.{side}": {"aim": tuple(tvec)},
                f"leg_toes.{side}": {"orient": Matrix.Rotation(tp - math.radians(7.0), 3, UP.cross(facing))
                                     @ Matrix.Rotation(math.atan2(facing.x, -facing.y), 3, "Z")}}


def planted(rig, facing=FWD, foot_override=None):
    """Legs callback: both feet planted where they stand at rest (or at foot_override[side])."""
    def legs(r):
        out = {}
        for s in "LR":
            f = foot_override[s] if foot_override and s in foot_override else r.rest_foot[s]
            out.update(r.leg_aims(s, f, facing))
        return out
    return legs


# ---------------------------------------------------------------- the pose library (named poses)

NECK_MAIN = [f"neck_main_{i}" for i in range(1, 8)]
NECK_L = [f"neck_L_{i}" for i in range(1, 7)]
NECK_R = [f"neck_R_{i}" for i in range(1, 7)]
HEADS = ["head_main", "head_L", "head_R"]
JAWS = ["jaw_main", "jaw_L", "jaw_R"]
CROWNS = ["crown_main", "crown_L", "crown_R"]
NECKS = {"main": NECK_MAIN, "L": NECK_L, "R": NECK_R}
WING = ["wing_shoulder", "wing_upper", "wing_fore", "wing_hand"]


def neck_pose(chain, x=0.0, y=0.0, z=0.0, head=None):
    """Spread (x, y, z) world-axis degrees evenly over a neck chain, optionally extra on its head bone."""
    out = {n: {"rot": (x / len(chain), y / len(chain), z / len(chain))} for n in chain}
    return out


def wing_pose(side, lower=0.0, sweep=0.0, fore=0.0, hand=0.0):
    """Lower the wing (degrees), sweep it back about Z, and bend fore / hand further."""
    s = side_sign(side)
    return {f"wing_shoulder.{side}": {"rot": (0, s * lower, s * sweep)},
            f"wing_fore.{side}": {"rot": (0, s * fore, s * fore * 0.5 * 0 + 0)},
            f"wing_hand.{side}": {"rot": (0, s * hand, 0)}}


# recoil: the hit snaps the body back and throws every head back
RECOIL = {"root": {"rot": (-6, 0, 0)}, "pelvis": {"t": (0, 0.22, -0.10)},
          "spine_3": {"rot": (-4, 0, 0)}}
for _k, _chain in NECKS.items():
    RECOIL = add_pose(RECOIL, neck_pose(_chain, x=-62 if _k == "main" else -54))
for _h in HEADS:
    RECOIL = add_pose(RECOIL, {_h: {"rot": (-14, 0, 0)}})
for _j in JAWS:
    RECOIL = add_pose(RECOIL, {_j: {"rot": (12, 0, 0)}})
for _s in "LR":
    RECOIL = add_pose(RECOIL, wing_pose(_s, lower=-14, hand=-6))
RECOIL = add_pose(RECOIL, {"crown_main": {"scale": 1.12}, "crown_L": {"scale": 1.12}, "crown_R": {"scale": 1.12}})


# ---------------------------------------------------------------- clips: pose as a function of time

def idle_pose(t, T=4.0):
    s = t / T
    w = 2 * math.pi * s
    p = {"pelvis": {"t": (0, 0, 0.018 * math.sin(2 * w))},
         "spine_2": {"rot": (1.0 * math.sin(2 * w), 0, 0)},
         "spine_3": {"rot": (1.5 * math.sin(2 * w - 0.4), 0, 0)}}
    for i, n in enumerate(NECK_MAIN):
        p[n] = {"rot": (1.0 * math.sin(w + 0.28 * i), 0, 1.7 * math.sin(w + 0.28 * i + 1.3))}
    for i, n in enumerate(NECK_L):
        p[n] = {"rot": (1.3 * math.sin(w + 0.3 * i + 1.0), 0, 2.0 * math.sin(w + 0.3 * i + 2.5))}
    for i, n in enumerate(NECK_R):
        p[n] = {"rot": (1.3 * math.sin(w + 0.3 * i + 3.0), 0, 2.0 * math.sin(w + 0.3 * i + 4.1))}
    for k, (h, j) in enumerate(zip(HEADS, JAWS)):
        p[h] = {"rot": (2.5 * math.sin(w + 0.9 * k + 0.6), 0, 0)}
        p[j] = {"rot": (2.0 + 1.5 * math.sin(2 * w + k), 0, 0)}
    for k, c in enumerate(CROWNS):  # creaking: slow twist, a touch of growth
        p[c] = {"rot": (0, 2.0 * math.sin(2 * w + 1.7 * k), 2.5 * math.sin(2 * w + 1.7 * k + 0.8)),
                "scale": 1.0 + 0.015 * math.sin(2 * w + k)}
    for s in "LR":  # wings settling: a slow droop and lift with the fore and hand trailing
        sg = side_sign(s)
        p[f"wing_shoulder.{s}"] = {"rot": (0, sg * 3.0 * math.sin(w + 0.4 * (s == "R")), 0)}
        p[f"wing_upper.{s}"] = {"rot": (0, sg * 2.0 * math.sin(w - 0.5 + 0.4 * (s == "R")), 0)}
        p[f"wing_fore.{s}"] = {"rot": (0, sg * 2.5 * math.sin(w - 1.0 + 0.4 * (s == "R")), 0)}
        p[f"wing_hand.{s}"] = {"rot": (0, sg * 3.0 * math.sin(w - 1.5 + 0.4 * (s == "R")), 0)}
    return p


WALK_T = 1.6
WALK_STRIDE = 0.6
WALK_DUTY = 0.6
WALK_DROP = 0.12
WALK_REST_FOOT = {}
WALK_GROUND_SPEED = WALK_STRIDE / (WALK_DUTY * WALK_T)  # m/s the planted foot slides backward


def walk_body(t):
    p = (t / WALK_T) % 1.0
    w = 2 * math.pi * p
    body = {"pelvis": {"t": (0.07 * math.sin(w), 0, -WALK_DROP + 0.03 * math.cos(2 * w)),
                       "rot": (0, 3.5 * math.sin(w), 0)},
            "spine_1": {"rot": (0, 0, 2.5 * math.sin(w))},
            "spine_3": {"rot": (0, -2.0 * math.sin(w), 0)}}
    for i, n in enumerate(NECK_MAIN):  # the neck bobs against the body and the head stays steady
        body[n] = {"rot": (1.3 * math.sin(2 * w + 0.4 + 0.2 * i), 0, 0.9 * math.sin(w + 0.3 * i))}
    for i, n in enumerate(NECK_L):
        body[n] = {"rot": (1.7 * math.sin(2 * w + 0.9 + 0.25 * i), 0, 1.6 * math.sin(w + 1.2 + 0.3 * i))}
    for i, n in enumerate(NECK_R):
        body[n] = {"rot": (1.7 * math.sin(2 * w + 1.5 + 0.25 * i), 0, 1.6 * math.sin(w + 3.2 + 0.3 * i))}
    for k, h in enumerate(HEADS):
        body[h] = {"rot": (-3.0 * math.sin(2 * w + 0.6 + k), 0, 0)}
    for s in "LR":
        sg = side_sign(s)
        body[f"wing_shoulder.{s}"] = {"rot": (0, sg * 2.5 * math.sin(2 * w + 0.5), 0)}
        body[f"wing_fore.{s}"] = {"rot": (0, sg * 3.0 * math.sin(2 * w - 0.3), 0)}
    for k, c in enumerate(CROWNS):
        body[c] = {"rot": (0, 0, 2.0 * math.sin(2 * w + k))}
    return body


def walk_foot(side, t):
    """World foot target for the walk: stance slides back at the ground speed, swing arcs forward."""
    p = ((t / WALK_T) + (0.0 if side == "L" else 0.5)) % 1.0
    f0 = Vector(WALK_REST_FOOT[side])
    half = WALK_STRIDE / 2
    if p < WALK_DUTY:
        u = half - WALK_STRIDE * (p / WALK_DUTY)  # forward offset (metres, + is forward = -Y)
        lift = 0.0
    else:
        q = (p - WALK_DUTY) / (1 - WALK_DUTY)
        u = -half + WALK_STRIDE * smooth(q)
        lift = 0.34 * math.sin(math.pi * q) ** 1.2
    toe = 7.0 if p < WALK_DUTY else 7.0 - 20.0 * math.sin(math.pi * ((p - WALK_DUTY) / (1 - WALK_DUTY)))
    return Vector((f0.x, f0.y - u, f0.z + lift)), toe


def stagger_pose(t):
    a = pchip([(0, 0), (0.05, -0.1), (0.2, 1.0), (0.45, 0.85), (0.8, -0.12), (1.0, 0.03), (1.2, 0)], t)
    return add_pose(idle_pose(0.0), RECOIL, a)


# turn: yaw of the root over time (degrees, negative is to the right, toward -X), with wind-up and overshoot
TURN_T = 1.5
YAW_KEYS = [(0, 0), (0.18, 5), (0.45, -22), (1.0, -75), (1.3, -93), (1.5, -90)]
STEPS = {"L": [(0.05, 0.35, -25), (0.65, 0.95, -60), (1.25, 1.5, -90)],
         "R": [(0.35, 0.65, -45), (0.95, 1.25, -90)]}


def yaw_at(t):
    return pchip(YAW_KEYS, t)


def turn_foot(rig, side, t):
    f0 = rig.rest_foot[side]
    def at(yaw):
        return Matrix.Rotation(math.radians(yaw), 4, "Z") @ f0
    pos_yaw, prev = 0.0, (at(0.0), 0.0)
    cur = (at(0.0), 0.0)
    for (a, b, land) in STEPS[side]:
        if t < a:
            break
        if t >= b:
            cur = (at(land), land)
            continue
        q = (t - a) / (b - a)
        start = cur
        end = at(land)
        pos = start[0].lerp(end, smooth(q))
        yaw = start[1] + (land - start[1]) * smooth(q)
        pos.z += 0.34 * math.sin(math.pi * q) ** 1.2
        return pos, yaw, 7.0 - 20.0 * math.sin(math.pi * q)
    return cur[0], cur[1], 7.0


def turn_body(t):
    yaw = yaw_at(t)
    lead = (yaw_at(min(t + 0.15, TURN_T)) - yaw)
    body = {"root": {"rot": (0, 0, yaw)}, "pelvis": {"t": (0, 0, -0.10 + 0.02 * math.sin(2 * math.pi * t / 0.6))}}
    for n in NECK_MAIN:
        body[n] = {"rot": (0, 0, lead * 0.55 / 7)}
    for chain in (NECK_L, NECK_R):
        for n in chain:
            body[n] = {"rot": (0, 0, lead * 0.8 / 6)}
    return add_pose(body, idle_pose(t * 0.0 + 0.0), 0.0)


DEATH_T = 4.0
T_BUCKLE, T_ROLL, T_NECKS = 0.35, 1.4, 2.2


def death_body(t, rig):
    """Body pose for the death at time t (without the floor fit)."""
    base = idle_pose(0.0)
    a_recoil = pchip([(0, 0), (0.06, -0.1), (0.3, 0.8), (0.9, 0.35), (1.4, 0.1)], t)
    drop = pchip([(0, 0), (0.35, 0), (0.9, 0.55), (1.2, 0.85), (1.4, 0.9)], t)
    pose = add_pose(base, RECOIL, a_recoil)
    pose = add_pose(pose, {"pelvis": {"t": (0, 0, -drop), "rot": (0, 0, 0)}})
    roll = pchip([(0, 0), (1.4, 0), (1.9, 28), (2.4, 84), (2.65, 94), (3.0, 90)], t)
    pitch = pchip([(0, 0), (1.2, 6), (1.4, 8), (3.0, 8)], t)
    pose = add_pose(pose, {"root": {"rot": (pitch * 0.3, roll, 0)}})
    # wings fold back along the flanks as it goes down
    fold = smooth((t - 0.9) / 1.2)
    for s in "LR":
        sg = side_sign(s)
        pose = add_pose(pose, {f"wing_shoulder.{s}": {"brot": (0, sg * 25 * fold, sg * 80 * fold)},
                               f"wing_upper.{s}": {"brot": (0, 0, sg * 10 * fold)},
                               f"wing_fore.{s}": {"brot": (0, 0, sg * 40 * fold)},
                               f"wing_hand.{s}": {"brot": (0, 0, sg * 70 * fold)}})
    # necks fall last: bend toward the floor (world Y once it lies on its side)
    fall = pchip([(0, 0), (T_NECKS, 0), (2.9, 0.75), (3.4, 1.05), (3.8, 1.0), (4.0, 1.0)], t)
    for k, chain in NECKS.items():
        amt = (70 if k == "main" else 62) * fall
        pose = add_pose(pose, {n: {"brot": (0, amt / len(chain), 0)} for n in chain})
    for h in HEADS:
        pose = add_pose(pose, {h: {"brot": (0, 12 * fall, 0)}})
    for j in JAWS:
        pose = add_pose(pose, {j: {"brot": (14 * fall, 0, 0)}})
    return pose


# ---------------------------------------------------------------- building actions

def solve_clip(rig, name):
    """List of (frame, channels) for a clip; the clip's per-frame pose callbacks live here."""
    keys = []
    if name == "idle":
        n, step = 120, 5
        for f in range(0, n + 1, step):
            t = (f % n) / FPS
            rig.apply_pose(idle_pose(t), planted(rig))
            keys.append((f, rig.channels()))
    elif name == "walk":
        n, step = int(round(WALK_T * FPS)), 1
        WALK_REST_FOOT.update({s: tuple(rig.rest_foot[s]) for s in "LR"})
        for f in range(0, n + 1, step):
            t = (f % n) / FPS

            def legs(r, t=t):
                out = {}
                for s in "LR":
                    foot, toe = walk_foot(s, t)
                    out.update(r.leg_aims(s, foot, FWD, toe_deg=toe))
                return out
            rig.apply_pose(walk_body(t), legs)
            keys.append((f, rig.channels()))
    elif name == "turn_in_place":
        n = int(round(TURN_T * FPS))
        for f in range(0, n + 1):
            t = f / FPS

            def legs(r, t=t):
                out = {}
                for s in "LR":
                    foot, yaw, toe = turn_foot(r, s, t)
                    facing = Matrix.Rotation(math.radians(yaw), 3, "Z") @ FWD
                    out.update(r.leg_aims(s, foot, facing, toe_deg=toe))
                return out
            rig.apply_pose(turn_body(t), legs)
            keys.append((f, rig.channels()))
    elif name == "stagger":
        n = int(round(1.2 * FPS))
        for f in range(0, n + 1, 2):
            rig.apply_pose(stagger_pose(f / FPS), planted(rig))
            keys.append((f, rig.channels()))
    elif name == "death":
        n = int(round(DEATH_T * FPS))
        plant_t = None
        attach = {}
        for f in range(0, n + 1):
            t = f / FPS
            body = death_body(t, rig)
            if t <= T_ROLL:
                rig.apply_pose(body, planted(rig))
                if (f + 1) / FPS > T_ROLL and not attach:  # last planted frame: remember the feet relative to the body
                    mb = rig.body_matrix().inverted()
                    attach = {s: mb @ rig.rest_foot[s] for s in "LR"}
            else:
                # first apply the body, then put the feet where they sit in the body frame
                rig.apply_pose(body)
                mb = rig.body_matrix()
                targets = {s: mb @ attach[s] for s in "LR"}
                rig.apply_pose(body, planted(rig, FWD, targets))
            # floor fit: lift the root so nothing is below the floor, and let it fall into place
            z = rig.min_z()
            lift = -z + 0.004 if z < 0.004 else 0.0
            if lift:
                body = add_pose(body, {"root": {"t": (0, 0, lift)}})
                if t <= T_ROLL:
                    rig.apply_pose(body, planted(rig))
                else:
                    rig.apply_pose(body)
                    mb = rig.body_matrix()
                    rig.apply_pose(body, planted(rig, FWD, {s: mb @ attach[s] for s in "LR"}))
            keys.append((f, rig.channels()))
        keys[-1] = (n, keys[-1][1])
    else:
        die(f"unknown clip {name}")
    return keys


def write_action(rig, name, keys, loop):
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    rig.arm.animation_data_create()
    rig.arm.animation_data.action = act
    prev_q = {}
    rig.reset()
    touched = set(rig.names)  # every clip keys every bone, so no clip inherits another's leftover pose
    for f, ch in keys:
        for n in rig.names:
            if n not in touched:
                continue
            loc, q, sc = ch[n]
            if n in prev_q and sum(a * b for a, b in zip(q, prev_q[n])) < 0:
                q = tuple(-x for x in q)  # keep the quaternion on the near side so keys interpolate the short way
            prev_q[n] = q
            pb = rig.arm.pose.bones[n]
            pb.location, pb.rotation_quaternion, pb.scale = loc, q, sc
            pb.keyframe_insert("location", frame=f)
            pb.keyframe_insert("rotation_quaternion", frame=f)
            pb.keyframe_insert("scale", frame=f)
    act["loop"] = loop
    act.frame_start, act.frame_end = 0, keys[-1][0]
    act.use_frame_range = True
    rig.arm.animation_data.action = None
    return act


def foot_names():
    return [f"leg_toes.{s}" for s in "LR"]


def measure(rig, name, act, loop):
    rig.arm.animation_data.action = act
    rig.mod.show_viewport = True
    sc = bpy.context.scene
    f0, f1 = int(act.frame_start), int(act.frame_end)
    dg = None
    minz, minz_at = 1e9, None
    foot = {s: [] for s in "LR"}
    pose_first = pose_last = None
    t0 = time.time()
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        ev = rig.obj.evaluated_get(dg)
        m = ev.to_mesh()
        co = np.empty(len(m.vertices) * 3)
        m.vertices.foreach_get("co", co)
        ev.to_mesh_clear()
        z = float(co[2::3].min())
        if z < minz:
            minz, minz_at = z, f
            vi = int(np.argmin(co[2::3]))
            low_group = rig.obj.vertex_groups[max(rig.obj.data.vertices[vi].groups, key=lambda g: g.weight).group].name
        ev_arm = rig.arm.evaluated_get(dg)
        for s in "LR":
            foot[s].append(tuple(ev_arm.pose.bones[f"leg_toes.{s}"].head))
        snap = np.array([list(ev_arm.pose.bones[n].head) + list(ev_arm.pose.bones[n].tail) for n in rig.names])
        if f == f0:
            pose_first = snap
        pose_last = snap
    out = {"frames": f1 - f0, "seconds": (f1 - f0) / FPS, "loop": bool(loop), "min_z_m": round(minz, 4),
           "min_z_frame": minz_at, "min_z_vertex_bone": low_group, "min_z_ok": minz >= -FLOOR_TOL, "min_z_checked": "every frame, full mesh",
           "loop_pose_diff_m": round(float(np.abs(pose_first - pose_last).max()), 6) if loop else None,
           "measure_seconds": round(time.time() - t0, 1)}
    if name == "walk":
        dt = 1.0 / FPS
        rec = {}
        speeds_all = []
        for s in "LR":
            fp = np.array(foot[s])
            planted_f = fp[:, 2] < rig.rest_foot[s].z + 0.01
            sp = []
            for i in range(len(fp) - 1):
                if planted_f[i] and planted_f[i + 1]:
                    sp.append((fp[i + 1, 1] - fp[i, 1]) / dt)
            sp = np.array(sp)
            rec[s] = {"planted_frames": int(planted_f.sum()), "slide_speed_mean_mps": round(float(sp.mean()), 4),
                      "slide_speed_min_mps": round(float(sp.min()), 4), "slide_speed_max_mps": round(float(sp.max()), 4),
                      "max_abs_dev_from_ground_speed_mps": round(float(np.abs(sp - WALK_GROUND_SPEED).max()), 4),
                      "planted_lateral_drift_m": round(float(np.ptp(fp[planted_f, 0])), 4),
                      "planted_height_range_m": round(float(np.ptp(fp[planted_f, 2])), 4)}
            speeds_all += list(sp)
        out["implied_ground_speed_mps"] = round(WALK_GROUND_SPEED, 4)
        out["stride_m"], out["stance_fraction"], out["cycle_s"] = WALK_STRIDE, WALK_DUTY, WALK_T
        out["feet"] = rec
        out["root_displacement_m"] = 0.0
    rig.arm.animation_data.action = None
    rig.mod.show_viewport = False
    return out


def build():
    t0 = time.time()
    rig = Rig(os.path.join(HERE, "goose_rigged.blend"))
    bpy.context.scene.render.fps = FPS
    metrics = {}
    acts = {}
    for name, loop in (("idle", True), ("walk", True), ("turn_in_place", False), ("stagger", False), ("death", False)):
        t1 = time.time()
        rig.reach_err = 0.0
        keys = solve_clip(rig, name)
        acts[name] = write_action(rig, name, keys, loop)
        print(f"goose_clips: {name}: {len(keys)} keys, frames 0..{keys[-1][0]}, IK reach shortfall "
              f"{rig.reach_err:.3f} m, solved in {time.time() - t1:.1f} s")
        rig.reach_err = 0.0
    bpy.context.scene.frame_start, bpy.context.scene.frame_end = 0, 120
    for name, loop in (("idle", True), ("walk", True), ("turn_in_place", False), ("stagger", False), ("death", False)):
        metrics[name] = measure(rig, name, acts[name], loop)
        print(f"goose_clips: {name}: {json.dumps(metrics[name])}")
    rig.reset()
    rig.mod.show_viewport = True
    bpy.ops.object.mode_set(mode="OBJECT")
    os.makedirs(CLIPS_DIR, exist_ok=True)
    with open(os.path.join(CLIPS_DIR, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=1)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "goose_animated.blend"), compress=True)
    bad = [n for n, m in metrics.items() if not m["min_z_ok"]]
    print(f"goose_clips: wrote goose_animated.blend and clips/metrics.json in {time.time() - t0:.1f} s")
    if bad:
        die(f"clips go below the floor: {bad}")


# ---------------------------------------------------------------- review renders

BG = "#EDE6D6"


CAM_TARGET = {"death": (2.0, 0.3, 2.2)}  # the goose falls toward +X


def setup_scene(res, samples, target=(0, 0.3, 3.0)):
    from PIL import Image  # noqa: F401  (fail early if Pillow is missing)
    sc = bpy.context.scene
    for o in [o for o in bpy.data.objects if o.type in ("CAMERA", "LIGHT") or o.name.startswith("Ground")]:
        bpy.data.objects.remove(o)
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 3
    sc.cycles.use_light_tree = False
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.view_settings.view_transform = "AgX"
    sc.render.image_settings.file_format = "PNG"
    sc.render.film_transparent = True
    sc.render.image_settings.color_mode = "RGBA"
    w = bpy.data.worlds.new("W")
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.03, 0.022, 0.015, 1)
    d = 20.0
    centre = Vector((0, 0, 3.3))
    for name, pos, en, sz, col in (("Key", (0.75, -0.95, 0.85), 26, 0.6, (1.0, 0.86, 0.7)),
                                   ("Fill", (-1.1, -0.55, 0.25), 5, 1.0, (1.0, 0.78, 0.6)),
                                   ("Rim", (-0.3, 1.2, 1.0), 22, 0.6, (0.7, 0.76, 0.9))):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = en * d * d
        ld.size = d * sz
        ld.color = col
        lo = bpy.data.objects.new(name, ld)
        lo.location = centre + Vector(pos) * d
        lo.rotation_euler = (centre - lo.location).to_track_quat("-Z", "Y").to_euler()
        sc.collection.objects.link(lo)
    gm = bpy.data.meshes.new("Ground")
    g = 400
    gm.from_pydata([(-g, -g, 0), (g, -g, 0), (g, g, 0), (-g, g, 0)], [], [(0, 1, 2, 3)])
    ground = bpy.data.objects.new("Ground", gm)
    sc.collection.objects.link(ground)
    ground.is_shadow_catcher = True
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    cam.data.type = "ORTHO"
    cam.data.clip_start, cam.data.clip_end = 0.01, 400
    yaw, pitch = math.radians(-35), math.radians(16)
    toward = Vector((math.sin(yaw) * math.cos(pitch), -math.cos(yaw) * math.cos(pitch), math.sin(pitch)))
    target = Vector(target)
    cam.location = target + toward * 60
    cam.rotation_euler = (-toward).to_track_quat("-Z", "Y").to_euler()
    cam.data.ortho_scale = 11.0
    sc.collection.objects.link(cam)
    sc.camera = cam


def composite(path):
    from PIL import Image
    h = BG.lstrip("#")
    r = Image.open(path).convert("RGBA")
    flat = Image.new("RGBA", r.size, tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (255,))
    Image.alpha_composite(flat, r).convert("RGB").save(path)


def render_clip(rig, name, tmp):
    from PIL import Image, ImageDraw, ImageFont
    act = bpy.data.actions[name]
    sc = bpy.context.scene
    rig.arm.animation_data_create()
    rig.arm.animation_data.action = act
    rig.mod.show_viewport = True
    n = int(act.frame_end)
    loop = bool(act.get("loop"))
    frames = [int(round(x)) for x in np.linspace(0, n, 8, endpoint=not loop)]
    times = {}
    # --- stills
    setup_scene(600, 16, CAM_TARGET.get(name, (0, 0.3, 3.0)))
    t0 = time.time()
    tiles = []
    for f in frames:
        sc.frame_set(f)
        p = os.path.join(tmp, f"{name}_still_{f:03d}.png")
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        composite(p)
        tiles.append((f, Image.open(p).convert("RGB")))
    times["stills_s"] = round(time.time() - t0, 1)
    tw = tiles[0][1].width
    sheet = Image.new("RGB", (tw * 4, tw * 2 + 0), BG)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
    except OSError:
        font = ImageFont.load_default()
    for i, (f, im) in enumerate(tiles):
        x, y = (i % 4) * tw, (i // 4) * tw
        sheet.paste(im, (x, y))
        d = ImageDraw.Draw(sheet)
        d.text((x + 12, y + 10), f"{name}  frame {f}  ({f / FPS:.2f} s)", fill="#14120E", font=font)
    sheet_path = os.path.join(CLIPS_DIR, f"{name}_sheet.png")
    sheet.save(sheet_path)
    if os.environ.get('GOOSE_STILLS_ONLY'):
        rig.arm.animation_data.action = None
        return times
    # --- mp4: every second frame at 15 fps, 480 px, 8 samples
    setup_scene(480, 8, CAM_TARGET.get(name, (0, 0.3, 3.0)))
    t0 = time.time()
    seq = os.path.join(tmp, f"{name}_seq")
    os.makedirs(seq, exist_ok=True)
    for i, f in enumerate(range(0, n + (0 if loop else 1), 2)):
        sc.frame_set(f)
        p = os.path.join(seq, f"{i:04d}.png")
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        composite(p)
    mp4 = os.path.join(CLIPS_DIR, f"{name}.mp4")
    rc = os.system(f'ffmpeg -y -loglevel error -framerate 15 -i "{seq}/%04d.png" -c:v libx264 -pix_fmt yuv420p "{mp4}"')
    if rc != 0:
        die(f"ffmpeg failed for {name}")
    times["mp4_s"] = round(time.time() - t0, 1)
    rig.arm.animation_data.action = None
    return times


def render(names):
    tmp = os.environ.get("GOOSE_CLIPS_TMP")
    if not tmp:
        die("set GOOSE_CLIPS_TMP to a scratch directory for the intermediate frames")
    os.makedirs(tmp, exist_ok=True)
    os.makedirs(CLIPS_DIR, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, "goose_animated.blend"))
    arm = bpy.data.objects["goose_rig"]
    bpy.context.view_layer.objects.active = arm

    class R:  # the bits of Rig that render needs
        pass
    rig = R()
    rig.arm, rig.obj = arm, bpy.data.objects[SLUG]
    rig.mod = [m for m in rig.obj.modifiers if m.type == "ARMATURE"][0]
    names = names or ["idle", "walk", "turn_in_place", "stagger", "death"]
    for name in names:
        t0 = time.time()
        times = render_clip(rig, name, tmp)
        print(f"goose_clips: rendered {name}: {json.dumps(times)} total {time.time() - t0:.1f} s")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("build", "render"):
        die("usage: goose_clips.py build | render [clip ...]")
    if sys.argv[1] == "build":
        build()
    else:
        render(sys.argv[2:])


main()
