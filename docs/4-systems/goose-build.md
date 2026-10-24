# Goose build

## What it owns

Every goose model file: `art/goose/goose.glb`, `goose.fbx`, `goose.blend` and the baked textures in
`art/goose/textures/`, all rebuilt from `art/goose/spec.json`.

## How it works

`goose_design.py` is pure Python: it reads the spec (`goose_design.py:28`) and turns the design
numbers into parts and mesh faces, using lofts, tubes and feathers (`goose_design.py:151`,
`goose_design.py:166`, `goose_design.py:245`). `draw_concept.py` draws the concept sheet from the
same parts. `build_goose.py` runs inside Blender-as-a-module, makes one mesh
(`build_goose.py:52`), validates it (`build_goose.py:82`), has `goose_texture.py` bake the surfaces,
and exports (`build_goose.py:122`).

## Invariants

- The build refuses to export a model over `triangle_budget` (`build_goose.py:86`), more than
  0.15 m off `height_m` (`build_goose.py:26`, `build_goose.py:90`), or using materials the spec
  does not list (`build_goose.py:57`).
- A fix goes into `spec.json` or `goose_design.py`, never into the exported files.
- Faces -Y, +Z up, origin on the ground between the feet (`spec.json`, `scale_note`).

## Traps

- The full bake takes about 10 minutes on a 4-core cloud sandbox, measured in an earlier session
  (`art/goose/README.md`); `GOOSE_TEXTURE_PX=1024` is the quick-look setting.
- The README's rebuild commands name the art-pipeline scripts by their old path in
  AjsClaudeCodeTools; they now live in `Ajw2003/claude-art-pipeline`.

## Version 2 model (approved 2026-10-24, being built under #18)

`goose_design.py` gains a version 2 mode and `build_goose.py` writes `goose_v2.blend`, `.glb` and
`.fbx` with textures in `art/goose/textures_v2/`; version 1's files and `art/goose/textures/` are not
rebuilt. The soft parts (body, a single neck root that forks into the three necks, wing arms,
thighs, tail) are merged into one closed skin with smoothed joins; hard parts (teeth, ribs, claws,
crowns, feathers, scutes) stay separate shells. The body gains muscle, sag, skin folds and ribs
under torn skin; feathers hang over every join. Two texture sets: the body, and the heads with the
upper necks at higher detail. The triangle budget stays 300,000.

Trap: `build_rig.py` assigns weights by named design part (`g.mesh_parts`). A merged skin is no
longer split that way, so the version 2 rig carries weights over from the current rig by nearest
surface instead.

How the skin is fused (#18, plan `docs/plans/2026-10-24-goose-v2-skin.html`, approved 1A 2A 3A):
`spec.json` holds a `v2` block that `goose_design.build_parts(version=2)` merges over the design
numbers: one neck root from the chest whose top, at about 3.05 m, is where the two side necks start;
the heads keep version 1's positions. `goose_skin.py` (bpy) meshes the soft parts listed in
`v2.skin.parts`, melts them with a voxel remesh (`voxel_m`), relaxes only vertices within
`join_width_m` of a second soft part so each crease fills into a curve, and decimates to
`triangle_cap`. Each new face then copies the material, pattern and texture coordinates of the
nearest unfused face, mapping all its corners through that one face so a face across a part's
wrap-around seam does not smear; this stand-in colour is replaced when #20 re-bakes. `build_goose.py
--v2` adds the hard parts unchanged and refuses to export unless the skin is one piece.
