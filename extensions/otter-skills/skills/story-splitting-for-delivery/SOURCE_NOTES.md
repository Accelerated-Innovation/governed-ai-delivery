# SOURCE_NOTES — story-splitting-for-delivery skill pair

Covers both skills in this family:
- `skills/story-splitting-for-delivery/`
- `skills/user-pov-sliced-stories/`

## What was taken

### From `vendor-sources/iterative-story-split/SKILL.md` (priority source)
- Full progressive admission workflow: start closed → first admissions → admit one → widen → keep reject path → forever.
- Admission boundary naming, default-rejection framing, slice quality gate.
- Versioning guidance (minor/major semantics for admitted contracts).
- Required output format (progressive admission plan template) — kept verbatim.
- Sequencing heuristics and bargain-hunting framing.
- Anti-patterns list.
- Facilitation script (20–30 min).
- Worked micro-example (account update queue).
- Cross-link to `user-pov-sliced-stories` as optional formatter.
- Source URLs: progressive admission article + splitting resource list.

### From `vendor-sources/iterative-story-split/references/source-map.md` (priority source)
- Full content adapted into `references/source-map.md`, with one addition: a note about the old listicle source so lead integrators know why it was deprioritized.

### From `vendor-sources/user-pov-sliced-stories/SKILL.md` (priority source)
- Formatter-only role clarified up front.
- Workflow (create admission plan first, then restate in user POV).
- Required output format (User invokes / User uses result / Acceptance checks / Not yet in slice).
- Sequencing rules, quality gate, response style.
- Cross-link to `story-splitting-for-delivery` as the primary splitter.

## What was dropped

### From `vendor-sources/STORY_SPLITTING_SKILL.md` (lower priority, old listicle)
- **Dropped entirely from skill bodies**: SPIDR-first primary workflow, hamburger method full procedure, 8-step facilitation script, split pattern menu (26+ sub-bullets), worked "pay bills online" example.
- **Vocabulary preserved** (in `references/source-map.md` only): walking skeleton, tracer bullet, bargain hunting, scatter-gather avoidance, SPIDR as backup prompt vocabulary, hamburger method name-only pointer.
- Source links from the listicle (Gojko, Dinwiddie, Cohn, Wake, Killick, etc.) were not added to the package. They are available in the original vendor file for anyone who needs them.

## Design choices

- Two skills remain separate by design: triggers and outputs differ. `story-splitting-for-delivery` outputs an admission plan; `user-pov-sliced-stories` outputs formatted slice descriptions for stakeholders.
- Progressive admission is the **only** primary workflow in `story-splitting-for-delivery`. SPIDR and other pattern menus are demoted to vocabulary in `references/source-map.md`, used only to name the next admission boundary when it is unclear.
- `user-pov-sliced-stories` sets `allow_implicit_invocation: false` in its Codex config — it should only trigger when the user explicitly wants user-POV formatting, not when they ask for a split.
- Family framing: **story-splitting-for-delivery** (progressive admission for delivery-ready thin vertical slices), not generic story writing.
- The canonical installable copies are the skill directories in this repository. Older user-level Warp copies are source history and may be replaced manually using the root installation guidance.

## Deferred evaluations (not release blockers)

- Keep `user-pov-sliced-stories` explicit-only unless routing evaluations show
  that prompts such as “how do we describe these slices?” reliably intend that
  formatter rather than the primary splitter.
- Add a condensed bibliography from the old listicle to
  `references/source-map.md` only if users demonstrate a recurring need to cite
  those outside authors.
