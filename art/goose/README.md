# The Honking Deep (eldritch goose boss)

A hero-tier boss built by the `art-pipeline` skill from a one-line prompt: a Canada goose gone feral
in a dead maple wood, styled toward Bloodborne, standing proud like a real goose (body traced off a
photo, necks upright, heads high). Three heads, each a gore-caked mask: wrinkled hide, bony brows in
a scowl over one sunken eye, cheeks split back from the beak and lined with teeth, a beak crowded
with broken, blood-rooted teeth, and dead bare maple branches torn out through the skull. Ragged
hackles down every neck, blood run down from the jaws; bare finger bones breaking out of the wings
and bare ribs through the flanks; a maple leaf branded into the breast above a matted bib of
blood-soaked feathers; mud up the legs. Soot, ash, grimy bone and dried blood, nothing glowing.
6.75 m to the crown's twig tips, 272,380 triangles against a 300,000 budget; one mesh, one
material reading three baked 4096 px textures (colour with ambient occlusion folded in, normal,
roughness); faces -Y, origin on the ground between the feet.

| File | What it is |
|---|---|
| `spec.json` | size, budget, materials (hex), build notes, and the design numbers everything is built from |
| `goose_design.py` | the design as pure Python: spec in, parts and mesh faces out (no Blender needed) |
| `draw_concept.py` | draws `concept.png`, front and side views with the reference human and palette, from those parts |
| `build_goose.py` | turns the parts into one Blender mesh, validates it, has `goose_texture.py` bake it, exports the model files |
| `goose_texture.py` | procedural surfaces per material (feather barbs and shafts, scalloped plumage, hide, bark, bone, scutes, blood, mud, grit, the brand decal) baked into one texture set |
| `textures/` | the baked colour, normal and roughness images (4096 px JPEG) the model reads |
| `goose.glb` / `goose.fbx` / `goose.blend` | the model |
| `views/` | the four review renders and `stats.json` |
| `build_rig.py` | adds the 59-bone armature to `goose.blend`, skins it (weights computed per part, not bone-heat), runs the pose test; writes `goose_rigged.blend` |
| `goose_skin.py` | version 2: melts the soft parts into one closed skin and carries version 1's colour over to it (#18) |
| `goose_v2.glb` / `goose_v2.fbx` / `goose_v2.blend` | version 2 model from `build_goose.py --v2`, textures in `textures_v2/`; review sheet `docs/art/reviews/goose-v2-review.png` |
| `goose_rigged.blend` | the model with the rig bound; `rig_views/` holds its pose-test renders (rest three-quarter, posed three-quarter, front, side) |
| `goose_clips.py` | the pose library and the 13 clips as Blender Actions at 30 fps, their metrics, per-clip review renders, and the FBX / manifest export |
| `goose_animated.blend` | `goose_rigged.blend` plus the 13 actions (fake user), with "hit" / "release" / "roar" pose markers |
| `goose_anims.fbx` | the armature and the 13 actions as takes, animation only (no mesh), 59 deform bones |
| `clips/` | `manifest.json` (what an engine reads), `metrics.json` (measurements), and per clip `<clip>_sheet.png` (8 stills) and `<clip>.mp4` |

Review sheets: `docs/art/reviews/goose-review.png` (the model), `goose-rig-review.png` (the rig pose test) and
`goose-clips-review.png` (all 13 clip sheets stacked); recorded verdicts beside them.

Rebuild and re-review, from the repo root (needs `python3.11` with `bpy`, from
`claude-art-pipeline/plugins/art-pipeline/skills/art-pipeline/scripts/setup_bpy.sh`):

```bash
python3 art/goose/draw_concept.py
python3.11 art/goose/build_goose.py
python3.11 claude-art-pipeline/plugins/art-pipeline/skills/art-pipeline/scripts/render_views.py art/goose/goose.glb --out art/goose/views --res 900 --background "#EDE6D6"
python3 claude-art-pipeline/plugins/art-pipeline/skills/art-pipeline/scripts/review_sheet.py --concept art/goose/concept.png --views art/goose/views --title "The Honking Deep (eldritch goose boss)" --out docs/art/reviews/goose-review.png
```

The full build takes about 10 minutes on this cloud sandbox's 4 CPU cores (Cycles on CPU);
`GOOSE_TEXTURE_PX=1024` before the build command bakes small for a quick look in under a minute.

