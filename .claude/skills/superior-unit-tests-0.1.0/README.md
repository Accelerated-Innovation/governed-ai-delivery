# superior-unit-tests

A portable agent skill: write or improve unit tests following a strict
determinism, F.I.R.S.T., and fast-feedback-budget discipline. Use when asked
to write tests, improve tests, review test quality, classify tests, or
assess a test suite against a 30-second fast-feedback budget. Invokes a
structured output protocol that identifies behaviors under protection,
classifies each test by level and feedback loop, and flags nondeterminism
risks.

## Layout

```
SKILL.md      the skill itself (agent-agnostic, YAML frontmatter + body)
install       installs SKILL.md into <target>/.claude/skills/superior-unit-tests/
package       builds dist/superior-unit-tests-<version>.tar.gz
VERSION       current version
```

## Requirements

bash (3.2+). No other dependency.

## Usage

- `./install <target-dir>` — copies this skill into
  `<target-dir>/.claude/skills/superior-unit-tests/SKILL.md`. Idempotent;
  overwrites only that skill's own file, not sibling skills.
- `./package` — builds a self-contained
  `dist/superior-unit-tests-<version>.tar.gz` containing `SKILL.md`,
  `install`, `README.md`, and `VERSION`, so a recipient can install without
  cloning this repo.

## Installing manually

Any agent that reads skills from `.claude/skills/<name>/SKILL.md`
(Claude, GitHub Copilot CLI, and compatible tools) can use this skill by
copying `SKILL.md` into `<project>/.claude/skills/superior-unit-tests/SKILL.md`.
`./install` automates exactly that copy.

## What this skill does not do

It does not run the test suite or choose a test framework. It structures how
tests should be written, classified, and budgeted; execution is left to the
developer or another skill.

## Status

Single-skill package. No plugin/marketplace manifest yet beyond the
`SKILL.md` frontmatter (`name`, `description`) that agents already read
directly.
