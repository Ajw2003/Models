# Goose rig and clips

Status: built (2026-10-21). Designed and approved the same day (`docs/6-decisions/Decisions.md`).

## What it owns

The goose boss's skeleton, its skin binding to the pass 19 mesh, the 13 animation clips, the
animation-only FBX that carries them, and the clip manifest an engine importer reads.

## How it works

- `art/goose/build_rig.py` opens the built `goose.blend`, places a 59-bone generic (non-humanoid)
  skeleton from the design numbers in `spec.json` and `goose_design.py` (`build_skeleton`,
  `art/goose/build_rig.py:164`), then binds it with weights computed per part by name, not Blender's
  bone-heat (`classify`, `art/goose/build_rig.py:237`; `compute_weights`, `art/goose/build_rig.py:312`),
  which keeps rigid parts (teeth, ribs, finger bones, crown branches) on one bone each. It writes
  `goose_rigged.blend` (`build`, `art/goose/build_rig.py:411`) and posed review renders (`pose_test`,
  `art/goose/build_rig.py:462`). Bones are named from the goose's own point of view: `.L` is +X
  (`BONE_SIDE`, `art/goose/build_rig.py:51`).
- Bones: root, pelvis, spine 1-3, tail 1-2; main neck 1-7, head, jaw; each side neck 1-6, head,
  jaw; one crown bone per head; each wing shoulder, upper arm, forearm, hand, finger 1-4; each leg
  thigh, shin, tarsus, toes. 59 in total (`BONE_COUNT`, `art/goose/build_rig.py:47`).
- `art/goose/goose_clips.py` holds named poses (bone rotations, plus crown scale for the phase
  transition: `RECOIL`, `idle_pose` at `art/goose/goose_clips.py:284`) and one pose function per clip that is
  converted to bone channels and keyed every frame (Bezier, auto-clamped handles) with easing, anticipation
  and overshoot built into the curves (`solve_clip` at `:453`, `solve_attack` at `:923`, `write_action` at
  `:965`). Legs are solved by a two-bone IK onto foot targets (`Rig.leg_aims`, `:203`). Clips stay in place
  (the root only turns or rises where the clip says so): the game moves the body. Hit, release and roar events
  are timeline markers on the actions (`attack_markers`) and are recorded in `manifest.json`.
- Clips (13): idle, walk, turn on the spot, stagger, death; Hesitation Peck, Flapping Charge, Leap
  and Dive, Wing Gust, Turning Tail Sweep, Neck Lunge Grab, Death Honk; The Crown Wakes.
- Output: `goose_anims.fbx` (animation only, 13 takes, no mesh; `export_fbx`, `art/goose/goose_clips.py:1343`),
  `clips/manifest.json` (length, loop flag, events, end pose, root motion per clip; `write_manifest`, `:1310`),
  `clips/metrics.json` (`measure`, `:1023`), and per clip 8 stills on the real model plus an MP4 under
  `art/goose/clips/` (`render_clip`, `:1214`). FBX does not carry pose markers, so the manifest is the source of
  truth for events; the export re-imports the file and fails unless it finds 13 takes of the right lengths.

## Invariants

- The pass 19 mesh is not changed; the rig binds to it as built.
- Planted feet slide only at the clip's implied ground speed (walk 0.625 m/s (measured mean 0.6205, one edge frame 0.13 m/s off), flapping_charge 3.889 m/s (measured exactly); the root never moves), and nothing goes below the floor in any frame (`metrics.json`,
  `min_z_m`, every frame of the full mesh).
- Every one-shot clip ends in the pose the next state expects: attacks return to the idle pose,
  death ends lying still, The Crown Wakes ends in the phase-two stance with crowns at 1.5 times
  their size.

## Traps

- Cycles on CPU only in the cloud sandbox; EEVEE and Workbench abort without a GPU.
- The mesh is 272,380 triangles, so automatic weighting and every render are slow; quick-look
  renders use a low sample count.

## Version 2 (approved 2026-10-21, not built yet)

Version 2 is built beside version 1 by the same scripts with a version switch; version 1's files are
never rebuilt. `build_rig.py` writes `goose_rigged_v2.blend` with 68 bones (59 plus `tongue_<head>_1..3`
for the main, left and right heads). `goose_clips.py` applies a global tempo of 1.4 and an effort layer
(deeper anticipation, strain shudder at strikes, heaving recovery) and writes `goose_animated_v2.blend`,
`goose_anims_v2.fbx` and `art/goose/clips_v2/` (sheets, MP4s, metrics, manifest, and a
`<clip>_compare.mp4` with version 1 left and version 2 right for each shared clip).

Version 2 clips (20): idle, walk, turn_in_place; hesitation_peck, flapping_charge, leap_and_dive,
wing_gust, turning_tail_sweep, neck_lunge_grab, death_honk; death (falls forward, necks flat, jaws
slack, tongues out); crown_wakes (12 s); stun_fall, stun_loop (loops), stun_get_up; hit_front,
hit_left, hit_right, hit_heavy, hit_back (turns round to face the attacker, angrier).

### Design review changes (approved 2026-10-24)

- Tempo is split per phase of each attack: wind-up 1.6, strike 1.0 to 1.1, recovery 1.4 times
  version 1. The strike shudder is one heavy shake, not a 5-per-second tremor.
- Attacks gain goose tells: head-pumping before hesitation_peck and neck_lunge_grab, a low-neck hiss
  with wings half-open before flapping_charge, the wing's wrist leading wing_gust. The main head
  leads every big attack; the side heads follow up.
- crown_wakes has no shudder bursts: stillness, the main neck rising bone by bone from the base,
  side heads first, crowns growing over 1 to 1.5 s per stage with one crack, one long roar.
- hit_front, hit_left, hit_right, hit_heavy and hit_back key only neck, head, jaw, tongue and wing
  bones (the legs, pelvis and root are untouched), so the game plays them on top of any clip.
- stun_fall ends, and stun_loop holds, with the main head on the ground in front of the chest.
