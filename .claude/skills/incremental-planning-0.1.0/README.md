# incremental-planning

A portable agent skill for breaking implementation work into the smallest
independently demonstrable increments, before any code is written.

## Layout

```
SKILL.md      the skill itself (agent-agnostic, YAML frontmatter + body)
install       installs SKILL.md into <target>/.claude/skills/incremental-planning/
package       builds dist/incremental-planning-<version>.tar.gz
VERSION       current version
```

## Requirements

bash (3.2+). No other dependency.

## Usage

- `./install <target-dir>` — copies this skill into
  `<target-dir>/.claude/skills/incremental-planning/SKILL.md`. Idempotent;
  overwrites only that skill's own file, not sibling skills.
- `./package` — builds a self-contained
  `dist/incremental-planning-<version>.tar.gz` containing `SKILL.md`,
  `install`, `README.md`, and `VERSION`, so a recipient can install without
  cloning this repo.

## Installing manually

Any agent that reads skills from `.claude/skills/<name>/SKILL.md`
(Claude, GitHub Copilot CLI, and compatible tools) can use this skill by
copying `SKILL.md` into `<project>/.claude/skills/incremental-planning/SKILL.md`.
`./install` automates exactly that copy.

## What this skill does not do

It does not write code, tests, commits, or architecture, and it does not
choose implementation approaches. It classifies requests and proposes the
next demonstrable increment(s); execution is left to other skills or to the
developer.

## Status

Single-skill package. No plugin/marketplace manifest yet beyond the
`SKILL.md` frontmatter (`name`, `description`) that agents already read
directly.
