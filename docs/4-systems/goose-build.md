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
