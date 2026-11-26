# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is (read this first)

This repo is the **source for `govkit`**, a Python CLI that installs governance artifacts into *other people's* projects. It now demonstrates limited self-hosting through the explicit `.govkit/profile.yaml`, source policy, generated resolution and empty pack lock. It selects no consumer packs or agent skills, has no legacy marker, and does not use the consumer `features/` workflow. Follow [source self-hosting](plans/SOURCE_SELF_HOSTING.md); do not run blanket `govkit apply` here.

The installer/payload distinction still governs development. The tree splits into two kinds of product content:

- **The installer** — `cli/*.py`. Real Python source. This is the code you test and lint.
- **The payload** — `agents/`, `docs/`, `governance/`, `ci/`, `features/`, `extensions/`. Markdown specs, YAML configs, Gherkin, and JSON schemas that `govkit apply` copies into a target project. Editing these changes what *users* receive, not how the CLI behaves.

`.govkit/`, `plans/` and the source Tests workflow are source-specific configuration/guidance. Local self-hosting executes a bounded profile-test suite and source pipeline contract through canonical conformance; protected-caller and semantic architecture evidence remain unknown. Select a separately reviewed policy snapshot, request and base explicitly. The recurring maintenance request must not relabel arbitrary implementation work as low impact. Keep test-first development and the full delivery checks below.

When a task says "fix the API conventions" or "update the spec-planning skill," you are almost always editing **payload**, not the installer. When it says "apply is writing the wrong marker" or "doctor crashes," you are editing the **installer**.

## Commands

