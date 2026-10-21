# Decisions

The running log of what was decided in this repo, when and why. Newest entry at the top. Entries
are never rewritten; a later decision flips an old entry's Status to Superseded with a pointer.

## 2026-10-21 — Goose boss animation: seven attacks, The Crown Wakes, the playable set, this repo only

**Context.** aj asked for the goose boss (`art/goose`, The Honking Deep) to be animated as a
Soulslike boss with five attacks and a phase transition. The goose had no rig and no clips
(`art/goose/views/stats.json` records 0 bones). The proposal page
`docs/plans/2026-10-21-goose-boss-animation.html` put four choices to aj.

**Decision.** aj approved the design with "Design approved: goose boss animation 1* 2A 3A 4A":

- Attacks (question 1, their own answer): all five from option B ("The bird that hunts":
  Hesitation Peck, Flapping Charge, Leap and Dive, Wing Gust, Turning Tail Sweep) plus attacks 4
  and 5 from option A (Neck Lunge Grab, Death Honk), seven attacks in total.
- Phase transition (question 2): option A, The Crown Wakes, animation only, so the pass 19 mesh
  stays unchanged.
- Extra clips (question 3): option A, the playable set: idle, walk, turn on the spot, stagger and
  death.
- Target (question 4): option A, this repo only; no engine import.

That is 13 clips: 7 attacks, 1 phase transition and 5 supporting clips, on a 59-bone generic rig.

**Why.** aj chose the goose-movement attacks and kept the two that use the three heads. The
animation-only transition keeps the approved model; the supporting clips make the boss droppable
into a fight; no game was named as the goose's home, so nothing goes into an engine yet. Rejected:
option A's Triple Peck, Wing Rake and Rearing Stomp; the new-geometry Brand Tears Open transition;
attacks and transition only; a Unity import.

**Status.** Standing.

## 2026-10-21 — The models move out of AjsClaudeCodeTools

**Context.** The goose and scythe were made on the `claude/art-pipeline` branch of
`Ajw2003/AjsClaudeCodeTools`, a plugin repo and not the right home for game assets.

**Decision.** They moved here with their commit history filtered down to the model files
(byte-for-byte identical to that branch's commit `cd0cef5`). The old branch stays untouched. New
work goes on `AjsAgent/import-models` and reaches `main` only by pull request.

**Why.** aj asked for a separate models repo and chose to keep the history and leave the old
branch alone.

**Status.** Standing.
