# SOURCE_NOTES — unit-testing skill

## Sources consulted

1. `vendor-sources/canonical-tdd/canonical-tdd-skill.md` — **highest priority**
   - Frontmatter name was `split-tidy-ship`; this is the canonical Tim Ottinger / IL skill covering ZOMBIES, Tidy First?, Eight Virtues, and Canon TDD discipline.
2. `vendor-sources/tdd/SKILL.md` — Warp `tdd` skill (previously installed at `~/.agents/skills/tdd`)
3. `vendor-sources/tdd/sources/CORPUS_SUMMARY.md` — distilled Clean Start series + TDD corpus notes
4. `vendor-sources/tdd/references/anti-patterns.md` — TDD anti-patterns quick list
5. `vendor-sources/tdd-skill/SKILL.md` — near-identical to `vendor-sources/tdd/SKILL.md` (same content; tdd-skill is an older copy)
6. `vendor-sources/unit_test_engineering/SKILL.md` — FIRST diagnostics, flaky-test triage, test design guidelines
7. Tim Ottinger, ["Why Are My Tests Flakey?"](https://www.industriallogic.com/blog/why-are-my-tests-flakey/) — over-specification, cross-contamination, global state, unreliable inputs and environments, date/time errors, and intermittent production behavior; vendored at `vendor-sources/tdd-skill/sources/why-are-my-tests-flakey.md`

## What was taken

- **From canonical-tdd:** Phase 2 (Tidy First? / First-After-Later-Never), Phase 3 (ZOMBIES ordering + one-test-at-a-time canon), Phase 4 (Eight Virtues refactor target with full virtue definitions and LSP/ast-grep tool preference). These are the core TDD/microtest/tidy/ZOMBIES/virtue-refactor sections per PLAN.md instructions.
- **From tdd:** Clean Start preconditions, red-green-refactor-integrate cycle, FIRST microtest table, structure-shy / LoD guidance, high-fidelity rule, affordable feedback section, cargo-cult avoidance table, session algorithm, graceful retreat / Save Your Game discipline.
- **From unit_test_engineering:** FIRST violation diagnostic table (symptom → violation → root causes → repair), flaky-test repair approaches, test design anti-patterns (god test, shared fixture mutation, sleep-based sync), "one behavior per test" rule.
- **From "Why Are My Tests Flakey?":** operational evidence for Isolated and Repeatable tests; order randomization as a diagnostic rather than a repair; controlled, test-specific environments; unordered-result handling; calendar-boundary and synchronization guidance; and the distinction between a flaky test and a reliable test exposing flaky production code.
- **Resilience interpretation:** frequent edits to existing tests during behavior-preserving production work are treated as evidence of over-specification or structural coupling. The skill requires classifying a break as an intentional contract change, production regression, brittle test, or unresolved cause before editing the test.
- **From tdd/references/anti-patterns.md:** supplemented and deduplicated into `references/anti-patterns.md`.

## What was dropped

- **Phase 1 (story splitting / INVEST/SPIDR)** — belongs to `story-splitting-for-delivery` per PLAN.md.
- **Phase 5 (trunk landing, feature toggles, Branch by Abstraction, MMMSS gates)** — out of scope for this package per PLAN.md.
- **Full article dumps** from `vendor-sources/tdd/sources/` (Clean Start series text, full URI corpus) — too bulky; CORPUS_SUMMARY.md content was distilled into skill body instead.
- **`tdd-skill/sources/` directory** — identical to `tdd/sources/`; not duplicated.
- **BDD/examples section** from CORPUS_SUMMARY — kept only the "BDD complements TDD; does not replace microtesting" note within the cargo-cult table; full BDD treatment belongs elsewhere.
- **MMMSS shipping gate logic** from canonical-tdd Phase 5.

## Key design choices

- Merged all three source skills into ONE `SKILL.md` body (no sibling skills); PLAN.md rule "one concept, one skill."
- ZOMBIES section is now a first-class section (not buried), matching canonical-tdd priority.
- Tidy First? is integrated into the cycle diagram and has its own section, with explicit First/After/Later/Never choices.
- The Industrial Logic Red-Green-Refactor-Integrate loop is expanded operationally as Clean Start → test list → Tidy First? → Red → Green → Refactor → authorized atomic Save Your Game microcommit → separately verified shared integration. Human review participates in the rapid microcommit loop; the local commit and integration are intentionally not conflated.
- Eight Virtues doctrine matches the review skill: Working is non-negotiable; the other seven are peers in balance.
- FIRST diagnostic table from `unit_test_engineering` is kept as a quick triage reference within the skill body.
- `agents/openai.yaml` default_prompt is an ordered operational checklist usable directly by Codex.
- `references/anti-patterns.md` is lean; points back from SKILL.md with one line rather than duplicating all items.

## Deferred evaluations and design options (not release blockers)

1. **Eight Virtues canonical source** — the virtue definitions come from canonical-tdd-skill.md (Ottinger & Langr); if a dedicated shared reference is later useful, both `unit-testing` and `representation-refactor-review` could link to it rather than duplicate it.
2. **Description trigger wording** — the current `description:` frontmatter uses a concise capability boundary. Validate it against real routing prompts before expanding it.
