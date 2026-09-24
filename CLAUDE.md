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
./run_tests                   # fast loop (~20s) = pytest -m "not e2e"; use during development
./full_test                   # fast loop, then the e2e tier — same coverage as CI's plain `pytest`
pytest                        # full suite (~1200 tests across tests/; what CI runs)
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

## Delivery review

Before creating a PR, run Qodo local review using `qodo-review` with self-contained session context and issue/spec references. Evaluate findings and fix verified bugs test first; record the actual result. Do not silently skip a blocked review or claim it completed. For an existing PR, use `qodo-review-resolver` to inspect and remediate its structured findings. Keep the implementation plan and issue status current, then follow the user's standing commit/push/PR instruction. Merging requires separate authorization.

## Installer architecture (`cli/`)

The CLI is deliberately layered so command modules depend **inward** only, avoiding import cycles:

- **`paths.py` — the dependency-free kernel.** Every module resolves bundled-asset locations (`AGENTS_DIR`, `EXTENSION_PACKS_DIR`, `REPO_ROOT`) through it. It imports nothing internal. **Reference attributes at call time (`paths.AGENTS_DIR`), never `from .paths import AGENTS_DIR`** — tests monkeypatch these attributes to point govkit at a fake bundle, and a copied binding won't see the patch.
- **`govkit.py` — dispatch only.** Each subcommand lives in its own `cmd_*.py` (or `doctor.py`/`calibrate.py`) module exposing a `register(subparsers)` that binds its handler via `set_defaults(func=...)`. Adding a command = new module + append to `_REGISTRARS`.
- **Domain modules** — `manifest.py` (loading, prompts, and compatibility selection facade), `legacy_resolution.py` (legacy levels and ordered manifest selection), `resolution.py` / `resolution_models.py` (pure explicit-requirement resolution and typed plans), `marker.py` (`.govkit/` read/write), `stack_select.py`/`overlay.py` (stack overlays), `detect.py` (repo inference), `headers.py` (edit-protection markers), `install_common.py` (copy loop shared by apply + upgrade), `extensions.py` (extension-pack discovery).

The resolution foundation is described in [ADR 0001](plans/decisions/0001-resolution-boundaries.md). `resolution.py` accepts explicit typed inputs and returns versioned plans; it performs no filesystem access, network access, printing, or process exits. Keep level interpretation in the legacy boundary. A selected resource/check or a plan's `ready` property is not approval to overwrite a file or evidence that a control ran.

`profiles.py` validates versioned desired profiles and replayable resolution records using bundled JSON Schemas and typed inputs. `profile_store.py` previews/applies only the two profile metadata files, preserving project-owned content and the legacy marker. `cmd_profile.py` exposes the dedicated preview/apply commands. [ADR 0002](plans/decisions/0002-profile-materialization.md) and the [profile guide](docs/DECLARATIVE_PROFILES.md) describe authority, ownership and runtime dependency choices. Request routing and release assessment remain later increments. When changing a profile schema, keep the embedded resolution-schema definitions and every paired example aligned; tests enforce this parity and runtime replay.

### Two behaviors that recur across the codebase

**Bundled-asset path resolution (dev vs. wheel).** In an editable install, assets are read from the repo root (`agents/`, `extensions/`). In the built wheel, `pyproject.toml`'s `force-include` remaps them under the `cli/` package (`agents/`→`cli/agents/`, `extensions/`→`cli/extension_packs/`, etc.). `paths.py` has the `if (_HERE / "agents").exists() else _HERE.parent / "agents"` fallback for exactly this. **Consequence:** editable-install tests can pass while the wheel is broken (missing force-include). The `wheel-smoke` job in `.github/workflows/test.yml` builds a real wheel and installs into a clean venv to catch this — mirror it if you touch packaging or add a new bundled asset dir. Note `extensions/` ships to `cli/extension_packs/`, **not** `cli/extensions/` — the latter name is the discovery *module* `cli/extensions.py`.

