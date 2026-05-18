# Smoke test scripts

PowerShell scripts that exercise `govkit apply` and `govkit validate` across the supported agent × type × level matrix. Used for pre-release smoke checks and as a baseline for the project-shape refactor (see [plans/PROJECT_SHAPE_REFACTOR_PLAN.md](../plans/PROJECT_SHAPE_REFACTOR_PLAN.md)).

## What's here

| Script | Matrix | Output dir |
|---|---|---|
| `smoke.ps1` | 3 agents × 3 levels (`--type api`) | `scripts/projects/` |
| `smoke-ui.ps1` | 3 agents × 2 frameworks × 3 levels (`--type api --ui react\|angular`) | `scripts/projects-ui/` |
| `smoke-ui-new.ps1` | 3 agents × 2 UI shapes × 3 levels (`--type ui-react\|ui-angular`) — tactical, superseded by Phase 4 Inc 11 | `scripts/projects-ui-new/` |
| `smoke-dotnet.ps1` | 3 agents × 3 levels (`--type api`, .NET-realistic feature content) | `scripts/projects-dotnet/` |
| `smoke-inspect.ps1` | Visual inspection helper (no apply/validate) | Reads from `scripts/projects*/` |

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

Each smoke feature ships only the **3 spec inputs** — `acceptance.feature`, `nfrs.md`, `eval_criteria.yaml`. `plan.md` and `architecture_preflight.md` are intentionally absent so the `/architecture-preflight` and `/spec-planning` skills can be invoked against the sandbox to generate them. This means L4 (and L5) validate will fail by design.

- **L3 apply + validate** — green. L3 validate short-circuits (no per-feature artifacts).
- **L4 apply** — green.
- **L4 validate** — **FAILS as expected**. Missing `plan.md` and `architecture_preflight.md` are the trigger. Run `/architecture-preflight <feature>` and `/spec-planning <feature>` in the agent against the sandbox to populate them; re-run `govkit validate` and it should pass.
- **L5 apply** — green.
- **L5 validate** — **FAILS as expected**. Same artifacts missing, plus `mode: deterministic` doesn't satisfy L5-specific LLM checks.

The script's exit code excludes L4 and L5 validate failures from the overall pass/fail decision. A successful overall run prints:
```
All apply steps and L3 validate passed. L4/L5 validate are expected to fail
until /architecture-preflight and /spec-planning generate the missing artifacts.
```

## Inspecting sandboxes (`smoke-inspect.ps1`)

After running a smoke script, use `smoke-inspect.ps1` to open one or more sandbox dirs for visual review. It does not apply or validate — it only reads what's already on disk under `scripts/projects*/`.

Select exactly one of:

| Parameter | Example | Behaviour |
|---|---|---|
| `-Config <name>` | `-Config claude-code-l3` | Open one sandbox by exact leaf name (case-insensitive). |
| `-Pattern <wildcard>` | `-Pattern "*ui*-l4"` | Open every sandbox whose leaf name matches the PowerShell wildcard. |
| `-All` | `-All` | Open every sandbox under every `projects*` directory. |

Then pick a viewer with `-Editor`:

| Mode | Effect |
|---|---|
| `explorer` (default) | `Invoke-Item` — one Windows Explorer window per dir. |
| `code` | Launches each dir in VS Code via the `code` CLI (must be on PATH). |
| `tree` | Prints a recursive `Get-ChildItem -Force` listing with file sizes to stdout. Safe to redirect with `>`. |

Examples:

```powershell
.\scripts\smoke-inspect.ps1 -Config claude-code-l3
.\scripts\smoke-inspect.ps1 -Pattern "*ui*-l4" -Editor code
.\scripts\smoke-inspect.ps1 -All -Editor tree > tmp\baseline.txt
.\scripts\smoke-inspect.ps1 -Pattern "codex-*" -Editor tree -SandboxRoot c:\users\marty\source\sandbox\govkit-test
```

Tree mode writes through the success stream, so it is the right choice when you want to snapshot every sandbox to a file (e.g. the pre-refactor baseline in Increment 0c of the project-shape refactor plan).

## Troubleshooting

**"govkit version: 0.7.0" but I just edited the repo and don't see my changes.**
The venv has a cached editable install. Delete `scripts/.venv/` and re-run — the script will recreate the venv against the current repo state.

**`python` not on PATH.**
The script uses whatever `python` resolves to in your shell. Either add Python 3.11+ to PATH or modify the script's `python -m venv $venvDir` line to use an absolute path.

**Pre-commit warnings about `.venv/` or sandbox dirs being tracked.**
They shouldn't be — the `.gitignore` covers them. If they show up in `git status`, verify the `.gitignore` entries are present and that no parent `.gitignore` has un-ignored them.

## Related plans

- [plans/PROJECT_SHAPE_REFACTOR_PLAN.md](../plans/PROJECT_SHAPE_REFACTOR_PLAN.md) — these scripts are baseline tooling for the v0.8.0 refactor. Increment 0b adds a visual-inspection helper (`smoke-inspect.ps1`). Increment 11 rewrites the apply invocations (drops `--ui`, splits backend/UI by `--type`).
