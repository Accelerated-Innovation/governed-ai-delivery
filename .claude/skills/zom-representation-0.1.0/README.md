# zom-representation

A portable agent skill for reasoning about representation changes in
existing code: Zero-One-Many Representation Evolution. Applies whenever
code needs to change, grow, or be refactored — surfacing representation
pressure (numbered variables, growing conditionals, repeated parameter
groups, scattered constants) and guiding it toward a more coherent shape.

## Layout

```
SKILL.md      the skill itself (agent-agnostic, YAML frontmatter + body)
install       installs SKILL.md into <target>/.claude/skills/zom-representation/
package       builds dist/zom-representation-<version>.tar.gz
VERSION       current version
```

## Requirements

bash (3.2+). No other dependency.

## Usage

- `./install <target-dir>` — copies this skill into
  `<target-dir>/.claude/skills/zom-representation/SKILL.md`. Idempotent;
  overwrites only that skill's own file, not sibling skills.
- `./package` — builds a self-contained
  `dist/zom-representation-<version>.tar.gz` containing `SKILL.md`,
  `install`, `README.md`, and `VERSION`, so a recipient can install without
  cloning this repo.

## Installing manually

Any agent that reads skills from `.claude/skills/<name>/SKILL.md`
(Claude, GitHub Copilot CLI, and compatible tools) can use this skill by
copying `SKILL.md` into `<project>/.claude/skills/zom-representation/SKILL.md`.
`./install` automates exactly that copy.

## What this skill does not do

It does not implement the refactor itself, choose a language or framework,
or run tests. It observes representation pressure, applies the 8 Code
Virtues framework, and recommends how a representation should evolve;
execution is left to the developer or another skill.

## Status

Single-skill package. No plugin/marketplace manifest yet beyond the
`SKILL.md` frontmatter (`name`, `description`) that agents already read
directly.