```bash
pip install -e ".[test]"      # development install with test dependencies
./run_tests                   # fast tier = pytest -m "not e2e"; takes several minutes
./full_test                   # fast loop, then the e2e tier — same coverage as CI's plain `pytest`
pytest                        # full suite, including tests requiring external toolchains
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

Bootstraps its own `scripts/.venv/` (gitignored) and writes sandboxes under `scripts/projects*/`. See [scripts/README.md](scripts/README.md). L4/L5 `validate` is **expected to fail** in these sandboxes — the script writes its own `hello_world_api` feature with only the three spec inputs, omitting `plan.md` / `architecture_preflight.md`. `govkit init` starters ship both files.

## Delivery review

CodeRabbit reviews each PR. Evaluate its findings, including outside-diff findings in review bodies, and fix verified bugs test first; reply on the PR with the actual result or the reason for declining. Do not claim a review completed that did not run. Keep the implementation plan and issue status current, then follow the user's standing commit/push/PR instruction. Merging requires separate authorization.

## Installer architecture (`cli/`)

The CLI is deliberately layered so command modules depend **inward** only, avoiding import cycles:

- **`paths.py` — the dependency-free kernel.** Every module resolves bundled-asset locations (`AGENTS_DIR`, `EXTENSION_PACKS_DIR`, `REPO_ROOT`) through it. It imports nothing internal. **Reference attributes at call time (`paths.AGENTS_DIR`), never `from .paths import AGENTS_DIR`** — tests monkeypatch these attributes to point govkit at a fake bundle, and a copied binding won't see the patch.
- **`govkit.py` — dispatch only.** Each subcommand lives in its own `cmd_*.py` (or `doctor.py`/`calibrate.py`) module exposing a `register(subparsers)` that binds its handler via `set_defaults(func=...)`. Adding a command = new module + append to `_REGISTRARS`.
- **Domain modules** — `manifest.py` (loading, prompts, and compatibility selection facade), `legacy_resolution.py` (legacy levels and ordered manifest selection), `resolution.py` / `resolution_models.py` (pure explicit-requirement resolution and typed plans), `marker.py` (`.govkit/` read/write), `stack_select.py`/`overlay.py` (stack overlays), `detect.py` (repo inference), `headers.py` (edit-protection markers), `install_common.py` (copy loop shared by apply + upgrade), `extensions.py` (extension-pack discovery), `extension_inventory.py` (read-only view of installed legacy and lock-verified declarative extensions, with conflicting copies; backs `extension list --installed` and skill-context extension facts).

The resolution foundation is described in [ADR 0001](plans/decisions/0001-resolution-boundaries.md). `resolution.py` accepts explicit typed inputs and returns versioned plans; it performs no filesystem access, network access, printing, or process exits. Keep level interpretation in the legacy boundary. A selected resource/check or a plan's `ready` property is not approval to overwrite a file or evidence that a control ran.

`profiles.py` validates versioned desired profiles and replayable resolution records using bundled JSON Schemas and typed inputs. `profile_store.py` previews/applies only the two profile metadata files, preserving project-owned content and the legacy marker. `cmd_profile.py` exposes the dedicated preview/apply commands. [ADR 0002](plans/decisions/0002-profile-materialization.md) and the [profile guide](docs/DECLARATIVE_PROFILES.md) describe authority, ownership and runtime dependency choices. Request routing lives in `workflows.py`; release/maintenance assessment lives in `release_metadata.py` and `maintenance.py`. When changing a profile schema, keep the embedded resolution-schema definitions and every paired example aligned; tests enforce this parity and runtime replay.

### Two behaviors that recur across the codebase

**Bundled-asset path resolution (dev vs. wheel).** In an editable install, assets are read from the repo root (`agents/`, `extensions/`). In the built wheel, `pyproject.toml`'s `force-include` remaps them under the `cli/` package (`agents/`→`cli/agents/`, `extensions/`→`cli/ext/`, etc.). `paths.py` has the `if (_HERE / "agents").exists() else _HERE.parent / "agents"` fallback for exactly this. **Consequence:** editable-install tests can pass while the wheel is broken (missing force-include). The `wheel-smoke` job in `.github/workflows/test.yml` builds a real wheel and installs into a clean venv to catch this — mirror it if you touch packaging or add a new bundled asset dir. The compact `cli/ext/` asset root preserves the Windows wheel path budget; `extensions/` ships there, **not** `cli/extensions/` — the latter name is the discovery *module* `cli/extensions.py`.

**File categories + edit-protection.** `apply`/`upgrade` treat installed files in three categories with different overwrite rules: **agent config** (govkit-owned namespace — always overwritten), **governed contracts** (write-once on apply, overwritten on upgrade), and **project artifacts** (never overwritten once present). User edits to governed docs are detected by content: the `<!-- govkit:editable -->` header (`headers.py`) records a SHA-256 of the installed body, and a differing body hash means user-edited (headers without a `hash:` field — pre-hash installs — fall back to file mtime vs. the marker's `applied_at`); `--force` overrides. govkit **never** writes or touches a file the user authored.

## Payload architecture

### Three agents, enforced parity

The payload ships for three agents — `agents/{claude-code,codex,copilot}/` — that install to different locations (`.claude/`, `AGENTS.md`+`.agents/`, `.github/`) but must stay behaviorally identical. **The test suite enforces parity.** In particular, a skill's `SKILL.md` frontmatter (`name:`, `description:`) must be **byte-identical** across all three agents. When you add or change a skill, rule, or governance doc, **change it for all three agents in lockstep** and run the parity tests (`pytest -k parity`, plus `tests/test_agent_skills.py`, `tests/test_govkit.py`). Do not claim a per-agent gap without diffing the three inventories first — they are meant to match.

Skills follow the **Open Skills** standard: frontmatter is `name`+`description` only (no `argument-hint:`, no `user-invocable:`, no `$ARGUMENTS`). Feature names are derived from natural language. Skills install with a `govkit-` prefix (`.claude/skills/govkit-spec-planning/`) so they never collide with a user's own skills.

For GovKit-owned skills, keep the source folder basename, `SKILL.md` frontmatter `name`, and manifest installation basename identical (including `govkit-` and any `ui-` qualifier). Preserve native installation paths when reorganizing sources. Vendored upstream skills have a separate provenance/sync contract; do not silently rewrite them as part of first-party payload maintenance.

Native vendored skills may map an explicit upstream `agents/openai.yaml` policy into agent-specific metadata: boolean `allow_implicit_invocation: false` adds `disable-model-invocation: true` for Claude/Copilot, while Codex consumes the sidecar. This is a deliberate exception to the first-party frontmatter restriction. Preserve raw source/pinned bytes, alias native default prompts and keep historical renderer versions replayable; see `docs/CAPABILITY_PACKS.md`.

Shared first-party skill bodies can select installed-type prose with flat, whole-line `<!-- govkit:docs-area data -->` / `<!-- /govkit:docs-area -->` sections (`backend`, `data`, or `ui`). `skill_templating.py` selects the known docs area before expanding path tokens; missing/unknown context leaves sections visible. Do not nest sections. Apply/upgrade recopy the bundled source before rendering. Keep all three agent sources aligned and exercise real installs plus the installed-wheel instruction tests.

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

`cmd_conform.py` renders the report assembled by `conformance.py` through typed models, an explicit registry/runner and legacy/pack adapters. See [ADR 0004](plans/decisions/0004-check-evidence-foundation.md) and [check reports](docs/CONFORMANCE.md). Required unknown/skipped/unconfigured evidence cannot pass; a validated result file does not authenticate its origin. Keep runtime schemas and examples aligned. Default inspection is offline and read-only: never use the migrating legacy marker reader in this path. Preserve the legacy commands' behavior through injected external boundaries. Pack execution requires explicit opt-in and is not sandboxed. Actual-diff routing is composed by `change_conformance.py`; `maintenance.py` reuses the canonical check/evidence contract.

### Brownfield discovery

`cmd_discover.py` renders bounded read-only observations from `discovery_scan.py` and decisions/previews from `discovery.py`. See [ADR 0005](plans/decisions/0005-brownfield-discovery.md) and [discovery](docs/BROWNFIELD_DISCOVERY.md). Observed docs/imports are not accepted policy; only explicit accepted profiles feed existing protected installers. Baselines are explicit caller-reviewed records, never written/accepted automatically. Incomplete/changed coverage cannot prove removal. Keep report schema, four bundled example repositories and runtime-only wheel smoke aligned. `maintenance_outcome()` uses I04's facts contract; actual-change conformance and canonical maintenance consume these observations without promoting them to accepted policy.

### Request workflow planning

`cmd_request.py` prints proposed templates and per-request plans. `workflows.py` resolves only validated snapshots; `workflow_store.py` owns bounded local reads and deterministic replay. See [ADR 0006](plans/decisions/0006-request-workflows.md) and [request workflows](docs/REQUEST_WORKFLOWS.md). Preserve additive policy/check requirements, existing defect eligibility, independent LLM evaluation and verified pinned guidance. Agent normalization stays outside the deterministic boundary. Planning readiness is not approval or conformance. Supplied scope observations do not replace actual Git capture in `change_conformance.py`. Keep schemas, eight examples and runtime-only wheel smoke aligned. An `experiment` reference escalates defect/bounded work to full-feature and adds the `experiment-record` artifact; requests without one must replay unchanged (`tests/fixtures/request-replay-v1`).

### Architecture experiments

`experiments.py` assesses an optional per-feature `experiments.yaml` and the single `preflight_outcome` block in `architecture_preflight.md`. It is pure: callers supply parsed records, a digest reader and an optional clock. `experiment_store.py` owns bounded, contained, no-symlink reads, and returns `None` when a feature declares neither record. See ADR 0020 and `docs/ARCHITECTURE_EXPERIMENTS.md`.

- **What makes evidence stale.** A changed requirement, dependency or evidence file, edited criteria, re-pinned inputs or an expired result. A preflight relying on stale evidence is an error.
- **Rules that guard requirements.** `adopt` requires a pass. Narrowing behavior requires an accepted requirement change. The schema has no waiver field, and synthetic evidence never satisfies an application requirement.
- **What a clean assessment means.** The records are consistent and current. It is not execution or conformance.
- **Where it runs.** `govkit validate` reports experiment findings per feature, at any level; `--only experiments` runs just these checks. Errors FAIL. Outstanding or unknown findings WARN, or FAIL with `--strict`. Both `quality-gate.yml` templates run the non-strict `--only experiments` check when a non-starter feature declares either record. Every feature install ships both schemas.
- **Agent guidance.** The backend, CLI and data preflight, GenAI preflight, spec-planning and implementation-plan skills, the generic spec-compliance rule, the entry instructions, both preflight and plan templates, and the backend, CLI and data starters carry the loop, identically for all three agents. Starters ship `status: blocked` with the reason "Preflight not yet completed." UI payload is a later increment.
- **Request and change wiring.** An `experiment` request reference routes work to full-feature; `change_conformance.py` assesses the referenced records through `experiment_store` (errors FAIL, outstanding/unknown UNKNOWN) and honors a declared preflight outcome. It never executes experiments.
- **Keep aligned.** The schemas and the six example scenarios, together with their expected results. `tests/wheel_experiment_smoke.py` runs the loop (acceptance scenarios S1–S6) from a clean wheel for all three agents on the legacy and declarative routes.

### Feature-scoped validate and known failures

`validate_scope.py` runs the same checks as `validate.run_validation` for a `--feature` selection and classifies failures against a `--known-failures` record; `known_failures.py` owns the bounded record read, schema validation, digest and rendering. See ADR 0021 and `docs/KNOWN_FAILURES.md`.

- **No options, no change.** `cmd_validate.py` calls the legacy runner unless one of the four options is given. Keep that path byte-identical; identifiers and the new summary line belong to the scoped path only.
- **Identity.** Scope kind and name, check identifier, optional finding code. Never message text. Check identifiers (`FEATURE_CHECK_IDS`, `CHECKS_BY_SCOPE`) are a public contract: add, never rename. `_named_checks` is the single source for both runners and for `check_adapters`.
- **Authority.** GovKit never writes or accepts a record. An unusable record stops the run and is never read as empty. A valid record or a matching digest is not evidence of review.
- **Resolved versus ignored.** Only an entry whose check was evaluated for its scope and is no longer failing or warning is resolved. Entries outside the selection are ignored.
- **Keep aligned.** The schema, the bundled example, `tests/test_validate_scope.py` and `tests/wheel_validate_smoke.py` (all three agents). `govkit conform` keeps positional feature codes until #253. Payload skills, rules and CI templates do not use these options yet.

### Feature evidence report

`evidence_report.py` builds the canonical report for `govkit evidence --feature`: each scenario in a feature's `acceptance.feature` bound to JUnit test results, and each criterion in its `eval_criteria.yaml` compared with a measured score. `scenario_identity.py` supplies identifiers and revision digests; `evidence.py` reads test cases. See ADRs 0022 to 0024 and `docs/EVIDENCE_REPORT.md`.

- **Mirrored identity.** `scenario_identity.py` copies the `discovery-engine` reader and the `aipos-plugins` slug rule. Do not make it more forgiving or more correct than its sources: its digests must equal the graph's. Refresh `tests/fixtures/scenario-identity/` by running the engine's reader, never by editing expected values.
- **Binding.** A `govkit.scenario` property (`id`, then `tag`), then the reduced title. A test that carries the property is never matched by title. Only `id` is exact across features.
- **Outcome.** `PASS` only when every scenario passed. Missing, skipped and unmarked skips are `INCONCLUSIVE`. Exit 0 only on `PASS`; 2 is a bad invocation.
- **No feature option, no change.** Without `--feature` the command and its output are unchanged. Feature mode reads no marker and writes nothing.
- **Public contract.** Requirement identifiers, states, binding names, refusal reasons and exit codes: add, never rename.
- **Criteria.** `criterion_identity.py` mirrors the engine's criterion identity, target reading and comparison, pinned by `criteria_parity.json`. `evaluation_results.py` reads `govkit-eval-results*.json`, bounded and without following links; an unusable file is an error, never an empty result. See ADR 0023.
- **Classes.** `execution_class` is `free`, `paid` or `human`. With no result, free is `missing` and the others are `owed`. An unknown class is an error, not `free`. GovKit never starts an evaluation.
- **Backend form only.** `target` and `execution_class` exist only in the backend `eval_criteria` schema. Data-form criteria are not compared and prevent `PASS`; UI files have none. Do not add the fields to the other two schemas without a criterion they apply to.
- **Freshness.** `evidence_record.py` writes and checks `govkit-evidence-record.json`; `tree_identity.py` identifies the working tree through Git. Results count only when the record's commit, tree digest and result-file digests still hold; otherwise the feature is `INCONCLUSIVE` and the result states stay visible. See ADR 0024.
  - `--record` is the only option that writes, and it is its own step: never record inside the report.
  - The tree digest leaves out the record's own list of result files and the record. Keep that set identical when recording and checking.
  - An unusable record is `unavailable`, never `unrecorded`.
  - A record is an observation, not proof that tests ran. Do not describe a local `PASS` as a gate.
  - Tests pass a stand-in `observe`; `tests/test_tree_identity.py` uses real Git.
- **Result location.** `--record --junit PATTERN` replaces the default file-name search for test results; the record keeps the patterns and the report reads them from it. See ADR 0025.
  - Every stated match must be JUnit XML inside the target. Recorded files are left out of the tree digest, so do not loosen this.
  - Check patterns when reading a record as well as when writing one.
  - Only JUnit XML is read, and binding is verified with pytest-bdd only. Do not claim another runner works without a real run.
- **Not claimed here.** The report cannot detect a removed scenario or criterion. `change:definition` in change conformance does (ADR 0026).
- **Keep aligned.** The three schemas, the bundled example (its report must equal the real output for its own inputs), the closed sets shared by `criterion_identity.py` and the schemas, `tests/test_evidence_report.py` and `tests/wheel_evidence_smoke.py`.

### Actual-change conformance

`change_scope.py` captures bounded Git observations; `change_policy.py` reads accepted provider configuration; `change_architecture.py` measures scoped literal constraints; `change_defects.py` adapts existing eligibility/red-green execution. `change_conformance.py` recomputes request requirements and composes I04 checks. See ADR 0007 and `docs/CHANGE_CONFORMANCE.md`. Keep accepted policy outside the inspected tree, commands explicitly opted in, missing semantic/platform evidence unknown, and synthetic eight-pilot wheel coverage aligned. `artifact:experiment-record` maps assessor errors to FAIL and outstanding/unknown findings to UNKNOWN; `artifact:architecture-preflight` honors a declared outcome block. `migration.py` preserves legacy ownership and obligations; `maintenance.py` separately assesses release, resource, fit and CI facts.

`definition_change.py` backs `change:definition` (ADR 0026): a change may add scenarios and criteria, and a removed or altered one, or a changed `Background` above an existing scenario, fails.

- The check is added only when the change touches a feature definition file. Keep every other report byte-identical.
- It is pure and reads the captured snapshot. It never judges whether an edit weakens; any change to what existed is a finding for a person.
- `CODES` is a public contract: add, never rename. Messages hold no step text or values.
- It reuses `scenario_identity.py` for identifiers and digests. Do not change that module for it.

`protected_change.py` backs `change:protected` (ADR 0027): existing files under the declared `tests` may only gain lines, existing files under `files` may not change, and a declared escape marker's count may not rise.

- The declaration is the optional `protected` section of the accepted conformance configuration, read only from the trusted policy checkout. Never read it from the inspected tree.
- The check is added only when the section is declared. Nothing is protected by default.
- It is language-neutral on purpose. Do not add per-language test parsing here.
- Known limits, stated in the guide: an inserted line inside an existing test is not seen, and imports are not traced. Do not describe the check as proof that tests were not weakened.
- `CODES` is a public contract: add, never rename. Messages hold no file content.

`feature_verdict.py` backs `govkit conform --feature` (ADR 0028): one state for a feature, done, continue or escalate, from its evidence report and the change checks.

- **No feature option, no change.** Without `--feature` the report, the output and the exit status are byte-identical. `change-results` itself gains only the `evidence:feature` check; the answer is a separate `govkit.feature-verdict` document that holds both reports.
- **Order.** A weakened definition or protected file, or evidence in error, escalates first. Then anything the agent can do is `continue`. Then anything else not passing is `escalate`. Unknown is never done.
- **Who can act.** Failed, missing free, stale and unrecorded results are the agent's. Skipped, owed and not-compared results, and required checks without a pass, are a person's. Do not move a reason between the groups without a maintainer decision.
- **The evidence is read before any check runs.** A command `conform` executes must not supply the results it is judged by.
- **Not a gate.** `evidence:feature` passes on result files as a local check. Do not describe a local done as proof that tests ran, or as approval.
- **Public contract.** `CODES`, the states and the exit codes (0, 1, 3; 2 for a run that could not start): add, never rename.
- **Keep aligned.** The schema, the bundled example (it must replay through `parse_feature_verdict`), `tests/test_feature_verdict.py`, `tests/test_change_verdict.py` and the `feature_answer` pilot in `tests/wheel_change_smoke.py`.

`feature_artifacts.py` adds the feature artifact checks of `govkit validate` to a `--feature` run, chosen by the accepted profile and not a level (ADR 0029).

- **Selection.** `gherkin-delivery` selects the level 4 checks and `llm-evaluation` adds the level 5 checks, each as `feature:<identifier>` for the selected feature only. Without `gherkin-delivery` nothing is added.
- **Reuse, do not copy.** The check functions and identifiers come from `validate._named_checks`. Do not change `govkit validate` output for this path; `check_eval_criteria`'s `schema` argument is optional for that reason.
- **The forecast.** `feature:eval-prediction` is advisory and always unknown. Do not make it required: no feature could then be done.
- **The schema.** Chosen by the profile's `repository.project_type` and read from the bundled schemas, never from the inspected tree. Unset or unknown is unknown; do not add a default or detect it from the file.
- **Not yet.** A whole-repository run with the known-failures record (L08), and the other items of #220.

### Safe legacy migration

`migration.py` composes existing legacy/profile/pack/discovery/check boundaries in an isolated preview; `migration_store.py` owns bounded snapshots and reversible writes. See ADR 0008 and `docs/LEGACY_MIGRATION.md`. Default preview is read-only. Apply requires an explicitly accepted profile and exact preview digest; preserve configured obligations, user bytes/modes/mtimes, flat-marker content and opt-in authority. Rollback derives ownership from the verified lock and refuses edited resources. Metadata installation never establishes enforcement parity. Keep real legacy-install and runtime-only wheel pilots aligned. Canonical maintenance now feeds preview and post-operation verification; actual legacy removal remains a later release after an explicitly announced compatibility boundary and migration evidence.

### Maintenance version facts

`release_metadata.py` owns approved metadata, freshness and policy/runtime candidate selection; `maintenance_inventory.py` observes actual resource digests and composes protected previews through the existing pack store. `cmd_maintain.py` alone owns explicit cache output outside the target. See ADR 0009 and `docs/MAINTENANCE_INVENTORY.md`. Keep inventory/preview offline, source refresh data-only and anonymous, customizations protected, unknown freshness explicit and source/lookup timestamps separate. Do not infer enforcement or newest-version certification from inventory.

### Canonical maintenance assessment

`maintenance_facts.py` composes inventory, discovery and canonical CI check outcomes into four independent dimensions; `maintenance.py` captures/replays their inputs and compares post-operation findings. `maintenance_operations.py` revalidates inputs and freshness before routing protected previews. See ADR 0010 and `docs/MAINTENANCE_ASSESSMENT.md`. Required status must trace to accepted policy, including on passing CI checks; unverified lock claims cannot invent mandatory resources or version failures. CI evidence must match complete Git/profile/lock identity, scope and accepted age. Missing providers remain unknown; provider adapters consume explicit exports and preview integration changes, while live collection/authentication and protected-caller enforcement remain external. Saved release inputs must replay the effective metadata and candidates. Migration rechecks release/CI freshness at the current clock while keeping still-valid approval digests stable, then reruns assessment after application at the current time; disappearance without a passing dimension under unchanged policy is unverified. Preserve existing write authorization, customization protection and rollback. Keep runtime-only three-agent assessment and migration pilots aligned.

### Maintenance posture projection

`posture.py` projects replayed canonical maintenance assessments through a strict export allowlist; `cmd_posture.py` renders or explicitly publishes the result through the existing artifact writer. See ADR 0014 and `docs/POSTURE_REPORTING.md`. Preserve canonical findings/actions and reuse check aggregation; do not inspect a target or derive new upgrade decisions during export. Free text, paths, URLs and custom identifiers become pseudonymous references, not authenticated evidence. Public version displays omit local labels; exact values remain referenced. Maintenance execution is not project-control execution, and export success is not a conformance pass. Keep strict schemas, the bundled example and runtime-only three-agent/both-provider pilot aligned. `posture_aggregate.py` supplies offline fleet aggregation; `docs/ADOPTION_PILOT.md` defines the separate voluntary protocol. I12's source self-hosting selects no consumer payload.

### Change posture projection

`posture_change.py` separately projects replayed I07 change results. See ADR 0015 and `docs/CHANGE_POSTURE.md`. Preserve workflow obligations, independent evaluations, configured versus executed controls, canonical states/findings/actions and error-as-unknown behavior. Use the shared privacy descriptors and check aggregator; never combine maintenance/change identities or infer provider authentication. Reject contradictory repository identity and missing/weakened planned controls. Explicit change publication needs the caller-selected protected target because the source omits its filesystem root. Keep descriptor schema parity, the bundled example and eight real change wheel pilots aligned.

### Offline posture aggregation

`posture_aggregate.py` counts explicitly selected privacy-filtered exports for a caller-defined cohort and reporting clock; `cmd_posture.py` owns input I/O and stdout. See ADR 0016 and `docs/POSTURE_AGGREGATION.md`. Keep maintenance/change identities and denominators separate, identical duplicates idempotent, conflicting snapshots rejected, and missing/stale/unknown evidence out of fresh-pass numerators. Reuse canonical actions/states without another assessment engine or health score. Embedded export schemas must match their source contracts, and replay recomputes counts from validated exports. Keep all ten synthetic scenarios and the three-agent/both-provider wheel pilot aligned. The voluntary team protocol is documentation, not collected adoption evidence or telemetry.

### Shared gate catalog

`gate_catalog.py` composes typed logical GateSpec declarations from explicit profiles and local pack snapshots; `cmd_pipeline.py` exposes read-only `pipeline catalog`. See ADR 0011 and `docs/GATE_CATALOG.md`. All declarations share one common conformance invocation with trusted request/base/policy inputs. Preserve additive requirements and literal scopes; do not use the catalog as a runtime allowlist or introduce path filters that bypass conformance. Version pins and catalog readiness are composition facts, not execution/enforcement or publisher authentication. `gate_legacy.py` expands only the named bounded bundled legacy table at the loading boundary; the legacy adapter stays pure and all 258 frozen selections remain unchanged. Keep all three manifest references, runtime schema, examples and installed-wheel pilot aligned. `pipeline_render.py` and `pipeline_store.py` provide pinned entry points and protected generation; provider admission/evidence adapters retain external authority limits.

### Protected provider generation

`pipeline_render.py` emits paired reusable entry points; `pipeline_store.py` binds exact preview authorization and protects existing files; `pipeline_runtime.py` verifies runtime/profile/pack pins, including the lock-recorded resolver version, before the common engine. See ADR 0012 and `docs/PIPELINE_GENERATION.md`. Templates require caller-prepared isolated runtime, trusted policy checkout, request and full base SHA. Keep provider inputs in environment values, absolute interpreter validation and Python isolation. `pipeline_files.py` binds all generation writes, rollback and cleanup to no-follow directory handles; unsupported platforms fail before writes. Preserve edit protection, stale-input guards and explicit execution opt-ins. The common engine validates pipeline-wide opt-ins before filtering by actual request requirements; mandatory controls remain intact and local explicit selections stay strict. Configuration currency cannot imply activation/execution/enforcement. Provider admission, maintenance evidence and explicit publication are separate adapters; generation must not fetch/install packages or rewrite existing workflows. Keep paired goldens, schemas and three-agent installed-wheel execution pilots aligned.


### Provider admission and evidence

`provider_admission.py` validates caller-supplied native PR context and clean pinned checkouts before runtime execution. `pipeline_evidence.py` compares explicit provider/change exports and generated configuration, producing canonical CI checks for the existing maintenance engine. `pipeline_assessment.py` composes protected candidate integration previews; `artifact_publication.py` creates only explicitly requested new artifacts outside inspected checkouts. See ADR 0013 and `docs/PROVIDER_EVIDENCE.md`. Preserve unknown facts, original evidence age, ignored generated-file identity and accepted request byte snapshots. Provider exports retain unverified-artifact provenance; imported success claims remain unknown and explicit failures survive unrelated report mismatches. They are not authenticated live collection; credentials, branch/reviewer policy and activation stay with protected callers. Keep both providers' schemas/examples, optional publication snippets and runtime-only wheel pilots aligned.
