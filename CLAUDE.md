# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is (read this first)

This repo is the **source for `govkit`**, a Python CLI that installs governance artifacts into *other people's* projects. It is **not** a govkit-governed project itself — there is no `features/` workflow, no `/govkit-*` skills, and no `.govkit/` marker governing development here.

That distinction drives everything. The tree splits into two kinds of content:

- **The installer** — `cli/*.py`. Real Python source. This is the code you test and lint.
- **The payload** — `agents/`, `docs/`, `governance/`, `ci/`, `features/`, `extensions/`. Markdown specs, YAML configs, Gherkin, and JSON schemas that `govkit apply` copies into a target project. Editing these changes what *users* receive, not how the CLI behaves.

When a task says "fix the API conventions" or "update the spec-planning skill," you are almost always editing **payload**, not the installer. When it says "apply is writing the wrong marker" or "doctor crashes," you are editing the **installer**.

## Commands

```bash
pip install -e ".[test]"      # dev install (extra is [test]; CONTRIBUTING.md's ".[dev]" is stale — [dev] doesn't exist)
pytest                        # full suite (~765 tests across tests/)
pytest tests/test_doctor.py                          # one file
pytest tests/test_doctor.py::TestRunDoctor           # one class
pytest -k parity                                     # by keyword (parity checks span several files)
ruff check cli/ && ruff format cli/   # lint + format (fix=true is on; scope to changed files, never a dir-wide run)
govkit list                   # smoke-run the CLI after an editable install
```

Ruff has `fix = true` in `pyproject.toml`, so `ruff check` **rewrites files**. Scope it to the files you changed rather than the whole tree, or it will reformat unrelated code into your diff.

### Local end-to-end smoke (PowerShell, Windows)

```powershell
.\scripts\smoke.ps1 -Agents claude-code -Levels 4 -Force   # apply+validate across agent×type×level
```

Bootstraps its own `scripts/.venv/` (gitignored) and writes sandboxes under `scripts/projects*/`. See [scripts/README.md](scripts/README.md). L4/L5 `validate` is **expected to fail** in these sandboxes — the starter features intentionally omit `plan.md` / `architecture_preflight.md`.

## Installer architecture (`cli/`)

The CLI is deliberately layered so command modules depend **inward** only, avoiding import cycles:

- **`paths.py` — the dependency-free kernel.** Every module resolves bundled-asset locations (`AGENTS_DIR`, `EXTENSION_PACKS_DIR`, `REPO_ROOT`) through it. It imports nothing internal. **Reference attributes at call time (`paths.AGENTS_DIR`), never `from .paths import AGENTS_DIR`** — tests monkeypatch these attributes to point govkit at a fake bundle, and a copied binding won't see the patch.
- **`govkit.py` — dispatch only.** Each subcommand lives in its own `cmd_*.py` (or `doctor.py`/`calibrate.py`) module exposing a `register(subparsers)` that binds its handler via `set_defaults(func=...)`. Adding a command = new module + append to `_REGISTRARS`.
- **Domain modules** — `manifest.py` (variant resolution), `marker.py` (`.govkit/` read/write), `stack_select.py`/`overlay.py` (stack overlays), `detect.py` (repo inference), `headers.py` (edit-protection markers), `install_common.py` (copy loop shared by apply + upgrade), `extensions.py` (extension-pack discovery).

### Two behaviors that recur across the codebase

**Bundled-asset path resolution (dev vs. wheel).** In an editable install, assets are read from the repo root (`agents/`, `extensions/`). In the built wheel, `pyproject.toml`'s `force-include` remaps them under the `cli/` package (`agents/`→`cli/agents/`, `extensions/`→`cli/extension_packs/`, etc.). `paths.py` has the `if (_HERE / "agents").exists() else _HERE.parent / "agents"` fallback for exactly this. **Consequence:** editable-install tests can pass while the wheel is broken (missing force-include). The `wheel-smoke` job in `.github/workflows/test.yml` builds a real wheel and installs into a clean venv to catch this — mirror it if you touch packaging or add a new bundled asset dir. Note `extensions/` ships to `cli/extension_packs/`, **not** `cli/extensions/` — the latter name is the discovery *module* `cli/extensions.py`.

