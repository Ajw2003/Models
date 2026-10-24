# Decisions

The running log of what was decided in this repo, when and why. Newest entry at the top. Entries
are never rewritten; a later decision flips an old entry's Status to Superseded with a pointer.

## 2026-10-24 — Goose v2 skin (#18): melt and smooth, fork at 3.05 m, colours carried over

**Context.** #18 (one fused skin and a forking neck root) is the first step of the version 2 goose
(#17). A throwaway test (`docs/art/reviews/goose-v2-prototype/prototype_fuse.py`) fused the soft
parts into one closed skin. The plan page is `docs/plans/2026-10-24-goose-v2-skin.html`.

**Decision.** aj approved "Design approved: goose v2 skin. Build plan approved: goose v2 skin 1A 2A 3A":

- Method (question 1): option A, a voxel remesh of the soft parts, smoothing only near the joins,
  then a decimate to a 75,000 triangle skin.
- Fork (question 2): option A, the root splits just above the breast, at about 3.05 m.
- Texture until #20 (question 3): option A, each skin face copies the nearest version 1 surface's
  colour and pattern, baked into `art/goose/textures_v2/`.

The steps are #22 (design numbers), #23 (fuse and one-shell check) and #24 (build and review).

**Why.** The test came out closed in both runs and the join width is one number; cutting and
stitching eight tubes is fragile. The side heads sit at 4.05 m, so a higher fork leaves stubby side
necks. A review sheet beside the concept needs colour to be judged.

**Status.** Standing.

## 2026-10-24 — Goose model version 2: one living beast

**Context.** aj asked for a senior game designer's critique of the goose model, textures and
blending, noting that the parts read as separate models. Close-ups
(`docs/art/reviews/goose-joins/`) and a mesh count showed 1,071 separate closed pieces: each neck,
wing and leg is a tube pushed into an egg-shaped body, with hard colour lines at every join. The
proposal is `docs/plans/2026-10-24-goose-model-review.html`.

**Decision.** aj approved "Design approved: goose model review 1A 2A 3A 4A 5A 6A 7A":

- Joins (question 1): option A, fuse the soft parts (body, necks, wing arms, thighs, tail) into one
  skin with smoothed, muscular joins; hard details (teeth, ribs, claws, crowns, feathers) stay
  separate pieces.
- Neck (question 2): option A, one massive neck root rising from the chest that forks into three.
- Colour (question 3): option A, re-bake with colour and feather pattern flowing across the joins.
- Form (question 4): option A, all of feathers over the joins, muscle and sag, ribs under torn skin,
  feathered thighs and continuous leg scales.
- Heads (question 5): option A, a second, sharper texture set for the heads and necks.
- Order (question 6): option A, the model first, then the design review's animation changes (attack
  tells, the new Crown Wakes, the stun and hits) on the new model.
- Versions (question 7): option A, a separate goose_v2 model and `art/goose/textures_v2/`, so
  version 1 keeps its exact look.

The design review's own build approval was never recorded (the session had restarted outside the
repo), so its animation work is folded into this plan after the model work.

**Why.** A living creature has no seams; one forking neck root reads as one beast and gives one
strong silhouette line; flowing colour removes the visible part boundaries; the heads are what the
player watches; building the model first means every clip is built and rendered once.

**Status.** Standing.

## 2026-10-24 — Goose design review: slow dread, fast strikes, partial hits, goose tells

**Context.** aj asked for a senior game designer's review of the version 2 goose clips for a
Soulslike game with Canadian roots, and found The Crown Wakes flickery rather than scary. The review
(`docs/plans/2026-10-24-goose-design-review.html`) counted 15 shudder bursts at 5 per second in The
Crown Wakes and crowns snapping in 0.2 s, and noted that version 2's uniform 1.4 slow-down also
slowed the strikes (charge 3.9 to 2.8 m/s).

**Decision.** aj approved "Design approved: goose design review 1A 2A 3A 4A 5A 6A":

- The Crown Wakes (question 1): option A, rebuilt slow, heavy and wrong: long stillness, the main
  neck dragged up a vertebra at a time, side heads waking first, each crown creaking out over 1 to
  1.5 s ending in one crack, one long roar with the side heads joining late. No shudder bursts.
- Tempo (question 2): option A, wind-ups 1.6, strikes 1.0 to 1.1, recoveries 1.4 times version 1;
  the strike shudder becomes one heavy shake.
