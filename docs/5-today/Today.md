# Today — 2026-10-25

**Done:** removed the maple leaf brand from goose_v2's breast, after aj said it looked comical
rather than fearful; version 1 keeps it. aj said the neck work is taking shape.

**Next, in order:** aj's QA pass on #18 with #25; push the branch; then #19, #20 and #21.

---

# Today — 2026-10-24

**Done:** started the goose version 2 chain at Models #18 (one fused skin and a forking neck root), as aj
chose. A throwaway test (`docs/art/reviews/goose-v2-prototype/prototype_fuse.py`) fused the soft parts
into one closed skin in about 5 seconds with 0 non-manifold edges. The build plan is
`docs/plans/2026-10-24-goose-v2-skin.html`.

Built #18 (steps #22, #23, #24): `goose_v2` with one fused skin and the forking neck root; the
one-shell check caught the wing arms stopping 0.1 m short of the body, so in version 2 they now
reach into it. Review sheet: `docs/art/reviews/goose-v2-review.png`.

aj's QA check failed #18: the necks read as rigid, smooth tubes. Designed and built #25 (#26, #27):
S-curved necks with vertebra ridges and a bone spike per vertebra; 297,820 triangles.

**Next, in order:** aj reviews #18 with #25; then #19, #20 and #21.

---

# Today — 2026-10-21

**Done:** moved the goose and scythe here; designed and got approval for the goose animation;
scaffolded the documentation tiers; built the 59-bone rig (#2), the five supporting clips (#3),
attack group one (#4), attack group two and The Crown Wakes (#5), and the FBX export, manifest and
docs (#6); fixed the Flapping Charge foot slide.

**Not done, on purpose:** no engine import (aj chose this repo only); no phase-two idle (not chosen).

**Next, in order:** aj checks the clips in the pull request; fixes from that check; merge.
