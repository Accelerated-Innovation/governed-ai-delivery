# Smoke test scripts

PowerShell scripts that exercise `govkit apply` and `govkit validate` across the supported agent × type × level matrix. Used for pre-release smoke checks and as a baseline for the project-shape refactor (see [plans/PROJECT_SHAPE_REFACTOR_PLAN.md](../plans/PROJECT_SHAPE_REFACTOR_PLAN.md)).

## What's here

| Script | Matrix | Output dir |
|---|---|---|
| `smoke.ps1` | 3 agents × 3 levels (`--type api`) | `scripts/projects/` |
| `smoke-ui.ps1` | 3 agents × 2 frameworks × 3 levels (`--type api --ui react\|angular`) | `scripts/projects-ui/` |
| `smoke-dotnet.ps1` | 3 agents × 3 levels (`--type api`, .NET-realistic feature content) | `scripts/projects-dotnet/` |

Output dirs and the bootstrapped `.venv/` are gitignored — running the scripts won't dirty your working tree.

## Prerequisites

- Python 3.11+ on PATH (the script bootstraps its own venv).
- PowerShell 7+ recommended (works in 5.1 too).
- The repo cloned somewhere (the scripts auto-detect their parent when run from `scripts/`).

## Quick start

From the repo root:

```powershell
.\scripts\smoke.ps1
```

First run installs `govkit` editable into `scripts/.venv/`. Subsequent runs reuse the venv.

Force a clean re-run (delete all existing sandbox dirs first):

```powershell
.\scripts\smoke.ps1 -Force
```

Subset of the matrix:

```powershell
.\scripts\smoke.ps1 -Agents claude-code -Levels 4 -Force
.\scripts\smoke-ui.ps1 -Frameworks react -Levels 3,4 -Force
```

## Parameters (all three scripts)

| Parameter | Default | Notes |
|---|---|---|
| `-SandboxRoot` | `$PSScriptRoot` (i.e. `scripts/`) | Where the venv and per-config project dirs are created. Override to write somewhere outside the repo. |
| `-RepoPath` | parent of `$PSScriptRoot` (i.e. repo root) | The govkit source the venv installs from. Override to point at a different checkout. |
| `-Agents` | `claude-code,codex,copilot` | Restrict to a subset of agents. |
| `-Levels` | `3,4,5` | Restrict to a subset of maturity levels. |
| `-Force` | (off) | Delete existing sandbox dirs before recreating. Without this, existing dirs are skipped. |

`smoke-ui.ps1` also accepts `-Frameworks react,angular` for the UI dimension.

## Redirecting output to an external sandbox

If you want output to land outside the repo (e.g. to keep your sandbox state across repo branches):

```powershell
.\scripts\smoke.ps1 -SandboxRoot c:\users\marty\source\sandbox\govkit-test
```

The script will create `c:\users\marty\source\sandbox\govkit-test\.venv\` and `c:\users\marty\source\sandbox\govkit-test\projects\` instead of using the in-repo paths.

## Expected results

- **L3 apply + validate** — green. L3 validate short-circuits (no per-feature artifacts).
- **L4 apply + validate** — green. Each sandbox gets a minimal smoke feature (`hello_world_api`, `hello_world_ui`, or `hello_world_dotnet_api`) covering the 5-artifact contract.
- **L5 apply** — green. The folder is created and the level-5 root file is installed.
- **L5 validate** — **FAILS as expected**. The smoke features are `mode: deterministic`; L5-specific checks require `mode: llm`. The script's exit code excludes L5 validate failures from the overall pass/fail decision.

A successful overall run prints:
```
All apply steps and L3/L4 validates passed. L5 validate is expected to fail until
the smoke feature is extended with LLM artifacts.
```

## Troubleshooting

**"govkit version: 0.7.0" but I just edited the repo and don't see my changes.**
The venv has a cached editable install. Delete `scripts/.venv/` and re-run — the script will recreate the venv against the current repo state.

**`python` not on PATH.**
The script uses whatever `python` resolves to in your shell. Either add Python 3.11+ to PATH or modify the script's `python -m venv $venvDir` line to use an absolute path.

**Pre-commit warnings about `.venv/` or sandbox dirs being tracked.**
They shouldn't be — the `.gitignore` covers them. If they show up in `git status`, verify the `.gitignore` entries are present and that no parent `.gitignore` has un-ignored them.

## Related plans

- [plans/PROJECT_SHAPE_REFACTOR_PLAN.md](../plans/PROJECT_SHAPE_REFACTOR_PLAN.md) — these scripts are baseline tooling for the v0.8.0 refactor. Increment 0b adds a visual-inspection helper (`smoke-inspect.ps1`). Increment 11 rewrites the apply invocations (drops `--ui`, splits backend/UI by `--type`).
