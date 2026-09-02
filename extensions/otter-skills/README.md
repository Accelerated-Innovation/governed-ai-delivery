# Otter Skills (third-party extension pack)

Seven software-craft agent skills by Tim Ottinger, vendored from the open-source
[otter-skills](https://github.com/tottinge/otter-skills) repository: unit
testing (TDD/microtests), atomic commits, story splitting, user-POV story
slicing, code and object naming, legacy-code safety, and representation
refactoring review.

This is **third-party content**. govkit vendors a pinned copy so installs stay
deterministic and offline — nothing is fetched from the network at install
time. The upstream LICENSE and NOTICE ship in this pack and travel with every
copy `govkit extension add` makes.

<!-- sync:provenance -->
| Upstream | https://github.com/tottinge/otter-skills |
|---|---|
| Pinned commit | `c9acbd139d182211cbea9b8f6d22a47af15266df` |
| Upstream version | 0.1.6 |
| License | Apache-2.0 (LICENSE and NOTICE ship in this pack) |
<!-- /sync:provenance -->

## Install

```bash
govkit extension add otter-skills --target .
```

The pack lands at `extensions/otter-skills/`, and each skill installs into the
applied agent's skills directory under an `otter-` prefix — for Claude Code,
`.claude/skills/otter-unit-testing/` and so on (`.agents/skills/` for Codex,
`.github/skills/` for Copilot). The prefix keeps these clearly third-party and
collision-free next to your own skills and govkit's `govkit-*` skills.

A skill directory that already exists is **skipped, never overwritten** — your
edits and independently-installed copies survive. Refresh everything to the
bundled version with:

```bash
govkit extension add otter-skills --target . --force
```

## Remove

There is no `extension remove` command yet; removal is manual:

```bash
rm -r extensions/otter-skills .claude/skills/otter-*   # adjust the skills dir per agent
```

## Tracking upstream directly

The bundled copy updates only when govkit re-vendors and releases. If the
upstream repository gains a govkit `manifest.yaml` at its root, you can skip
the bundled copy entirely and pull from source — pinned into your own repo:

```bash
govkit extension add --from-git https://github.com/tottinge/otter-skills --target .
```

Re-running with `--force` pulls upstream changes as a reviewable diff in your
project.

## Re-vendoring (govkit maintainers)

`scripts/sync_otter_skills.py` refreshes this pack from a new upstream commit;
it regenerates `manifest.yaml` and this file's provenance block. Each skill's
upstream `agents/` subdir (OpenAI agent-builder config) is intentionally not
vendored. See `origin` in [manifest.yaml](manifest.yaml) for the exact pin.