- Hits (question 3): option A, the five hit reactions move only necks, heads and wings with the legs
  planted, so the game plays them on top of any clip.
- Stun (question 4): option A, the main head lies on the ground in front, in reach for a critical
  strike, through stun_fall and stun_loop.
- Tells and head roles (question 5): option A, head-pumping before the peck and lunge, the low-neck
  hiss before the charge, the wrist-strike wing in the gust; the main head leads big attacks and the
  side heads follow up.
- Phase two (question 6): option A, a separate phase-two moveset proposal after this round.

This partly supersedes the 2026-10-21 version 2 decision: its uniform 1.4 tempo and its full-body
hit reactions are replaced; everything else in it stands.

**Why.** The review's reasoning: dread comes from stillness and wrong-looking slow motion; weight
comes from wind-up and recovery while danger comes from a fast strike; full-body flinches make a
boss look weak and lockable; a stun needs a clear target; real goose threat displays give the boss
an identity of its own.

**Status.** Standing.

## 2026-10-21 — Goose animation version 2 build plan approved

**Context.** The version 2 design became a build plan of five issues under #8 (Goose animation
version 2): #9 the v2 rig and version switch, #10 the slower clips, #11 death and The Crown Wakes,
#12 stun and hits, #13 export, side-by-side videos and the pull request update.

**Decision.** aj approved it ("Build plan approved: goose animation v2 1A 2A 3A 4A 5A 6*"). The work
runs in that order on `AjsAgent/import-models` and lands on pull request #7 beside version 1.

**Why.** The tongue bones and the version switch come first because every version 2 clip is built on
them, and the switch is what keeps version 1's files from being rebuilt.

**Status.** Standing.

## 2026-10-21 — Goose animation version 2: slower, forward death, longer transition, stun and hits

**Context.** aj checked the 13 version 1 clips in pull request #7 and asked for five changes, keeping
version 1 for comparison. The proposal page `docs/plans/2026-10-21-goose-animation-v2.html` put six
choices to aj.

**Decision.** aj approved "Design approved: goose animation v2 1A 2A 3A 4A 5A 6*":

- Tempo (question 1): option A, every clip 1.4 times as long, with heavier wind-ups, strain at the
  strike and heaving recovery.
- Comparison (question 2): option A, version 2 in its own files (`goose_rigged_v2.blend`,
  `goose_animated_v2.blend`, `goose_anims_v2.fbx`, `art/goose/clips_v2/`) plus a side-by-side video
  per clip that exists in both versions. Version 1 files are not rebuilt.
- Tongues (question 3): option A, three bones per tongue on a version 2 rig of 68 bones; the mesh is
  unchanged.
- Phase transition (question 4): option A, The Crown Wakes as a 12-second set piece.
- Stun (question 5): option A, three clips: stun_fall, stun_loop, stun_get_up.
- Hits (question 6, aj's own answer): option A's four (front, left, right, heavy) plus hit_back: hit
  from behind, the goose turns round to face the attacker and shows more anger. The anger is in the
  animation; any gameplay effect belongs to the game.

Version 2 has 20 clips: idle, walk, turn_in_place, the 7 attacks, death (forward), crown_wakes, the
3 stun clips and the 5 hit reactions. Version 1's stagger is not carried into version 2.

**Why.** aj's notes: the goose is a huge ancient beast and should look like it works hard to kill
you; death forward lets the heads lie flat; the phase transition should be a spectacle; a stun gives
a punish window; varied hits stop one clip looking replayed.

**Status.** Standing. Version 1 (the entry "Goose boss animation: seven attacks...") also stands;
both versions are kept.

## 2026-10-21 — Goose boss animation build plan approved

**Context.** The design approved earlier today became a build plan of five issues under #1
(Animate the goose boss: rig and 13 clips): #2 the rig, #3 the supporting clips, #4 attack group
one, #5 attack group two with the phase transition, #6 export, manifest and pull request.

**Decision.** aj approved the build plan ("Build plan approved: goose boss animation 1 2A 3A 4A*").
The work runs in that order, one builder per issue. Bones are named from the goose's own point of
view (the goose faces -Y, so +X is its left, `.L`), the Blender convention; `goose_design.py`'s
part tags, which call +X "R", are mapped across in one table in `build_rig.py`.

**Why.** The rig must exist before any clip, and the supporting idle pose is what every attack
starts from and returns to. The bone naming follows Blender because its mirror tools and any
engine importer expect it; the design file's naming is from the viewer's side.

**Status.** Standing.

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