**File categories + edit-protection.** `apply`/`upgrade` treat installed files in three categories with different overwrite rules: **agent config** (govkit-owned namespace — always overwritten), **governed contracts** (write-once on apply, overwritten on upgrade), and **project artifacts** (never overwritten once present). User edits to governed docs are detected by content: the `<!-- govkit:editable -->` header (`headers.py`) records a SHA-256 of the installed body, and a differing body hash means user-edited (headers without a `hash:` field — pre-hash installs — fall back to file mtime vs. the marker's `applied_at`); `--force` overrides. govkit **never** writes or touches a file the user authored.

## Payload architecture

### Three agents, enforced parity

The payload ships for three agents — `agents/{claude-code,codex,copilot}/` — that install to different locations (`.claude/`, `AGENTS.md`+`.agents/`, `.github/`) but must stay behaviorally identical. **The test suite enforces parity.** In particular, a skill's `SKILL.md` frontmatter (`name:`, `description:`) must be **byte-identical** across all three agents. When you add or change a skill, rule, or governance doc, **change it for all three agents in lockstep** and run the parity tests (`pytest -k parity`, plus `tests/test_agent_skills.py`, `tests/test_govkit.py`). Do not claim a per-agent gap without diffing the three inventories first — they are meant to match.

Skills follow the **Open Skills** standard: frontmatter is `name`+`description` only (no `argument-hint:`, no `user-invocable:`, no `$ARGUMENTS`). Feature names are derived from natural language. Skills install with a `govkit-` prefix (`.claude/skills/govkit-spec-planning/`) so they never collide with a user's own skills.

### Variant manifests

Each agent's `manifest.json` declares install sets as **variants** keyed by options (`level` ∈ {3,4,5}, `type` ∈ {api,cli,ui-react,ui-angular,data}, `ci` ∈ {github,azure}). `manifest.py` merges/replaces variant declarations (`by_type`, `by_stack`) into a concrete `(files, shared, governed)` list. A flat `files` format is retained for legacy/custom agents (`_apply_legacy_install`). The chosen options are recorded in the target's `.govkit/marker.json` so later commands (`calibrate`, `doctor`, `validate`, `upgrade`) need no re-specification.

### Maturity levels are additive

L3 ⊂ L4 ⊂ L5. **L3** = agent rules + architecture contracts, no `features/` dir (`govkit init` errors, `validate` no-ops). **L4** adds the `features/<name>/` 5-artifact contract and FIRST/7-Virtue prediction (avg ≥ 4.0). **L5** adds GenAI-ops contracts via `extensions/`. Only the governance file is re-issued per level; lower-level files are never replaced by higher levels.

### Stack overlays

Only 6 architecture docs vary per backend/data stack (`TECH_STACK.md`, `API_CONVENTIONS.md`, `TESTING.md`, `LAYER_IMPLEMENTATION.md`, `SECURITY_AUTH_PATTERNS.md`, `OBSERVABILITY_PORT_CONTRACT.md`). They live in `cli/stacks/<id>/` with an `overlay.yaml`. Everything else in `docs/` is stack-agnostic baseline. `govkit stack apply <id>` swaps overlays post-install, respecting edit-protection.

## When changing behavior, keep the payload internally consistent

A change is rarely one file. Changing a schema means updating starter templates and worked examples that must still validate against it. Changing a CI gate template means updating both `ci/github/` and `ci/azure/` and `ci/README.md`. Changing an architecture doc that agents read means reflecting it in the affected skills/rules. Tests assert this cross-consistency (`tests/test_schemas.py`, `tests/test_fixtures.py`, the per-extension tests). The commit convention is `type(scope): description` with types `feat|fix|docs|test|refactor|chore`.
