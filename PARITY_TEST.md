# Parity Test Guide

govkit has two parity invariants that this guide documents and verifies:

1. **Project shape parity (v0.8)** — every supported `(agent, shape, level)` combination produces a clean, leak-free install with byte-identical skill content across agents
2. **Language-agnostic parity (v0.7)** — agent rules reference `docs/backend/architecture/` files; swapping out the docs stack produces equivalent guidance without rule changes

The v0.8 matrix is the primary current concern. The v0.7 invariant remains in force and is still tested manually when stack docs change.

---

## v0.8 Project Shape Parity Matrix

The flat `--type` enumeration (`api`, `cli`, `ui-react`, `ui-angular`) crosses with three maturity levels and three agents:

| Dimension | Values | Count |
|---|---|---|
| Agent | `claude-code`, `codex`, `copilot` | 3 |
| Shape (`--type`) | `api`, `cli`, `ui-react`, `ui-angular` | 4 |
| Level | `3`, `4`, `5` | 3 |
| **Total combinations** |  | **36** |

The smoke matrix produces a subset of these (it omits `--type cli` at each level — backend coverage is provided by `--type api` since the resolver path is identical):

| Smoke script | Configurations | Total |
|---|---|---|
| `scripts/smoke.ps1` | 3 agents × `--type api` × 3 levels | 9 |
| `scripts/smoke-ui.ps1` | 3 agents × {`ui-react`, `ui-angular`} × 3 levels | 18 |
| `scripts/smoke-dotnet.ps1` | 3 agents × `--type api` × 3 levels (.NET-flavored feature content) | 9 |
| **Smoke matrix total** |  | **36** |

A clean run of all three smoke scripts is the automated parity check. Plan §15 of [plans/PROJECT_SHAPE_REFACTOR_PLAN.md](plans/PROJECT_SHAPE_REFACTOR_PLAN.md) defines the done-criteria.

---

## What v0.8 parity asserts

### 1. Apply succeeds for every combination

`govkit apply` must complete with exit 0 for every `(agent, shape, level, ci)` combination. The smoke scripts exit 0 if all applies succeed; L4/L5 validate failures are tolerated by design (smoke features intentionally ship only the 3 spec inputs so the planning skills have something to do).

### 2. Zero cross-shape leakage

