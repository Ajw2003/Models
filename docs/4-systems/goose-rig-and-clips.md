# Goose rig and clips

Status: designed and approved on 2026-10-21 (`docs/6-decisions/Decisions.md`), not built yet.
Line citations are added as the code lands.

## What it owns

The goose boss's skeleton, its skin binding to the pass 19 mesh, the 13 animation clips, the
animation-only FBX that carries them, and the clip manifest an engine importer reads.

## How it works

- `art/goose/build_rig.py` opens the built `goose.blend`, places a 59-bone generic (non-humanoid)
  skeleton from the design numbers in `spec.json` and `goose_design.py`, binds it with automatic
  weights, then applies rules that keep rigid parts (teeth, ribs, finger bones, crown branches)
  on one bone each. It writes `goose_rigged.blend` and posed review renders.
- Bones: root, pelvis, spine 1-3, tail 1-2; main neck 1-7, head, jaw; each side neck 1-6, head,
  jaw; one crown bone per head; each wing shoulder, upper arm, forearm, hand, finger 1-4; each leg
  thigh, shin, tarsus, toes. 59 in total.
- `art/goose/goose_clips.py` holds named poses (bone rotations, plus crown scale for the phase
  transition) and one function per clip that keys those poses with easing, anticipation and
  overshoot. Clips stay in place: the game moves the body. Hit events are written at set
  normalised times.
- Clips (13): idle, walk, turn on the spot, stagger, death; Hesitation Peck, Flapping Charge, Leap
  and Dive, Wing Gust, Turning Tail Sweep, Neck Lunge Grab, Death Honk; The Crown Wakes.
- Output: `goose_anims.fbx` (animation only), `clips/manifest.json` (length, loop flag, events per
  clip), and per clip 8 stills on the real model plus an MP4 under `art/goose/clips/`.

## Invariants

- The pass 19 mesh is not changed; the rig binds to it as built.
- Planted feet do not slide (under 1 cm) and nothing goes below the floor in any frame.
- Every one-shot clip ends in the pose the next state expects: attacks return to the idle pose,
  death ends lying still, The Crown Wakes ends in the phase-two stance with crowns at 1.5 times
  their size.

## Traps

- Cycles on CPU only in the cloud sandbox; EEVEE and Workbench abort without a GPU.
- The mesh is 272,380 triangles, so automatic weighting and every render are slow; quick-look
  renders use a low sample count.
