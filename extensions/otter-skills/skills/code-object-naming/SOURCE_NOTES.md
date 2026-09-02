# SOURCE_NOTES — code-object-naming

Author: naming-skill child agent
Source: `vendor-sources/naming_shortguide/` (manuscript MD chapters)

## Chapters read
- `introduction.md` — context/priority framing only; not operational
- `the_point.md` — key stats, Benner's 4 criteria, human+AI comprehension argument
- `nouns_and_verbs.md` — parts-of-speech rules, getter noun preference, `as` conversion signal
- `context.md` — hierarchy, windshield naming, domain terms, noise words, over-contextualization
- `familiarity.md` — profitable/unprofitable struggle, audience question, idiom principle
- `length.md` — scope-to-length matching, primacy, idiomatic nicknames (df/G/fig)
- `incrementalism.md` — Belshee's scale, obviously-bad names, safe rename protocol, caveats
- `extraction.md` — paragraph markers → functions, predicate extraction, class-split signal, browseability
- `conclusion.md` — skimmed; no new operationalizable content
- `foreword.md` — skimmed; framing only; dropped

## What was taken
- Belshee's naming-as-a-process 5-stage scale (core of Step 1 in workflow)
- Noun/verb/adjective grammar rules for code objects (Step 2)
- Context hierarchy + redundancy test + windshield naming + domain-term principle (Step 3)
- Scope-to-length table + primacy rule + idiomatic nicknames (Step 4)
- Incremental rename protocol + obviously-bad-name technique + rename caveats (Step 5)
- Extraction moments decision table (Step 5)
- Benner's 4 criteria (Understandability, Conciseness, Consistency, Distinguishability) — folded
  into the Name Audit checklist (not called out by name; Ottinger's framing preferred)
- Statistics from `the_point.md`: ~20% defect-location speedup, ~30% LLM token reduction

## What was dropped
- `introduction.md` prerequisites list (working code, tests, deploy pipeline) — acknowledged
  in one sentence in SKILL.md "Why Names Matter" but not reprinted
- Extended prose examples (FizzBuzz obfuscation demo, chocolate aisle analogy, bicycle tire
  patch analogy) — summarized as principles, not quoted
- `conclusion.md` — no operational content discovered; skipped
- `foreword.md` — no operational content
- `the_point.md` duplicate section (file contained apparent duplicate block starting line ~175)
  — treated as artifact of manuscript draft format; content used from first occurrence only
- Benner book citation (`Naming Things`, LeanPub 2025) and OOSC/Meyer citation — noted in
  digests but not embedded in SKILL.md body (lean packaging preference)
- Footnotes and bibliography — omitted from digests; Belshee URL retained in ch-incrementalism
  as it points to a live reference useful to agents

## Design choices
1. **Progressive disclosure**: SKILL.md is the complete operational workflow; references/ provide
   chapter-level depth without requiring agents to read all of them.
2. **Tables over prose** for decision rules and checklists — easier for agents to process.
3. **Belshee's scale** made explicit and central (Step 1) because it gives a shared vocabulary
   for discussing naming quality incrementally.
4. **Windshield naming** elevated to a named principle in SKILL.md body (not buried in references)
   because it is the most concise heuristic for intent vs. composition.
5. **Cross-link to representation-refactor-review** rather than duplicating Eight Virtues content.

## Deferred publication consideration

If the manuscript sources themselves are prepared for publication, clean the
known layout artifacts in `the_point.md` and confirm that `conclusion.md` is
complete. That source-publication work is outside this packaged skill.

The Benner book (`Naming Things`, LeanPub 2025) remains a skill-local source
note. A repository-wide bibliography is unnecessary unless more skills begin to
share that source.
