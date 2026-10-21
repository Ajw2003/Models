# Project state

**Headline: 55%.** The goose is rigged and 5 of its 13 clips are built; the 8 attack and transition clips are not.

| Milestone | Status |
|---|---|
| 1. Models moved in | Done: files compared byte for byte with `cd0cef5`; `main` at `7ac237e` |
| 2. Goose boss rig | Built, pose-tested and looked at (#2): 59 bones, `docs/art/reviews/goose-rig-review.png`; waits on aj's check in the pull request |
| 3. Goose boss clips | 5 of 13 built (#3): idle, walk, turn_in_place, stagger, death, with `art/goose/clips/metrics.json` and contact sheets; attack group one (#4) next |
| 4. Scythe finished | Unknown: no acceptance yet |

## The one thing that is not what it looks like

The goose is rigged (`art/goose/goose_rigged.blend`, 59 bones), but only one test pose has been
checked; tail, jaws, finger bones and full wing folds have not been posed yet.

## Cross-cutting issues

- The model READMEs' rebuild commands point at the art-pipeline scripts' old location in
  AjsClaudeCodeTools.
- Blender-as-a-module (`bpy` 5.0.1) runs under `python3.11` in the sandbox; Pillow had to be
  reinstalled for it with `pip install --user --ignore-installed pillow` before renders worked.
