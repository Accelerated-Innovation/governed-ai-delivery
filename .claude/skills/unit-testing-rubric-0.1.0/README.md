# unit-testing-rubric

A portable agent skill: standards for writing, reviewing, and evaluating
unit tests. Covers structural fidelity, the FIRST properties, behavioral
invariants, and coverage-as-diagnostic. Use whenever writing new tests,
reviewing existing tests, deciding what to test, assigning a test to a fast
vs. full feedback loop, or diagnosing flaky, slow, or low-value tests.

## Layout

```
SKILL.md      the skill itself (agent-agnostic, YAML frontmatter + body)
install       installs SKILL.md into <target>/.claude/skills/unit-testing-rubric/
package       builds dist/unit-testing-rubric-<version>.tar.gz
VERSION       current version
```

## Requirements

bash (3.2+). No other dependency.

## Usage

- `./install <target-dir>` — copies this skill into
  `<target-dir>/.claude/skills/unit-testing-rubric/SKILL.md`. Idempotent;
  overwrites only that skill's own file, not sibling skills.
- `./package` — builds a self-contained
  `dist/unit-testing-rubric-<version>.tar.gz` containing `SKILL.md`,
  `install`, `README.md`, and `VERSION`, so a recipient can install without
  cloning this repo.

## Installing manually

Any agent that reads skills from `.claude/skills/<name>/SKILL.md`
(Claude, GitHub Copilot CLI, and compatible tools) can use this skill by
copying `SKILL.md` into `<project>/.claude/skills/unit-testing-rubric/SKILL.md`.
`./install` automates exactly that copy.

## What this skill does not do

It does not write the tests itself or run a test suite. It evaluates and
guides test design and coverage decisions; execution is left to the
developer or another skill.

## Status

Single-skill package. No plugin/marketplace manifest yet beyond the
`SKILL.md` frontmatter (`name`, `description`) that agents already read
directly.
