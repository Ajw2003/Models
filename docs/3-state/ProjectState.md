# Project state

**Headline: 20%.** The models are in; the goose animation is designed and approved, not built.

| Milestone | Status |
|---|---|
| 1. Models moved in | Done: files compared byte for byte with `cd0cef5`; `main` at `7ac237e` |
| 2. Goose boss rig | Not started; design approved 2026-10-21 |
| 3. Goose boss clips | Not started; design approved 2026-10-21 |
| 4. Scythe finished | Unknown: no acceptance yet |

## The one thing that is not what it looks like

The goose looks finished in its review sheet, but it has 0 bones (`art/goose/views/stats.json`),
so nothing can move yet.

## Cross-cutting issues

- The model READMEs' rebuild commands point at the art-pipeline scripts' old location in
  AjsClaudeCodeTools.
- Blender-as-a-module (`bpy`) is not installed in this session's sandbox yet.
