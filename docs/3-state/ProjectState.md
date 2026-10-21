# Project state

**Headline: 70%.** The goose is rigged and 9 of its 13 clips are built; group two of the attacks and the phase transition are not.

| Milestone | Status |
|---|---|
| 1. Models moved in | Done: files compared byte for byte with `cd0cef5`; `main` at `7ac237e` |
| 2. Goose boss rig | Built, pose-tested and looked at (#2): 59 bones, `docs/art/reviews/goose-rig-review.png`; waits on aj's check in the pull request |
| 3. Goose boss clips | 9 of 13 built (#3, #4): the five supporting clips plus Hesitation Peck, Flapping Charge, Leap and Dive, Wing Gust; known defect: Flapping Charge's planted feet slide 14 to 16% faster than its implied 3.889 m/s ground speed (`art/goose/clips/metrics.json`); group two and The Crown Wakes (#5) next |
| 4. Scythe finished | Unknown: no acceptance yet |

## The one thing that is not what it looks like

The goose is rigged (`art/goose/goose_rigged.blend`, 59 bones), but only one test pose has been
checked; tail, jaws, finger bones and full wing folds have not been posed yet.

## Cross-cutting issues

- The model READMEs' rebuild commands point at the art-pipeline scripts' old location in
  AjsClaudeCodeTools.
- Blender-as-a-module (`bpy` 5.0.1) runs under `python3.11` in the sandbox; Pillow had to be
  reinstalled for it with `pip install --user --ignore-installed pillow` before renders worked.