`build_goose.py` refuses to export if the model is over budget, more than 0.15 m off the spec
height, below the ground, has a part that is not a closed shell, or loses a material.

Rig, clips and export, from the repo root (same `python3.11` with `bpy`, plus `ffmpeg` and Pillow for the
review renders). Measured on this cloud sandbox's 4 CPU cores:

```bash
python3.11 art/goose/build_rig.py                      # goose.blend -> goose_rigged.blend, about 5 s
python3.11 art/goose/build_rig.py --pose-test POSED.blend   # pose test, about 1 s (then render it with render_views.py)
python3.11 art/goose/goose_clips.py build              # 13 actions -> goose_animated.blend, clips/metrics.json, manifest.json, about 140 s
GOOSE_CLIPS_TMP=/path/to/scratch python3.11 art/goose/goose_clips.py render [clip ...]   # sheets and MP4s
python3.11 art/goose/goose_clips.py export             # goose_anims.fbx, manifest.json, re-import check, about 9 s
```

`render` takes about 60 s for a clip's 8 stills (600 px, 16 samples) and 70 to 340 s for its MP4 (480 px, 8
samples, 15 fps; longest is crown_wakes at 343 s), so all 13 clips take roughly 48 minutes. `export` fails unless
exactly 13 takes come back from a re-import with lengths within a frame of `metrics.json` and 59 bones. FBX does
not carry pose markers (the re-import shows 0 of 9), so `clips/manifest.json` is the source of truth for events.

What the review passes changed: pass 1 had barcode-like flank bars, washed-out and over-crowded
eyes, tentacles standing straight like extra legs, a needle of a tail and square feather tips;
pass 2 and 3 fixed those, and the validator caught a tentacle dipping 3 cm below the floor.
Passes 4-6 (the Bloodborne restyle) removed the 64 glowing eyes and the six tentacles, darkened the
palette, added ribs and rattier feathers, and turned blood stripes that read as tribal paint
(pass 5) into a ragged stain round the maw.
Passes 7-11 (dead maple) replaced the quill crests with dead maple crowns (enlarged after pass 7
read as spindly), scattered rotting leaves (made fewer and larger after pass 7's read as red
flecks), removed the breast maw and the blood stain, and put a maple-leaf brand bent to the breast
in their place, with blood-soaked breast feathers below it.
Passes 12-19 moved the surface detail into baked textures (the brand, feather barbs, hide, bark,
blood, grime), cut the last maple leaves (they looked alive), re-traced the body off a photo of a
standing goose (pass 13: the body tilts down to the tail, the chest no longer bulges), blended the
main neck into the chest and stood the goose up proud, made the breast bib hang like matted
feathers rather than a row of teeth (pass 15), gave the heads hide, brows, split cheeks, crowded
bloody teeth and torn skin round the crown roots, lumped every tube so nothing reads as machined,
added hackles, mud and occlusion, and set per-colour render gains so the lit render reaches the
concept sheet's tones (measured breast 82 vs the concept's 102, up from 64).

Known gaps: the lit render is still a little lighter on the black necks (31 vs 18) and darker on the
breast (82 vs 102) than the concept's flat colours; the brand and blood are baked at 4096 px over the
whole model, so they soften up close; it is not yet imported into an engine.

What now exists: the 59-bone rig, 13 clips (idle, walk, turn_in_place, stagger, death, hesitation_peck,
flapping_charge, leap_and_dive, wing_gust, turning_tail_sweep, neck_lunge_grab, death_honk, crown_wakes),
`goose_anims.fbx` and `clips/manifest.json`. Honest flaws in the clips and rig:

- There is no body-collision check: necks, wings and legs can pass through the body, and I only looked at the
  stills. Only the floor is checked (every frame, full mesh, lowest vertex at or above -0.01 m).
- The tail sweep in `turning_tail_sweep` looks modest in the stills.
- The walk's body roll is small, so the waddle is subtle.
- In `death`, the crowns prop the heads a little off the floor.
- The review stills are low-sample (16 samples, 600 px) and the MP4s are 480 px at 8 samples; no person has watched
  the MP4s yet.
- Planted feet slide at the implied ground speed (the root never moves), which `metrics.json` measures; it is
  not a slide-free foot lock. The walk has one edge frame about 0.13 m/s off that speed.
- `crown_wakes` and `death` end in different poses from idle by design; there is no phase-two idle.
