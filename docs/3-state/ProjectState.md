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

## The one thing that is not what it looks like

Every clip passed its floor and loop checks and was looked at as 8 stills, but no person has watched
the MP4s yet, and nothing checks a neck or wing passing through the body.

## Cross-cutting issues

- The model READMEs' rebuild commands point at the art-pipeline scripts' old location in
  AjsClaudeCodeTools.
- Blender-as-a-module (`bpy` 5.0.1) runs under `python3.11` in the sandbox; Pillow had to be
  reinstalled for it with `pip install --user --ignore-installed pillow` before renders worked.