Backend installs must not ship UI artifacts; UI installs must not ship backend artifacts. The Inc 16 leakage check in [plans/PROJECT_SHAPE_REFACTOR_PLAN.md §15](plans/PROJECT_SHAPE_REFACTOR_PLAN.md#section-15) enforces this on 18 backend + 18 UI sandboxes against ~26 leak patterns.

What "leakage" specifically means:

| Backend sandbox MUST NOT contain | UI sandbox MUST NOT contain |
|---|---|
| `src/CLAUDE.md` (Claude UI nested) | `docs/backend/architecture/` |
| `src/AGENTS.md` (Codex UI subtree) | `governance/backend/` |
| `docs/ui/`, `governance/ui/` | `.claude/rules/services.md`, `ports.md`, `adapters.md`, `api.md` (backend layer rules) |
| `.claude/rules/components.md`, `viewmodel.md`, `ui-api.md`, `accessibility.md` | `.claude/skills/spec-planning/` (vs `ui-spec-planning/` for UI) |
| `.claude/skills/ui-*` | `services/AGENTS.md` at repo root (Codex backend hex layer) |
| `ci/<provider>/ui-quality-gate.yml`, `l3-ui-quality-gate.yml` | `ci/<provider>/l3-quality-gate.yml`, `quality-gate.yml`, `eval-gate.yml` |

### 3. Skill content byte-identical across agents

Every `SKILL.md` across `agents/{claude-code,codex,copilot}/skills/**/` ships **frontmatter that is byte-identical** for the same skill across agents. The Open Skills format is the lowest common denominator — `name:` + `description:` only, no `argument-hint:` or `user-invocable:` extensions.

The 11 skills (7 backend + 4 UI) × 3 agents = 33 SKILL.md files. `tests/test_govkit.py::TestNoUiDimensionInManifests` and the skill-resolution tests lock this in.

### 4. Agent-specific loader behavior

Each agent's native progressive-loading mechanism is exercised:

| Agent | Mechanism | Verified by |
|---|---|---|
| Claude Code | Nested `CLAUDE.md` (root + `src/CLAUDE.md` for UI shapes) | Inc 8 IDE test + tree spot-check |
| Codex | Hierarchical `AGENTS.md` walk (root + per-layer nested) | Inc 10 dest verification + tree spot-check |
| Copilot | `.instructions.md` with `applyTo:` globs (`src/**/...` scoped) | Inc 9 applyTo audit + tree spot-check |

The `tmp/post-refactor-tree.txt` snapshot from Inc 16 is the canonical record of post-refactor sandbox layouts.

---

## Running the v0.8 parity check

### Automated

```powershell
.\scripts\smoke.ps1 -Force
.\scripts\smoke-ui.ps1 -Force
.\scripts\smoke-dotnet.ps1 -Force
```

Expected: 36/36 apply PASS, all L3 validate PASS, L4/L5 validate FAIL by design.

For a textual snapshot of every sandbox:

```powershell
.\scripts\smoke-inspect.ps1 -All -Editor tree > tmp\post-refactor-tree.txt
```

Spot-check that backend sandboxes contain no UI artifacts and vice versa.

### Unit tests

```bash
pytest tests/
```

Should report 366 passed (post-Inc-15). Key parity-related test classes:

- `tests/test_govkit.py::TestNoUiDimensionInManifests` — production manifests don't carry the dropped `ui` dimension
- `tests/test_govkit.py::TestResolveVariantFiles` (by-type dispatch tests) — CI gates dispatch correctly per shape
- `tests/test_govkit.py::TestShapeMigrationWarning` — legacy `options.ui` markers are read tolerantly
- `tests/test_validate.py::TestValidateUiShapes` — UI markers and 5-artifact validation are type-opaque
- `tests/test_schemas.py::TestSchemaRejects` and `TestSchemaAcceptsNewShapes` — schema rejects legacy `ui` and accepts new UI shapes

### Manual IDE checks

For high-confidence verification of the loader behavior, open a UI sandbox in each agent's native tool and probe for the expected layer-specific rule citations. See [docs/MONOREPO_PATTERN.md](docs/MONOREPO_PATTERN.md) for per-agent loader specifics.

---

## v0.7 Language-Agnostic Parity (still in force)

The earlier v0.7 refactor moved language-specific content out of agent rules and into `docs/backend/architecture/`. Rules reference docs; rules don't embed FastAPI / .NET / Java / Go specifics. The default docs ship FastAPI-by-default; switch stacks by copying from `docs/stacks/<stack>/` into `docs/backend/architecture/` (see README "Switching Tech Stacks").

This parity invariant is:

> All architecture rules in `agents/{claude-code,codex,copilot}/rules/backend/*.md` and `rules/cli/*.md` open with a pointer to the relevant `docs/backend/architecture/*.md` file. Universal architectural constraints (boundaries, FIRST, 7 Virtues, ADR triggers) are restated in the rule body; stack-specific patterns are not.

### When to re-verify v0.7 parity

- A new stack is added under `docs/stacks/` and you want to confirm agents pick it up correctly
- A rule file is modified — verify it still leads with the `docs/backend/architecture/<DOC>.md` pointer
- An architecture doc is moved or renamed — every rule that references it must be updated in lockstep

### How to verify v0.7 parity (manual)

The most reliable check is to apply a sandbox, swap in a non-default stack, and ask each agent to plan a small feature:

```bash
# Apply Python/FastAPI default
govkit apply --agent claude-code --type api --target /tmp/parity-fastapi

# Apply same, then swap to .NET/ASP.NET Core
govkit apply --agent claude-code --type api --target /tmp/parity-dotnet
cp docs/stacks/dotnet-aspnet/* /tmp/parity-dotnet/docs/backend/architecture/
```

Open both in Claude Code and ask each: *"Plan a new feature that adds a `GET /v1/widgets/{id}` endpoint."* Expected behavior:

- The FastAPI sandbox plan uses Pydantic models, `Depends(get_current_user)`, FastAPI decorators, `TestClient`
- The .NET sandbox plan uses minimal API endpoints, `[FromRoute]` / `[FromBody]`, dependency injection via `IServiceCollection`, xUnit + `WebApplicationFactory`

The **same rules** drove both responses — the difference came entirely from the swapped docs.

### v0.7 parity by file count

The v0.7 refactor touched 36 files (12 rules + 12 L3 entries + 12 L4/L5 entries). Every file must lead with a doc pointer. Quick verification:

```bash
# All rules reference docs/
grep -L "Your project" agents/{claude-code,copilot,codex}/rules/backend/*.md \
                      agents/{claude-code,copilot,codex}/rules/cli/*.md

# Should output nothing — if any file is listed, it's missing the doc pointer
```

```bash
# All entry files have a Project Documentation section
grep -L "Project Documentation" agents/{claude-code,copilot,codex}/claude-md/backend-*.md \
                                 agents/{claude-code,copilot,codex}/agents-md/backend-*.md \
                                 agents/{claude-code,copilot,codex}/copilot-instructions/backend-*.md
# Should output nothing
```

---

## References

- [plans/PROJECT_SHAPE_REFACTOR_PLAN.md](plans/PROJECT_SHAPE_REFACTOR_PLAN.md) — v0.8 refactor (project-shape parity)
- [scripts/README.md](scripts/README.md) — smoke script reference
- [docs/MONOREPO_PATTERN.md](docs/MONOREPO_PATTERN.md) — per-agent loader specifics under subpath installs
- [docs/stacks/README.md](docs/stacks/README.md) — stack swap guide (v0.7 parity surface)
- [CHANGELOG.md](CHANGELOG.md) — release history
