# Scythe build

## What it owns

The scythe model files `art/scythe/scythe.glb`, `scythe.fbx` and `scythe.blend`, rebuilt from
`art/scythe/spec.json`.

## How it works

`build_scythe.py` traces the blade outline from the reference image in pixels and converts it to
metres (`build_scythe.py:42`), extrudes it (`build_scythe.py:72`), builds the twisted shaft and the
skull (`build_scythe.py:103`, `build_scythe.py:147`) and exports.

## Invariants

- One mesh, 5 materials, 1.80 m tall, faces -Y (`art/scythe/README.md`).

## Traps

None recorded yet.
