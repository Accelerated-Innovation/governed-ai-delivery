# Source map

Use this file when you need deeper provenance or alternate phrasing.
Prefer the progressive admission article first. Use the resource list only when the admission boundary is unclear and broader splitting ideas would help identify the next case.

## Primary sources

- **Progressive Admission Pattern** (Agile Otter)
  https://agileotter.blogspot.com/2026/08/progressive-admission-pattern-for-data.html
  Core sequence: start closed → first admissions → additional admissions → keep reject path → continue forever.
  Applies beyond queues to any input-process-output cycle, including UI controls and form fields.
  Also covers interface versioning (minor for new admissions, major for changes to shipped contracts).

- **Splitting Stories resource list** (Agile Otter)
  https://agileotter.blogspot.com/2022/03/splitting-stories-resource-list.html
  Framing: end-to-end slices beat top-down design / bottom-up implementation.
  Always prefer N% of the system 100% done over 100% of the system N% done.

## Supporting ideas from the resource list
Use these as supporting vocabulary, not as a second competing workflow.

- **Walking skeleton / tracer bullet**: prove the end-to-end path exists early; this is slice 0.
- **Evolutionary design / primitive whole**: grow a working whole instead of assembling finished parts late.
- **Whole stories for whole teams**: keep product and engineering in one conversation around the split.
- **Bargain hunting**: choose the next slice by value and learning per effort, not by completeness.
- **Scatter-gather avoidance**: avoid splits where value appears only after late integration.
- **Example/test-based splitting**: when stuck, split by concrete examples. Each example that requires different code is a candidate admission boundary.
- **SPIDR and other pattern menus** (Spike, Path, Interface, Data, Rules): useful prompts for finding the next admission case, not a separate primary workflow.

## How this skill does story splitting
Many splitting guides ask: "What thin vertical slices deliver value?"
This skill answers through progressive admission: "What is closed by default, and which single case do we open next?"

That second question is the default operating mode here.
Supporting pattern menus (SPIDR, hamburger, paths/data/rules) are prompts for finding the next admission — not an alternative primary workflow.

## Lower-priority pointers from STORY_SPLITTING_SKILL.md (old listicle)
The vendor file `STORY_SPLITTING_SKILL.md` contains a richer SPIDR-first menu, the hamburger method, and a 30-minute facilitation script.
Those are useful as backup vocabulary if the team is stuck in technical decomposition. Do not resurrect that workflow as a primary path; fold only the vocabulary into `source-map.md` (done above).
