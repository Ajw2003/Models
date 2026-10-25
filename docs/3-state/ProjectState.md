# Project state

**Headline: 90%.** Version 1 (13 clips) is built and waits on aj's check; aj asked for version 2, which is under way: its 68-bone rig with tongue bones is built (#9), its 20 clips are not.

| Milestone | Status |
|---|---|
| 1. Models moved in | Done: files compared byte for byte with `cd0cef5`; `main` at `7ac237e` |
| 2. Goose boss rig | Built and looked at (#2): 59 bones, `docs/art/reviews/goose-rig-review.png`; waits on aj's check in the pull request |
| 3. Goose boss clips | All 13 built and looked at (#3 to #6); `art/goose/goose_anims.fbx` re-imports with 13 takes and 59 bones; events live in `art/goose/clips/manifest.json` because FBX drops the markers; waits on aj's check in the pull request |
| 4. Scythe finished | Unknown: no acceptance yet |

## Version 2 (#8)

- #9 rig with tongue bones: built and looked at, `docs/art/reviews/goose-rig-v2-review.png`. With the jaw wide open, the flat end of the original mouth tube shows; the mesh is unchanged, so it is left as built.
- #10 to #13: not started.

## Goose model version 2 (#17)

- #18 one fused skin and a forking neck root: built, waits on aj's review. `python3.11
  art/goose/build_goose.py --v2` gives 1,072 parts, 294,828 triangles (5,172 under the 300,000
  budget), height 6.750 m, and a skin of 1 piece; the whole model is 1,064 closed pieces against
  version 1's 1,071. Review sheet: `docs/art/reviews/goose-v2-review.png`. The join close-ups show
  no seam lines; the colour still changes in a hard, ragged black-to-pale line across the breast,
  which #20 replaces. Version 1's files are unchanged (`git status`).
- #25 necks (after aj's QA check failed #18 for rigid, smooth necks): built, waits on aj's review.
  The necks rest in an S-curve with 15 and 12 vertebra ridges and a bone spike per vertebra.
  `build_goose.py --v2` now gives 1,094 parts, 297,820 triangles (2,180 under budget), 6.750 m,
  skin 1 piece. Under the dark neck colour the ridges read faintly; the spikes carry the
  segmentation from behind (`docs/art/reviews/goose-v2-necks/`).
  aj liked the necks; on 2026-10-25 the maple leaf brand was removed from version 2 (1,093 parts,
  still 297,820 triangles; version 1 keeps its brand and rebuilds at 272,380).
- #19, #20 and #21: not started; #19 has 2,180 triangles of headroom, so it has to trim elsewhere.
  #21 now asks for one bone per vertebra (15 and 12).

## The one thing that is not what it looks like

Every clip passed its floor and loop checks and was looked at as 8 stills, but no person has watched
the MP4s yet, and nothing checks a neck or wing passing through the body.

## Cross-cutting issues

- The model READMEs' rebuild commands point at the art-pipeline scripts' old location in
  AjsClaudeCodeTools.
- Blender-as-a-module (`bpy` 5.0.1) runs under `python3.11` in the sandbox; Pillow had to be
  reinstalled for it with `pip install --user --ignore-installed pillow` before renders worked.