**File categories + edit-protection.** `apply`/`upgrade` treat installed files in three categories with different overwrite rules: **agent config** (govkit-owned namespace — always overwritten), **governed contracts** (write-once on apply, overwritten on upgrade), and **project artifacts** (never overwritten once present). User edits to governed docs are detected by content: the `<!-- govkit:editable -->` header (`headers.py`) records a SHA-256 of the installed body, and a differing body hash means user-edited (headers without a `hash:` field — pre-hash installs — fall back to file mtime vs. the marker's `applied_at`); `--force` overrides. govkit **never** writes or touches a file the user authored.

## Payload architecture

### Three agents, enforced parity

The payload ships for three agents — `agents/{claude-code,codex,copilot}/` — that install to different locations (`.claude/`, `AGENTS.md`+`.agents/`, `.github/`) but must stay behaviorally identical. **The test suite enforces parity.** In particular, a skill's `SKILL.md` frontmatter (`name:`, `description:`) must be **byte-identical** across all three agents. When you add or change a skill, rule, or governance doc, **change it for all three agents in lockstep** and run the parity tests (`pytest -k parity`, plus `tests/test_agent_skills.py`, `tests/test_govkit.py`). Do not claim a per-agent gap without diffing the three inventories first — they are meant to match.

Skills follow the **Open Skills** standard: frontmatter is `name`+`description` only (no `argument-hint:`, no `user-invocable:`, no `$ARGUMENTS`). Feature names are derived from natural language. Skills install with a `govkit-` prefix (`.claude/skills/govkit-spec-planning/`) so they never collide with a user's own skills.

### Variant manifests

Each agent's `manifest.json` declares install sets as **variants** keyed by options (`level` ∈ {3,4,5}, `type` ∈ {api,cli,ui-react,ui-angular,ui-nextjs,data}, `ci` ∈ {github,azure}). `manifest.py` expands the bundled `ci_catalog` reference from `governance/ci/legacy-selection.json`, then merges/replaces variant declarations (`by_type`, `by_stack`) into a concrete `(files, shared, governed)` list. Keep shared CI dispatch in that table; custom inline `variants.ci` manifests remain supported. Never combine inline CI and a shared reference. A flat `files` format is retained for legacy/custom agents (`_apply_legacy_install`). The chosen options are recorded in the target's `.govkit/marker.json` so later commands (`calibrate`, `doctor`, `validate`, `upgrade`) need no re-specification.

### Maturity levels are additive

L3 ⊂ L4 ⊂ L5. **L3** = agent rules + architecture contracts, no `features/` dir (`govkit init` errors, `validate` no-ops). **L4** adds five common feature artifacts; UI types require `design.md` as a sixth. **L5** adds GenAI-ops contracts via `extensions/`. Only the governance file is re-issued per level; lower-level files are never replaced by higher levels.

### Stack overlays

Only 6 architecture docs vary per backend/data stack (`TECH_STACK.md`, `API_CONVENTIONS.md`, `TESTING.md`, `LAYER_IMPLEMENTATION.md`, `SECURITY_AUTH_PATTERNS.md`, `OBSERVABILITY_PORT_CONTRACT.md`). They live in `cli/stacks/<id>/` with an `overlay.yaml`. Everything else in `docs/` is stack-agnostic baseline. `govkit stack apply <id>` swaps overlays post-install, respecting edit-protection.

UI project types are standalone and reject both `--stack` and
`govkit stack apply`. `ui-nextjs` uses its own server-first API-first payload;
direct SQL/database dependencies are a non-waivable boundary enforced by
doctor D016. The `nextjs/` docs folder is intentionally larger than `react/`
and `angular/` — its extra docs are server-first concerns with no SPA
equivalent. Do not replicate them for parity; see
`docs/ui/architecture/README.md`.

## When changing behavior, keep the payload internally consistent

A change is rarely one file. Changing a schema means updating starter templates and worked examples that must still validate against it. Changing a CI gate template means updating both `ci/github/` and `ci/azure/` and `ci/README.md`. Changing an architecture doc that agents read means reflecting it in the affected skills/rules. Tests assert this cross-consistency (`tests/test_schemas.py`, `tests/test_fixtures.py`, the per-extension tests). The commit convention is `type(scope): description` with types `feat|fix|docs|test|refactor|chore`.

### Declarative packs

`govkit profile` saves metadata; `govkit pack` separately resolves and installs pinned resources and native skills without a legacy marker. See `docs/CAPABILITY_PACKS.md` and ADR 0003. Keep the strict manifest/profile/lock schemas synchronized, and verify payload resources from a clean wheel. Agent-neutral pack skill sources live under `extensions/`; do not create three divergent copies. Pack resources, examples and detection are not accepted project policy.

### Check and evidence foundation

`cmd_conform.py` renders the report assembled by `conformance.py` through typed models, an explicit registry/runner and legacy/pack adapters. See [ADR 0004](plans/decisions/0004-check-evidence-foundation.md) and [check reports](docs/CONFORMANCE.md). Required unknown/skipped/unconfigured evidence cannot pass; a validated result file does not authenticate its origin. Keep runtime schemas and examples aligned. Default inspection is offline and read-only: never use the migrating legacy marker reader in this path. Preserve the legacy commands' behavior through injected external boundaries. Pack execution requires explicit opt-in and is not sandboxed. Actual-diff routing and maintenance are later increments.

### Brownfield discovery

`cmd_discover.py` renders bounded read-only observations from `discovery_scan.py` and decisions/previews from `discovery.py`. See [ADR 0005](plans/decisions/0005-brownfield-discovery.md) and [discovery](docs/BROWNFIELD_DISCOVERY.md). Observed docs/imports are not accepted policy; only explicit accepted profiles feed existing protected installers. Baselines are explicit caller-reviewed records, never written/accepted automatically. Incomplete/changed coverage cannot prove removal. Keep report schema, four bundled example repositories and runtime-only wheel smoke aligned. `maintenance_outcome()` uses I04's facts contract; actual diff/transition enforcement and integrated maintenance remain I07/I09.

### Request workflow planning

`cmd_request.py` prints proposed templates and per-request plans. `workflows.py` resolves only validated snapshots; `workflow_store.py` owns bounded local reads and deterministic replay. See [ADR 0006](plans/decisions/0006-request-workflows.md) and [request workflows](docs/REQUEST_WORKFLOWS.md). Preserve additive policy/check requirements, existing defect eligibility, independent LLM evaluation and verified pinned guidance. Agent normalization stays outside the deterministic boundary. Planning readiness is not approval or conformance. Supplied scope observations do not replace I07 actual-diff enforcement. Keep schemas, seven examples and runtime-only wheel smoke aligned.

### Actual-change conformance

`change_scope.py` captures bounded Git observations; `change_policy.py` reads accepted provider configuration; `change_architecture.py` measures scoped literal constraints; `change_defects.py` adapts existing eligibility/red-green execution. `change_conformance.py` recomputes request requirements and composes I04 checks. See ADR 0007 and `docs/CHANGE_CONFORMANCE.md`. Keep accepted policy outside the inspected tree, commands explicitly opted in, missing semantic/platform evidence unknown, and synthetic seven-pilot wheel coverage aligned. Legacy migration and consolidated maintenance remain I08/I09.

### Safe legacy migration

`migration.py` composes existing legacy/profile/pack/discovery/check boundaries in an isolated preview; `migration_store.py` owns bounded snapshots and reversible writes. See ADR 0008 and `docs/LEGACY_MIGRATION.md`. Default preview is read-only. Apply requires an explicitly accepted profile and exact preview digest; preserve configured obligations, user bytes/modes/mtimes, flat-marker content and opt-in authority. Rollback derives ownership from the verified lock and refuses edited resources. Metadata installation never establishes enforcement parity. Keep real legacy-install and runtime-only wheel pilots aligned. Canonical maintenance now feeds preview and post-operation verification; actual legacy removal remains I13.

### Maintenance version facts

`release_metadata.py` owns approved metadata, freshness and policy/runtime candidate selection; `maintenance_inventory.py` observes actual resource digests and composes protected previews through the existing pack store. `cmd_maintain.py` alone owns explicit cache output outside the target. See ADR 0009 and `docs/MAINTENANCE_INVENTORY.md`. Keep inventory/preview offline, source refresh data-only and anonymous, customizations protected, unknown freshness explicit and source/lookup timestamps separate. Do not infer enforcement or newest-version certification from inventory.

### Canonical maintenance assessment

`maintenance_facts.py` composes inventory, discovery and canonical CI check outcomes into four independent dimensions; `maintenance.py` captures/replays their inputs and compares post-operation findings. `maintenance_operations.py` revalidates inputs and freshness before routing protected previews. See ADR 0010 and `docs/MAINTENANCE_ASSESSMENT.md`. Required status must trace to accepted policy, including on passing CI checks; unverified lock claims cannot invent mandatory resources or version failures. CI evidence must match complete Git/profile/lock identity, scope and accepted age. Missing providers remain unknown; I10 owns live collection and repair. Saved release inputs must replay the effective metadata and candidates. Migration rechecks release/CI freshness at the current clock while keeping still-valid approval digests stable, then reruns assessment after application at the current time; disappearance without a passing dimension under unchanged policy is unverified. Preserve existing write authorization, customization protection and rollback. Keep runtime-only three-agent assessment and migration pilots aligned.

### Maintenance posture projection

`posture.py` projects replayed canonical maintenance assessments through a strict export allowlist; `cmd_posture.py` renders or explicitly publishes the result through the existing artifact writer. See ADR 0014 and `docs/POSTURE_REPORTING.md`. Preserve canonical findings/actions and reuse check aggregation; do not inspect a target or derive new upgrade decisions during export. Free text, paths, URLs and custom identifiers become pseudonymous references, not authenticated evidence. Public version displays omit local labels; exact values remain referenced. Maintenance execution is not project-control execution, and export success is not a conformance pass. Keep strict schemas, the bundled example and runtime-only three-agent/both-provider pilot aligned. I11b retains change-specific posture, fleet aggregation and the voluntary pilot; no source consumer installation yet.

### Shared gate catalog

`gate_catalog.py` composes typed logical GateSpec declarations from explicit profiles and local pack snapshots; `cmd_pipeline.py` exposes read-only `pipeline catalog`. See ADR 0011 and `docs/GATE_CATALOG.md`. All declarations share one common conformance invocation with trusted request/base/policy inputs. Preserve additive requirements and literal scopes; do not use the catalog as a runtime allowlist or introduce path filters that bypass conformance. Version pins and catalog readiness are composition facts, not execution/enforcement or publisher authentication. `gate_legacy.py` expands only the named bounded bundled legacy table at the loading boundary; the legacy adapter stays pure and all 258 frozen selections remain unchanged. Keep all three manifest references, runtime schema, examples and installed-wheel pilot aligned. I10b owns pinned reusable provider entry points and protected generation; I10c retains provider authority and maintenance/provider evidence.

### Protected provider generation

`pipeline_render.py` emits paired reusable entry points; `pipeline_store.py` binds exact preview authorization and protects existing files; `pipeline_runtime.py` verifies runtime/profile/pack pins, including the lock-recorded resolver version, before the common engine. See ADR 0012 and `docs/PIPELINE_GENERATION.md`. Templates require caller-prepared isolated runtime, trusted policy checkout, request and full base SHA. Keep provider inputs in environment values, absolute interpreter validation and Python isolation. `pipeline_files.py` binds all generation writes, rollback and cleanup to no-follow directory handles; unsupported platforms fail before writes. Preserve edit protection, stale-input guards and explicit execution opt-ins. The common engine validates pipeline-wide opt-ins before filtering by actual request requirements; mandatory controls remain intact and local explicit selections stay strict. Configuration currency cannot imply activation/execution/enforcement. I10c retains provider event/admission, maintenance facts and publication; generation must not fetch/install packages or rewrite existing workflows. Keep paired goldens, schemas and three-agent installed-wheel execution pilots aligned.


### Provider admission and evidence

`provider_admission.py` validates caller-supplied native PR context and clean pinned checkouts before runtime execution. `pipeline_evidence.py` compares explicit provider/change exports and generated configuration, producing canonical CI checks for the existing maintenance engine. `pipeline_assessment.py` composes protected candidate integration previews; `artifact_publication.py` creates only explicitly requested new artifacts outside inspected checkouts. See ADR 0013 and `docs/PROVIDER_EVIDENCE.md`. Preserve unknown facts, original evidence age, ignored generated-file identity and accepted request byte snapshots. Provider exports retain unverified-artifact provenance; imported success claims remain unknown and explicit failures survive unrelated report mismatches. They are not authenticated live collection; credentials, branch/reviewer policy and activation stay with protected callers. Keep both providers' schemas/examples, optional publication snippets and runtime-only wheel pilots aligned.
