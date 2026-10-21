# models

Game models built with the [art-pipeline](https://github.com/Ajw2003/claude-art-pipeline) plugin.

| Folder | Model |
|---|---|
| `art/goose/` | The Honking Deep, a three-headed eldritch goose boss (pass 19) |
| `art/scythe/` | A reaper scythe built from a reference image |
| `docs/art/reviews/` | Review sheets and recorded verdicts for both models |

Each model folder has its own README with what the files are and how to rebuild it.

## Where this came from

These models were first made on the `claude/art-pipeline` branch of `Ajw2003/AjsClaudeCodeTools`,
which is a Claude Code plugin repo and not the right home for game assets. They were moved here on
2026-10-21 with their commit history kept: every commit in this repo before this README is one of
the original commits, filtered down to just the model files. The files are byte-for-byte the same as
on that branch's last commit (`cd0cef5`).

The rebuild commands in each model's README name scripts under `claude-art-pipeline/plugins/...`.
That path now lives in the `Ajw2003/claude-art-pipeline` repo, so run them from a checkout of that
repo with this one alongside it.
