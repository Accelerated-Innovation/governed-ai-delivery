# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [0.14.0] — 2026-07-22

### Added

- Added a first-class `implementation_profiles` mechanism for extensions. An
  extension can now ship advisory **default product bindings** — a profile that
  maps a neutral contract set to concrete products a team may customize —
  separate from its provider-neutral `contract_sets`. The generic
  extension-manifest schema documents the key (`id`, `path`, `profiles_for`,
  `authority`, `product_selection_requires_adr`, and a reserved `gate`), and
  profiles are validated for path safety while remaining exempt from the
  contract-neutrality overlap heuristic (a profile is meant to name products).
  Two profiles ship on top of it: `AGENT_RUNTIME_STACK.md`
  (`skill-oriented-agent-architecture`) mapping the SOAA runtime
  responsibilities to default bindings, and `GATEWAY_STACK.md`
  (`llm-application`) mapping the model-gateway/observability/guardrail ports.
  Both are advisory, require an ADR to deviate, and wire no blocking CI gate.
- Added the bundled `skill-oriented-agent-architecture` extension. It translates
  approved SOAA v0.2 decisions into five progressively loaded contract sets for
  core semantics, selection and authority, context and resilience, assurance,
  and lifecycle interoperability. The package is provider-neutral, owns agent
  architecture outside the core baseline, and includes focused validation and
  installation tests.
- Added the bundled, provider-neutral `llm-application` extension with
  progressively loaded contracts for model gateway access, model evaluation,
  model observability, and model guardrails. Coding-agent rules and Level 5
  preflight/plan templates now load those contracts while concrete gateway,
  telemetry, evaluator, guardrail, and orchestration products remain optional
  implementation profiles selected in `TECH_STACK.md` or an ADR.

### Removed

- Removed the deprecated `agentic-skills` extension. It was the predecessor to
  `skill-oriented-agent-architecture`, which supersedes it; the two were never
  meant to be installed together. The generic extension-manifest JSON schema it
  hosted was a shared framework asset used by every extension's tests and has
  moved to `governance/schemas/extension-manifest.schema.json` (alongside the
  agent-manifest, marker, and stack-overlay schemas). The agentic-only smoke
  script `scripts/smoke-extensions.ps1` was removed with it.

### Fixed

- `govkit upgrade` no longer erases the team's calibration. It wrote the marker
  without threading the stored `stack`, `assumptions`, and `calibration`
  blocks, so every upgrade reset them to `null` / `[]` / no decisions —
  discarding each `calibration.decisions[]` entry, every `review_required:
  false` an assumption had earned, and the selected stack. The loss cascaded:
  `post_install_finalize` regenerates `.govkit/skill_context.yaml` from the
  marker, so a wiped `stack` silently blanked the stack facts the agent reads
  (`stack.id: null`). `apply`, `stack apply`, and `calibrate` already carried
  these through; `upgrade` was the lone writer that did not. `applied_at` still
  advances on upgrade — that is a re-install, and edit-protection depends on it.
- `govkit upgrade` now retires the pre-namespace rules and skills it used to
  leave behind. Moving govkit's rules under `.claude/rules/govkit/` (and
  `.github/instructions/govkit/`) and prefixing its skills `govkit-` changed
  where those files install, but upgrade wrote the new paths without removing
  the copies govkit itself had written at the old ones — so an agent that
  auto-loads its rules directory recursively ingested both, duplicating
  governance and contradicting it wherever the two versions had drifted.
  Upgrade now removes a superseded rule or skill when it is provably govkit's
  own (byte-identical to what govkit installs today, or untouched since the
  last apply); a file the team wrote or edited at the old path is kept, and
  govkit's namespaced copy installs alongside it — which is the point of the
  namespace. The cleanup runs only while the marker predates the move, and a
  delete it cannot perform warns instead of aborting the upgrade.
- `govkit upgrade` no longer crashes when the marker's `applied_at` is
  timezone-naive, or when a superseded file cannot be deleted. The first
  raised `TypeError` comparing a naive timestamp against a timezone-aware
  mtime; both are now treated as unknown history, which never authorizes a
  delete.

### Changed

- Removed the duplicate core `AGENT_ARCHITECTURE.md`,
  `LLM_GATEWAY_CONTRACT.md`, `EVALUATION_LLM_CONTRACT.md`,
  `OBSERVABILITY_LLM_CONTRACT.md`, and `GUARDRAILS_CONTRACT.md` files. Their
  maintained guidance now lives in `skill-oriented-agent-architecture` or
  `llm-application`; core apply/upgrade no longer needs maturity-level filename
  exclusion logic for those documents.
- **govkit's layer rules now install under a `govkit/` subdirectory**, so a team's
  own same-named rule survives. claude-code rules move to `.claude/rules/govkit/`
  and copilot's to `.github/instructions/govkit/` — a team that keeps their own
  `.claude/rules/api.md` (or `api.instructions.md`) is no longer clobbered by
  govkit's `api` rule; both coexist and load. Skill namespacing is not included
  here (it would change how govkit skills are invoked, e.g. `/spec-planning`), and
  codex's nested per-layer `AGENTS.md` files are unchanged for now.
- **govkit's skills are now prefixed `govkit-`**, so a team's own skill that shares
  a bare name with one of govkit's is no longer overwritten. This renames both the
  installed skill directory and its invocation name — e.g. `/spec-planning` becomes
  `/govkit-spec-planning` (and `$spec-planning` for codex). Governance content and
  skill descriptions are updated to the prefixed names. A team's own
  `.claude/skills/spec-planning/` now coexists with govkit's `govkit-spec-planning`.
- **Codex's nested per-layer `AGENTS.md` files are now installed as managed
  blocks too.** They must live in real source directories (`api/`, `services/`,
  …) for codex's path-scoping, so they can't move to a namespace — instead
  govkit fences its per-layer guidance in the same `BEGIN/END GOVKIT GOVERNANCE`
  block used for the root `AGENTS.md`, preserving a team's own content in those
  files.
- **govkit no longer overwrites your `CLAUDE.md` or `.github/copilot-instructions.md`.**
  Both agents natively auto-load a separate instructions directory, so govkit's
  governance now installs there — `.claude/rules/govkit/governance.md` for
  claude-code (plus a `src/**`-scoped `governance-src.md` for UI types) and
  `.github/instructions/govkit/governance.instructions.md` (`applyTo: "**"`) for
  copilot — and govkit writes no top-level instruction file at all. A team that
  wrote its own `CLAUDE.md` keeps it untouched while govkit's governance still
  loads every session. On `upgrade`, an existing install's old govkit-authored
  instruction file is retired automatically when it is govkit's own — either
  byte-identical to the current governance or untouched since the last apply
  (so older-version files clean up too); if you edited it, it is kept and
  governance install is skipped (with a warning) so you never get duplicate
  governance. Codex (`AGENTS.md`, which has no native rules directory) is
  unchanged for now.
- `govkit doctor`'s rule-glob check (D001) now scans the rules directory
  recursively, so rules in subdirectories — including govkit's own
  `.claude/rules/govkit/` — are validated instead of silently skipped.
- **Codex `AGENTS.md` is no longer overwritten wholesale.** Codex has no
  auto-loaded rules directory, so its governance must share `AGENTS.md` with the
  team — govkit now installs it as a managed block fenced by
  `<!-- BEGIN GOVKIT GOVERNANCE -->` / `<!-- END GOVKIT GOVERNANCE -->`, and
  preserves whatever the team wrote outside it. On `upgrade`, an existing
  pre-block govkit `AGENTS.md` is replaced by the block when it is provably
  govkit's own (byte-identical or untouched since `applied_at`); a team's file
  keeps its content with the block appended below. Nested per-layer `AGENTS.md`
  files are unchanged for now.

### Changed — internal

- Version comparison now treats absent components as zero, so `0.14` and
  `0.14.0` compare equal. Comparing the parsed tuples directly made
  `(0, 14) < (0, 14, 0)`, which sorted a version before the release it names —
  enough to put a marker on the wrong side of the gates that gate on `0.7.0`
  and `0.14.0`. Markers are not schema-validated, so abbreviated versions are
  reachable by hand-editing.
- `write_managed_agent_block` and `install_agent_file` were each defined twice,
  byte-identically, in `cli/install_common.py`; the redundant copy is removed.
  Python kept the second definition and the two matched, so there was no
  behavior change.
- The two stack marker records (the `stack.id` assumption and the `stack`
  metadata block) are now built only by `stack_select.build_stack_assumption`
  / `build_stack_meta`; `govkit stack apply` consumes them instead of
  inlining copies, so the two write paths cannot drift apart. See
  `plans/STACK_RECORD_DEDUP_PLAN.md`.
- The three one-time migration warnings in `cli/marker.py` (version, shape,
  directory) now share a single `_OneTimeWarning` value object instead of
  three copies of the flag/env-check/reset machinery. Messages, suppression
  env vars, and test reset helpers are unchanged. See
  `plans/MARKER_WARNING_CONSOLIDATION_PLAN.md`.
- Stack overlays are now the single owner of per-stack facts: `overlay.yaml`
  gains a required `supported_types` list (schema-enforced), doctor D005
  reads the expected language from the overlay's `skill_context.language`,
  and type-gating in stack selection reads `supported_types`. Deletes the
  parallel `_STACK_PRIMARY_LANGUAGE` and `_STACK_SUPPORTED_TYPES` code
  tables — adding a stack is now purely additive. Guard tests keep every
  bundled overlay declaring both facts. No user-facing behavior change and
  no overlay version bumps. See `plans/STACK_METADATA_UNIFICATION_PLAN.md`.
- Per-agent on-disk layout facts (instruction file, rules dir, rules glob,
  frontmatter glob key/shape) now have a single owner: `cli/agent_layout.py`.
  Replaces four private copies in `calibrate`, `setup_review`, `doctor`, and
  `rule_templating`. No user-facing behavior change; a bundle-parity test
  keeps the table and `agents/` in sync. See
  `plans/AGENT_LAYOUT_REFACTOR_PLAN.md`.

---

## [0.13.0] — 2026-06-07

### Added — Databricks and conservative data stack support

- Added a `databricks-lakehouse` data stack overlay for Databricks-native repos
  using Unity Catalog, Delta tables, Asset Bundles, Jobs, Lakeflow Pipelines,
  PySpark, SQL, and notebooks.
- Data installs now include a conservative `data-common-gate.yml` for GitHub
  or Azure. The gate runs static governance checks only and leaves warehouse,
  workspace, source freshness, and pipeline execution to opt-in stack gates.
- `python-dbt` data installs now include a conservative `dbt-gate.yml` for
  GitHub or Azure. The gate runs dbt dependency, parse, compile, SQLFluff, and
  static model YAML checks while keeping warehouse-backed execution opt-in.
- `databricks-lakehouse` data installs now include a conservative
  `databricks-gate.yml` for GitHub or Azure. The gate runs static Databricks
  configuration checks and optional bundle validation only when CLI auth is
  configured; workspace-backed execution remains opt-in.
- Added Databricks-native demo fixtures and documented mixed-signal precedence:
  when `dbt_project.yml` and Databricks bundle config are both present, GovKit
  treats the repo as `python-dbt` by default unless `--stack
  databricks-lakehouse` is passed explicitly.

### Changed — data stack selection and documentation

- Data CI behavior is now explicit in all production agent manifests: `--type
  data` installs the common repo-scope governance gate for GitHub or Azure at
  L3/L4 instead of inheriting it accidentally from the base CI block.
- `govkit upgrade` now validates marker options against the current manifest
  before resolving variants, so malformed markers fail fast instead of silently
  omitting governed CI gates.
- Manifest resolution now supports optional `by_stack` entries nested under
  `by_type`, enabling stack-aware data CI gates while preserving common CI for
  unmapped future stacks.
- README data-stack guidance now describes the conservative CI model: common
  governance is installed by default, while stack-specific execution gates
  remain opt-in until configured.
- README and Databricks stack guidance now document how GovKit and Databricks
  agent skills work together: GovKit remains authoritative for repo delivery
  governance, while `databricks aitools install` provides optional
  platform-specific assistant guidance.
- Databricks Asset Bundle repos with `databricks.yml` / `databricks.yaml` now
  auto-detect the `databricks-lakehouse` stack instead of falling back to the
  `python-dbt` data default.

### Fixed — data stack boundary and discoverability

- `govkit apply --type data --level 5` now fails fast with a clear message. Data
  projects support L3/L4 only; L5 remains the GenAI Operations tier for LLM
  application delivery.
- `govkit init --starter data --level 5` is also rejected instead of silently
  scaffolding the L4 data starter under an L5 request.
- `python-dbt` is now advertised in every production agent manifest's stack
  choices, so `govkit list` reflects the actual data default stack.
- `apply --stack` help and README stack-default wording now describe type-aware
  defaults (`python-fastapi` for `api` / `cli`, `python-dbt` for `data`).
- L4 data installs for Claude Code, Codex, and Copilot now include the
  `architecture-preflight`, `spec-planning`, and `implementation-plan` skills
  referenced by the generated data instructions.

### Maintenance

- Bumped the pinned `actions/checkout` workflow action used by CI and publish
  workflows.

---

## [0.12.0] — 2026-06-05

### Added — extension packs ship with the wheel + `govkit extension` command

Extension packs were repo-reference only and never distributed via PyPI. They now ship inside the wheel (`cli/extension_packs/`, force-included from `extensions/`), installable via a new command:

- `govkit extension list` — enumerate bundled packs (id, name, supported levels/types).
- `govkit extension add <id> --target <path> [--force]` — copy a pack into the target's `extensions/<id>/`, validate it in place, and **warn-and-proceed** on a level/type mismatch against the `.govkit` marker or a missing `relates_to.extends` core contract. `--force` overwrites an existing folder.

This makes `supported_levels` / `supported_project_types` non-inert — `extension add` now surfaces them as install-time warnings.

### Added — `vision-inference` extension pack

Governs applications that **consume** pretrained or hosted vision models (rather than train them), layered on `--type api` / `--type cli`. Two contract sets: discriminative (model-as-adapter, version pinning + drift, black-box acceptance eval, biometric data handling, PII-safe prediction logging) and generative/VLM (multimodal input, reusing the L5 GenAI-Ops contracts via `relates_to.extends`).

### Verification

- New `tests/test_cmd_extension.py` (list, add, overwrite guard, compat warnings) and `tests/test_vision_inference.py`. Full suite green on 3.11 + 3.12; wheel build confirmed to bundle `cli/extension_packs/` for both packs.

---

## [0.11.1] — 2026-06-05

### Fixed — `govkit calibrate` leaked internal PR references

The skill-context calibration step (step 9) printed internal roadmap language — `"generated at end of calibrate (PR 5+)"` and `"PR 6a wires the consumers"` — into the interactive prompt and the generated `GOVKIT_CALIBRATION_CHECKLIST.md`. Reworded to user-facing text, with a regression test asserting no calibration step exposes a `PR <n>` reference.

### Changed — README rewritten story-first

The README was reorganized so the install/customize path leads and reference material follows, addressing feedback that the getting-started flow was buried.

- New 4-step **Get started** checklist (install → apply → `govkit calibrate` → commit) with `govkit calibrate` as the canonical customize step.
- Agent/type/level/ci/stack options collapsed into one table; the full command matrix moved into a `<details>` block.
- Feature lifecycle written once (Claude Code) with a single agent-equivalents table instead of per-step 3-agent tables.
- New **Commands** table documenting all 8 subcommands; **Extensions** restructured ("how to add" before "authoring").
- Corrected stale content: `govkit doctor` and `govkit calibrate` are documented as shipped (not "future"); `doctor` positioned as a code/CI fit-check.

### Verification

- pytest green on 3.11 + 3.12 (new `test_no_internal_pr_references_in_user_facing_text`); wheel-smoke green.

---

## [0.11.0] — 2026-05-28

### Added — `--type data` parity for codex + copilot

`govkit apply --type data` (dbt/data projects) was claude-code-only. Codex and copilot now ship the same dbt data shape, bringing all three production agents to parity.

- Each agent's manifest gains `data` in `options.type.choices` and a `variants.type.data` block (L3 baseline + L4 spec-driven add-on; data has no L5 GenAI-ops tier).
- **Codex** installs `agents-md/data.md` + `agents-md/l4-data.md` (nested-`AGENTS.md` voice) and `rules/data/{staging,intermediate,marts,data-quality,pii}.md`. The dbt layers map to nested `models/<layer>/AGENTS.md`; the cross-cutting quality/PII rules land in `.agents/rules/`.
- **Copilot** installs `copilot-instructions/data.md` + `copilot-instructions/l4-data.md` and `instructions/data/*.instructions.md` with `applyTo` frontmatter (`**/models/staging/**`, etc.).
- The dbt-layer rule **bodies are identical to claude-code's** — codex strips the glob frontmatter (it scopes by nested placement); copilot uses `applyTo`. The governed `docs/data/architecture/` contracts and the `python-dbt` stack overlay are agent-agnostic and were already shared, so no new governed content was needed.

### Fixed — real `apply --type data` now selects `python-dbt`

0.10.1 fixed the `--detect` dry-run, but the **real install path still picked `python-fastapi`**: `resolve_options` silently fills `options["stack"]` from the manifest's `stack` default (`python-fastapi`, no prompt), and the stack-choice fallback consulted that value, shadowing the per-type default (`data → python-dbt`). Stack selection is now decoupled from `options["stack"]` — it reads the raw `--stack` flag (or falls through to the per-type default), so the installed marker and overlay match the requested shape. Covered by a real-`cmd_apply` regression test.

### Changed — `cli/govkit.py` decomposed (internal; no CLI behavior change)

The 1797-line `cli/govkit.py` was split into a focused module set with a strict inward dependency graph (commands → domain → kernel) and no import cycles. `govkit.py` is now ~68 lines: argparse wiring + a registrar table that dispatches via `set_defaults(func=...)`.

- New kernel modules: `cli/paths.py`, `cli/version.py`, `cli/marker.py`, `cli/fs.py`, `cli/manifest.py`, `cli/install_common.py`.
- New command modules: `cli/cmd_apply.py`, `cli/cmd_upgrade.py`, `cli/cmd_init.py`, `cli/cmd_stack.py`, `cli/cmd_list.py`, `cli/cmd_validate.py` — each owns its argparse surface via a `register(subparsers)` function. Adding a command is now a new module + one line in `_REGISTRARS` (OCP).
- **Internal import surface moved.** Code that imported helpers from `cli.govkit` (e.g. `from cli.govkit import read_govkit_marker`) must import from the owning module (`cli.marker`, `cli.fs`, `cli.manifest`, `cli.cmd_*`). The public surface — the `govkit` CLI — is unchanged. `cli.*` is not a documented API; this is flagged as the reason for the minor bump.

### Verification

- 822 pytest tests pass + 1 expected skip. New: `test_data_type_parity_across_agents` (3, parametrized over the agents), `TestApplyTypeDataStackDefault`, `tests/test_main_dispatch.py` (registry dispatch), `tests/test_stack_select.py`.
- `smoke.ps1` agent×level matrix green (L4/L5 validate-fails are by design); data-apply smoke verified for codex + copilot (correct `python-dbt` stack, files land, governed docs install).

---

## [0.10.1] — 2026-05-27

### Fixed — `--type data` stack selection

Patch release fixing two stack-selection bugs and one missing data artifact, all found while preparing a dbt demo against v0.10.0.

- **`--type data` no longer adopts an incompatible inferred stack.** When a repo had an ambient framework signal from a *different* shape — e.g. `fastapi` mentioned in `pyproject.toml` of a dbt project — `govkit apply --type data` would select the `python-fastapi` stack (high-confidence framework inference) and install its `docs/backend/architecture/` overlay docs, contradicting the requested data shape. `_resolve_stack_choice` now checks a new `_STACK_SUPPORTED_TYPES` map and rejects an inferred stack that doesn't support the requested `--type`. Precedence is now: explicit `--stack` flag → type-compatible high-confidence inference → per-type default. The user's explicit `--type` intent outranks an incidental framework signal. The same guard protects the inverse case (an ambient `dbt_project.yml` no longer hijacks a `--type api` install).
- **`govkit apply --detect` now reports the stack real apply would pick.** The dry-run path had its own inlined copy of the stack-resolution logic with the same bug. It now delegates to `_resolve_stack_choice`, so the proposed config can't drift from actual apply behavior.
- **Data installs now ship `docs/data/architecture/ADR/TEMPLATE.md`.** `l4-data.md` advertises `/adr-author` and the shared `adr-author` skill references `ADR/TEMPLATE.md`, but no ADR template was installed for data projects — the skill pointed at a missing file. Added a data-adapted ADR template (layer-boundary, data-contract, and PII/compliance impact sections instead of the backend HTTP-route framing). It ships via the existing `docs/data/architecture/` folder copy — no manifest change.

### Verification

- 805 pytest tests pass + 1 expected skip (was 798). New tests: `TestResolveStackChoiceTypeCompatibility` (5), `TestCmdApplyDetectFlag::test_detect_flag_with_type_data_ignores_ambient_fastapi`, `TestDbtProjectFixture::test_data_adr_template_installed`.
- Built wheel confirms `cli/docs/data/architecture/ADR/TEMPLATE.md` ships.

---

## [0.10.0] — 2026-05-27

### Added — Governance Accelerator

Govkit shifts from "template installer" to **calibrated governance accelerator**. Every install now (1) declares what it assumes about the repo, (2) provides a `doctor` for CI-time fit validation, and (3) provides a `calibrate` for guided team review. The goal: an install never silently contradicts the repo it landed in.

Three new commands ship in this release:

```bash
govkit stack list                      # enumerate bundled stack overlays
govkit apply --stack dotnet-aspnet     # first-class stack selection (with auto-detection)
govkit apply --detect                  # dry-run inference, print proposed config, exit 0
govkit stack apply <id> --target .     # swap stacks on an existing install (edit-protected)
govkit doctor [--target .]             # read-only fit validator with 12 checks
govkit calibrate [--target .] [--non-interactive] [--only <step>]
                                       # guided 9-step team review of installed governance
```

### Why the change

Pre-0.10 govkit installed a Python/FastAPI/hexagonal baseline regardless of the target repo, with no way to detect or warn about mismatches. A .NET repo that ran `govkit apply` got rule globs pointing at `**/adapters/**` (no matches), Python pytest examples in TESTING.md, and L5 LLM tooling sections in TECH_STACK.md it would never use. The agent then followed that contradictory guidance.

0.10 keeps the small, opinionated baseline but adds explicit assumptions, repo-fit detection, and an edit-protection contract so teams can adapt the installed governance without losing their changes on the next `upgrade`.

### `.govkit/` directory migration

The `.govkit` marker file becomes a `.govkit/` **directory** containing `marker.json` + (post-`apply`) `skill_context.yaml`. Legacy single-file markers are read tolerantly and migrated in place on first read; a one-time stderr warning fires (suppressible via `GOVKIT_NO_DIRECTORY_MIGRATION_WARNING=1`). No team action required.

`marker.json` schema (validated by `governance/schemas/govkit-marker.schema.json`) gains three new top-level fields:
- `stack: { id, version, display_name, applied_at }` — selected stack overlay metadata
- `assumptions: [ { id, value, source, confidence, evidence, files_affected, review_required, warning_message, calibrated_at, calibrated_against_overlay_version } ]` — every load-bearing choice with provenance
- `calibration: { completed_at, decisions: [...] }` — team's review state

### Edit-protection contract

Every governed/shared `.md` doc gets a `<!-- govkit:editable baseline: <id>@<version> -->` header on install. Subsequent `govkit upgrade` and `govkit stack apply` check the file's mtime against the marker's `applied_at` — if you've edited the doc since the last apply, it's preserved and the command exits without overwriting. Pass `--force` to override (the warning makes the destruction explicit). `cmd_upgrade` previously overwrote governed docs unconditionally; this PR closes that data-loss path.

### First-class stack overlays

The four stack overlays in `docs/stacks/` (dotnet-aspnet, java-spring-boot, nodejs-fastify, go-gin) move to `cli/stacks/` and gain a `python-fastapi` sibling so all 5 are structurally identical. Each carries an `overlay.yaml` with `id`, `version`, `display_name`, `summary`, `default_assumptions`, `docs`, `skill_context`, and `review_checklist`.

- `govkit apply --stack <id>` installs the chosen overlay on top of the baseline copy.
- `govkit stack list` enumerates bundled stacks from the installed wheel — no more `cp docs/stacks/...` against the repo checkout.
- `govkit stack apply <id> --target <path>` swaps stacks on an existing install.

### Repo-fit detection

A new `cli/detect.py` inspects the target tree for language, framework, CI, architecture, and LLM signals. Detection is target-scoped (per A10 — never walks from cwd, so monorepos don't cross-contaminate). csproj parsing uses `xml.etree.ElementTree` and checks `Project.Sdk` / `FrameworkReference.Include` rather than substring-matching package names (R3 — avoids false-positives like `Microsoft.AspNetCore.Authentication.Core` being mistaken for ASP.NET Core).

When `--stack` is omitted, `cmd_apply` runs detection and either: (a) high-confidence framework match → use the inferred stack, record assumption with `source: "detected"`; (b) otherwise → fall back to `python-fastapi`, record `source: "default", review_required: true` so the team is nudged to calibrate.

### `govkit doctor`

Read-only validator with monorepo auto-discovery (per A9). When `--target` is omitted, doctor walks for `.govkit/` directories under cwd and processes each install. 12 checks ship:

| ID | Severity | Catches |
|---|---|---|
| D000 | error | No `.govkit/marker.json` at target |
| D001 | error | Rule glob (agent-aware: claude-code `paths:`, copilot `applyTo:`, codex nested AGENTS.md skipped) resolves to 0 files |
| D003 | warning | Marker CI ≠ detected CI files |
| D004 | warning | Both GitHub Actions and Azure Pipelines present |
| D005 | warning | Stack's expected language disagrees with detection |
| D006 | warning | Installed doc baseline header older than bundled overlay version |
| D007 | warning | L5-only keywords (LiteLLM, DeepEval, NeMo, etc.) in a non-L5 install |
| D008 | info | L5 install with no LLM SDK in deps |
| D009 | warning | TESTING.md names a framework absent from dep manifests |
| D010 | warning | `review_required` assumption stale >30 days without calibration |
| D011 | error | Assumption `files_affected` lists missing paths |
| D013/D014 | error/warning | Extension manifest issues (delegates to `cli/extensions.py`) |

### `govkit calibrate`

Walks the team through a 9-step checklist (marker, TECH_STACK, BOUNDARIES, API_CONVENTIONS, TESTING, agent-instruction file, rules tree, CI gates, skill context). Two modes:

- **Interactive** (default) — prompts per step with `[y/n/s/q]` decisions
- **`--non-interactive`** — emits `GOVKIT_CALIBRATION_CHECKLIST.md` as a markdown todo file (CI-friendly)

Decisions are recorded in `marker.json.calibration.decisions[]` and per-assumption `calibrated_at` + `calibrated_against_overlay_version` fields. An assumption is resolved only when ALL linked steps confirm with no `needs-review` — one needs-review keeps it open. `--only <step>` revisits a single decision. Monorepo behavior mirrors doctor's. `calibrate` preserves the original `applied_at` (per A2) so edit-protection isn't silently weakened by every calibration pass.

### Skill context

A new `.govkit/skill_context.yaml` ships alongside `marker.json`. Skills (PR 6b/c rewrites) read a typed `SkillContext` via `load_skill_context(target)` for architecture style, source root, layer-to-folder hints, stack facts, CI, LLM flag, and discovered extensions. Written by `apply`, `upgrade`, `stack apply`, and `calibrate` — always fresh.

### Rule-glob templating

Layer-bound rule files in the source tree (e.g. `agents/claude-code/rules/backend/adapters.md`) now declare `paths_template: layers.outbound` alongside a hexagonal fallback `paths:`. At install time, `template_installed_rules(target, agent, layers)` expands the directive using `skill_context.layers.*` so the actual rule frontmatter ends up matching the team's folder layout (`**/Infrastructure/**` for clean architecture, `**/adapters/**` for hexagonal). Copilot's `applyTo:` (single string) is handled by the same helper via an `applyTo_template:` schema.

### L5 contract isolation

The 5 L5-only architecture contracts (`AGENT_ARCHITECTURE.md`, `LLM_GATEWAY_CONTRACT.md`, `GUARDRAILS_CONTRACT.md`, `OBSERVABILITY_LLM_CONTRACT.md`, `EVALUATION_LLM_CONTRACT.md`) now install only at L5. `cmd_apply` and `cmd_upgrade` pass an exclusion set to `copy_entry` at L3/L4. The L5-tagged sections of `TECH_STACK.md` (§4 Agent Frameworks, §4a LLM Gateway, §10a LLM Evaluation, §11 LLM Observability subsection, §11a Runtime Guardrails) were stripped from all 5 stack overlays — the same content already lived in `AGENT_ARCHITECTURE.md`. Doctor's D007 is silent on fresh L4 installs as a result.

### Skill body audit

The four claude-code backend skills (`architecture-preflight`, `spec-planning`, `implementation-plan`, `adr-author`) no longer name architecture-style folders (`ports/`, `adapters/`, `Controllers/`, `Application/`) or stack-specific libraries (`pytest`, `pydantic`, `FastAPI`) inline. They cite `docs/backend/architecture/BOUNDARIES.md` and `.govkit/skill_context.yaml` instead — the same skill text now works whether the team's repo is hexagonal, clean, or layered.

The architecture-preflight skill's §2.6 Extension Discovery block (per R4) is preserved intact; the `agent_guidance.architecture_preflight` contract on extension manifests continues to work.

### `--type data` (dbt-layered, claude-code)

A first cut of `--type data` ships for the claude-code agent so data teams can adopt the same calibrated-installer flow as backend teams. The shape mirrors `--type api`: opinionated baseline + stack overlay + worked starter feature, all editable with assumptions surfaced for team review.

- **New `--type data` choice** on `govkit apply` (claude-code only for now; copilot/codex variants land later).
- **New `python-dbt` stack overlay** (`cli/stacks/python-dbt/`) — 6 docs (TECH_STACK, QUERY_CONVENTIONS, TESTING, MODEL_LAYERING, PII_HANDLING, LINEAGE_OBSERVABILITY) covering dbt-core + a warehouse adapter (Snowflake / BigQuery / Redshift / Postgres), SQLfluff, dbt schema tests, optional `dbt-expectations` for L4.
- **New `docs/data/architecture/` baseline contracts** — 8 governed contracts (ARCH_CONTRACT, BOUNDARIES, DESIGN_PRINCIPLES, PIPELINE_CONTRACT, DATA_QUALITY_CONTRACT, LINEAGE_CONTRACT, PII_HANDLING_CONTRACT, ENVIRONMENTS) — the data-shape equivalent of the backend contracts.
- **New `.claude/rules/data/`** — 5 rules (`staging`, `intermediate`, `marts`, `data-quality`, `pii`); the layering rules use `paths_template: layers.{inbound,domain,outbound}` so they expand to whichever layer vocabulary the team uses (staging/intermediate/marts by default; medallion teams edit `skill_context.yaml`).
- **New `cli/detect.py` signals** — `dbt` framework (via `dbt_project.yml`) and `dbt-shape` architecture (via `models/{staging,intermediate,marts}/`). Detection promotes `python-dbt` to the inferred stack when `dbt_project.yml` is present.
- **New `dbt-layered` architecture style** in `cli/skill_context.py` — `inbound = models/staging/`, `domain = models/intermediate/`, `outbound = models/marts/`. Calibrate steps 3 (boundaries), 4 (now `QUERY_CONVENTIONS` instead of `API_CONVENTIONS` for data installs), and 5 (testing) speak data-team language.
- **New `features/starter_data/`** — a worked `customer_dim_freshness` L4 feature (acceptance.feature with `@nfr-freshness / @nfr-quality / @nfr-pii / @nfr-lineage / @nfr-reliability / @nfr-cost` scenarios, nfrs.md, eval_criteria.yaml, plan.md, architecture_preflight.md). `govkit init <feature> --starter data` scaffolds it.
- **New `tests/fixtures/dbt-project/`** — minimal dbt fixture (`dbt_project.yml` + `models/{staging,intermediate,marts}/` + `.github/workflows/`) backing 6 new tests in `tests/test_fixtures.py::TestDbtProjectFixture` that lock down detection, stack inference, rule-glob templating, and contract installation.

CI gates for `--type data` are intentionally left empty in `agents/claude-code/manifest.json::ci.<platform>.by_type.data` for this release — gate selection is the kind of thing teams want to shape themselves, and shipping a default would foreclose that conversation. Future releases will add opinionated dbt CI gates (source freshness checks, dbt test, SQLfluff) once we have feedback from real teams.

### Added
- **New CLI commands**: `govkit doctor`, `govkit calibrate`, `govkit stack list`, `govkit stack apply <id>`.
- **New `--stack <id>`, `--detect`, and `--force` flags** on `govkit apply`.
- **New `--force` flag** on `govkit upgrade` for explicit override of edit-protection (the existing `--force` on upgrade keeps its "re-apply at current version" meaning; both behaviors now ride the same flag).
- **`cli/detect.py`** — `RepoProfile`, `build_profile(target)`, `infer_stack(profile)`, language/framework/CI/architecture/LLM signal detectors.
- **`cli/doctor.py`** — `ValidationFinding`, `run_doctor`, `cmd_doctor`, `discover_install_targets`, and 9 registered checks (D001, D003–D011, D013/D014).
- **`cli/calibrate.py`** — `CalibrationStep`, `CalibrationDecision`, `build_checklist`, `cmd_calibrate`, `render_checklist_markdown`.
- **`cli/skill_context.py`** — `SkillContext`, `build_skill_context`, `write_skill_context`, `load_skill_context`.
- **`cli/overlay.py`** — `Overlay`, `STACKS_DIR`, `load_overlay`, `list_overlays`, `apply_overlay`.
- **`cli/headers.py`** — `format_editable_header`, `parse_editable_header`, `has_editable_header`, `prepend_header_to_file`.
- **`cli/setup_review.py`** — `write_setup_review`, `print_review_checklist` (agent-aware paths for claude-code / copilot / codex).
- **`cli/rule_templating.py`** — `expand_rule_template`, `template_installed_rules` (handles claude-code `paths_template:` and copilot `applyTo_template:`).
- **`governance/schemas/govkit-marker.schema.json`** — JSON Schema for `marker.json`, exercised by `tests/test_schemas.py`.
- **`cli/stacks/<id>/overlay.yaml`** for all 6 stacks (the 5 backend stacks + `python-dbt`) — `id`, `version`, `display_name`, `summary`, `default_assumptions`, `docs`, `skill_context`, `review_checklist`.
- **`--type data`** end-to-end (claude-code only): `python-dbt` stack overlay, `docs/data/architecture/` baseline contracts, `.claude/rules/data/` (staging/intermediate/marts/data-quality/pii), `dbt` framework + `dbt-shape` architecture detection, `dbt-layered` skill_context style, `features/starter_data/` worked example, data-aware calibrate steps. See narrative section above.
- **Five fixture repos** under `tests/fixtures/` — `dotnet-aspnet-azure/`, `python-fastapi-github/`, `empty/`, `monorepo/` (apps/api + apps/web), `dbt-project/` (dbt_project.yml + models/{staging,intermediate,marts}/) for end-to-end coverage.
- **Built-wheel smoke test** (per A12) — new `wheel-smoke` CI job: `python -m build`, `pip install dist/*.whl` into a clean venv, `govkit stack list` confirms all 5 stacks resolve, then a fresh `apply --stack dotnet-aspnet` exercises the full install path. Catches packaging regressions that editable installs can't.
- **Tests** — 326 new tests (440 → 766). New modules: `test_doctor.py` (50), `test_calibrate.py` (20), `test_skill_context.py` (17), `test_detect.py` (42), `test_overlay.py` (13), `test_rule_templating.py` (15), `test_setup_review.py` (13), `test_headers.py` (20), `test_fixtures.py` (33). Existing test modules also grew with PR-specific additions.

### Changed
- **`.govkit` marker** — now a directory (`.govkit/marker.json` + `.govkit/skill_context.yaml`). Legacy single-file markers auto-migrated on first read.
- **`copy_entry`** — extended with `applied_at`, `force`, `header_baseline`, `header_see`, `exclude_basenames`. Default values preserve pre-0.10 behavior for agent files; governed/shared paths pass the new args.
- **`write_govkit_marker`** — accepts optional `stack`, `assumptions`, `calibration`, `applied_at` kwargs; the marker always emits all four slots so the schema validates.
- **`resolve_options`** — options declared without a `prompt:` key are silently defaulted (so `--stack` doesn't interrupt users who want the default).
- **Agent manifests** for all three agents (claude-code, copilot, codex) — added `stack` option.
- **`agent-manifest.schema.json`** — `options.propertyNames` enum extended to include `"stack"`; the `prompt:` key on individual option specs is now optional.
- **`docs/stacks/<id>/` → `cli/stacks/<id>/`** — stack overlays moved under the `cli` package; the wheel ships them automatically.
- **Stack TECH_STACK.md files** — L5-only sections (§4, §4a, §10a, §11 LLM, §11a) stripped from all 5 overlays.
- **L5-only architecture contracts** — `AGENT_ARCHITECTURE.md`, `LLM_GATEWAY_CONTRACT.md`, `GUARDRAILS_CONTRACT.md`, `OBSERVABILITY_LLM_CONTRACT.md`, `EVALUATION_LLM_CONTRACT.md` excluded from L3/L4 installs via `copy_entry(exclude_basenames=...)`.
- **claude-code rules** — `api.md`, `ports.md`, `services.md`, `adapters.md` use `paths_template: layers.<key>` with hexagonal fallback.
- **copilot instructions** — `api.instructions.md`, `ports.instructions.md`, `services.instructions.md`, `adapters.instructions.md` use `applyTo_template: layers.<key>` with hexagonal fallback.
- **claude-code skills** — `architecture-preflight`, `spec-planning`, `implementation-plan`, `adr-author` no longer reference architecture-style folders or stack libraries inline; cite `BOUNDARIES.md` and `skill_context.yaml` instead.
- **CI workflow** ([.github/workflows/test.yml](.github/workflows/test.yml)) — added the self-doctor smoke step (PR 4) and the wheel-smoke job (PR 7).
- **README** — "Switching Tech Stacks" section rewritten around `govkit stack list` / `--stack` / `govkit stack apply`; the `cp docs/stacks/...` recipe is gone.
- **`pyproject.toml`** — dropped the redundant `"cli/stacks" = "cli/stacks"` force-include that caused zipfile duplicate-name warnings during build; cli/stacks/ ships via the `packages = ["cli"]` declaration.

### Removed
- **Old `cp docs/stacks/<id>/*` recipe** from README — superseded by `govkit stack apply`.
- **`docs/stacks/` directory** — moved to `cli/stacks/` (preserves git history via `git mv`).
- **L5-only sections in stack TECH_STACK.md files** — same content remains in `AGENT_ARCHITECTURE.md`, now L5-only.

### Plan amendments honored

This release ships against the 12 amendments captured in [plans/GOVERNANCE_ACCELERATOR_PLAN.md](plans/GOVERNANCE_ACCELERATOR_PLAN.md): A1 (.govkit → directory), A2 (upgrade edit-protection), A3 (single shared `cli/stacks/`), A4 (skill-content rule scoped to vocabulary, not file references), A5 (overlay `version:` for D006), A6 (`calibrated_against_overlay_version`), A7 (D003 warning, not error), A8 (PR 6 split into 6a/6b/6c), A9 (monorepo auto-discovery for doctor + calibrate), A10 (detectors take explicit `target: Path`), A11 (marker schema in `governance/schemas/`), A12 (built-wheel smoke verifies the wheel layout, not the editable install).

### Verification

- 785 pytest tests pass + 1 expected skip (was 440).
- Built wheel installs cleanly into a fresh venv; `govkit stack list` resolves all 6 stacks (5 backend + `python-dbt`) from the wheel layout; `govkit apply --stack dotnet-aspnet` produces a complete install with marker, skill_context, baseline header, review file. `govkit apply --type data` against a dbt fixture detects `dbt` framework + `dbt-shape` architecture and selects the `python-dbt` overlay automatically.
- Doctor on a fresh L4 install of any agent: zero D007 errors (L5 leakage closed); D001/D003 surfaces real mismatches.
- Monorepo fixture (apps/api Python + apps/web TypeScript): doctor + calibrate auto-discover both installs; per-install findings are isolated.

### Upgrade

```bash
pip install --upgrade govkit
```

Existing installs auto-migrate on the next `govkit upgrade` or `govkit validate`:
- `.govkit` (file) → `.govkit/` (directory with `marker.json` + `skill_context.yaml`). One-time stderr warning; suppressible with `GOVKIT_NO_DIRECTORY_MIGRATION_WARNING=1`.
- Governed docs gain the `<!-- govkit:editable baseline: govkit@0.10.0 -->` header on the next overwrite.
- The 5 L5-only contracts are removed from L3/L4 installs on the next `upgrade` (this is intentional — they shouldn't have been there).

For non-L5 installs that want to keep the L5 reference docs locally, copy them out before upgrading or simply re-add them as project-authored files (govkit will leave them alone if they lack the editable header).

To exercise the new commands:

```bash
govkit apply --detect --target .              # see what would be inferred
govkit doctor --target .                       # validate fit
govkit calibrate --target . --non-interactive  # emit the review checklist
govkit stack list                              # see bundled stacks
govkit stack apply dotnet-aspnet --target .    # swap overlays (edit-protected)
```

---

## [0.9.0] — 2026-05-24

### Added — extension pack discovery

Govkit now discovers and validates **self-describing extension packs** placed under `<project>/extensions/<id>/`. Extensions are optional, additive, and live in-place — there is no install command for them. The folder itself *is* the install. Govkit needs no per-extension code changes; new extension types are recognized as soon as their `manifest.yaml` appears in a consuming project.

```text
<project>/
├── docs/
├── governance/
├── features/
├── extensions/
│   └── <extension-id>/
│       ├── manifest.yaml      # self-describing — id, contract_sets, capabilities, agent_guidance
│       ├── docs/
│       └── governance/
└── .govkit
```

### Conflict-resolution model

When an extension contract covers the same topic as a core govkit contract (e.g. an `AGENT_EVALUATION_CONTRACT.md` extension alongside core `EVALUATION_LLM_CONTRACT.md`), the manifest declares the relationship via `relates_to`:

```yaml
contract_sets:
  - id: my_contracts
    paths: [docs/backend/architecture/AGENT_EVALUATION_CONTRACT.md]
    relates_to:
      extends:    [docs/backend/architecture/EVALUATION_LLM_CONTRACT.md]   # both apply; stricter wins
      supersedes: []                                                        # extension replaces core (requires ADR)
```

Undeclared overlap is detected by a filename-topic heuristic and surfaced as a WARN (or FAIL with `--strict`). The architecture-preflight skill reads core contracts first, then extensions, and HALTs for an ADR when an applicable contract conflict isn't declared.

### Added
- **Extension discovery** — `cli/extensions.py` with `discover_extensions`, `load_manifest`, `report_extensions`, `validate_extension`. Discovery returns `[]` when `extensions/` is absent (zero behavior change for non-extension projects).
- **Extension validation in `govkit validate`** — checks required manifest fields, id format, id↔folder name match, `contract_sets[].paths` existence under the extension folder, `templates[].path` existence, `relates_to.{extends,supersedes}` paths existence under project root, and undeclared overlap with core contracts under `docs/backend/architecture/`.
- **`--strict` flag on `govkit validate`** — promotes extension manifest warnings to failures (exit 1). Default mode warns and exits 0 so existing CI pipelines aren't broken by a new extension.
- **Extension discovery in `govkit apply`** — prints an "Extensions detected" summary after the marker write when extensions are present. Silent otherwise.
- **Section 2.6 "Extension Discovery"** added to all 6 `architecture-preflight/SKILL.md` files (claude-code, codex, copilot × backend, ui). Identical content per the agent-parity invariant. Instructs the agent to discover extensions dynamically without hardcoded names, list applicable contracts in the preflight report, and apply the core-first + `relates_to` reading order on conflict.
- **Reference extension `extensions/agentic-skills/`** — reshaped to mirror the core govkit layout (`docs/`, `governance/`). Manifest declares `relates_to.extends` for the 4 core L5 contracts whose topic it overlaps: `EVALUATION_LLM_CONTRACT.md`, `OBSERVABILITY_LLM_CONTRACT.md`, `OBSERVABILITY_PORT_CONTRACT.md`, `GUARDRAILS_CONTRACT.md`.
- **JSON Schema `extensions/agentic-skills/schemas/extension-manifest.schema.json`** — describes the manifest shape (id, name, version, extension_type, contract_sets, templates, agent_guidance, relates_to). Tested in `tests/test_schemas.py`.
- **`scripts/smoke-extensions.ps1`** — end-to-end smoke script covering 8 scenarios: baseline (no extensions/), discovery via apply, valid validate, valid `--strict`, broken contract path (warn vs strict), undeclared overlap, no-extensions regression. Configurable target via `-ProjectPath`.
- **Tests** — 37 new tests across `tests/test_extensions.py`, `tests/test_agent_skills.py`, and extension-related additions to `tests/test_schemas.py` and `tests/test_govkit.py`. Total test count grew from 366 → 440.
- **Documentation** — root README gains an "Extensions" section covering the discovery contract, manifest schema, conflict-resolution model, and a pointer to the reference example.

### Changed
- **PyYAML as runtime dependency** — first runtime dep added to govkit (`pyyaml>=6.0`). Required to parse `manifest.yaml`. `pip install --upgrade govkit` picks it up automatically.
- **`extensions/agentic-skills/` reshape** — templates moved from `templates/backend/agentic/` to `governance/backend/templates/`; manifest paths updated; install model documented as in-place rather than CLI-installed.

### Verification
- 440 pytest tests pass (was 366).
- Smoke script reports 9/9 scenarios PASS against a fresh sandbox.
- Reference `agentic-skills` extension validates cleanly against the live repo (zero issues), pinned by `test_agentic_skills_extension_validates_cleanly_against_repo`.

### Upgrade

```bash
pip install --upgrade govkit
```

Projects that don't use extensions need no other changes. Projects that want to adopt an extension drop the extension folder under `<project>/extensions/<id>/` and re-run `govkit validate` — no `govkit apply` needed for the extension itself.

---

## [0.8.0] — 2026-05-18

### Breaking changes — one install = one project shape

The orthogonal `--type {api,cli}` × `--ui {none,react,angular}` cross-product is gone. The `--type` flag now takes one of **four flat choices**: `api`, `cli`, `ui-react`, `ui-angular`. The `--ui` flag has been **removed entirely**.

| 0.7.0 | 0.8.0 |
|---|---|
| `govkit apply --type api --ui none` | `govkit apply --type api` |
| `govkit apply --type api --ui react` (broken on Claude/Copilot — dead sidecar) | `govkit apply --type ui-react` |
| `govkit apply --type api --ui angular` (broken on Claude/Copilot — dead sidecar) | `govkit apply --type ui-angular` |

### Why the change

The 0.7 cross-product made three project shapes look like four configurations and broke the case it claimed to support. UI guidance landed in `CLAUDE-UI.md` / `.github/copilot-instructions-ui.md` sidecars that neither Claude Code nor Copilot's loaders pick up — UI rules were functionally dead for two of the three agents in fullstack mode. There was also no UI-only install path (`--ui react` always shipped backend rules alongside).

The flat model fixes both: every install is one shape with clean rule isolation, and fullstack monorepos are supported via per-subdir installs (see [docs/MONOREPO_PATTERN.md](docs/MONOREPO_PATTERN.md)).

### What this means for adopters

After upgrading, govkit prints a one-time stderr warning per command invocation when a legacy `.govkit` marker carries the dropped `ui` option. Suppress with `GOVKIT_NO_SHAPE_MIGRATION_WARNING=1` if needed.

**No automated marker migration.** Re-apply with the new flag:

```bash
pip install --upgrade govkit

# UI-only project — replaces a 0.7 `--type api --ui react` install
govkit apply --agent claude-code --type ui-react --target .

# Backend-only project — replaces a 0.7 `--type api --ui none` install
govkit apply --agent claude-code --type api --target .

# Fullstack monorepo — replaces a 0.7 `--type api --ui react` install
govkit apply --agent claude-code --type api      --target apps/api
govkit apply --agent claude-code --type ui-react --target apps/web
```

The 0.7 sidecar files (`CLAUDE-UI.md`, `.github/copilot-instructions-ui.md`, `src/AGENTS.md` from the old cross-product) are no longer written. If they exist in your project from a 0.7 install, delete them after re-applying.

### Changed
- **`--type` choices** — `api`, `cli`, `ui-react`, `ui-angular`. Default is still `api`.
- **`--ui` flag removed** from `govkit apply` argparse. Re-introducing it via custom scripts will error.
- **`--starter` choices** — `backend`, `cli`, `ui-react`, `ui-angular`. The legacy `ui` value is rejected. Both `ui-react` and `ui-angular` map to the framework-agnostic `starter_ui/` directory; if they diverge later, dedicated starter dirs can be added without resolver changes.
- **Skills converged on Open Skills format** — `SKILL.md` frontmatter is now byte-identical across the three agents per skill. `name:` + `description:` only; no `argument-hint:` (Claude Code) or `user-invocable:` (Copilot) extensions; no `$ARGUMENTS` substitution in bodies. The 33 SKILL.md files across `agents/{claude-code,codex,copilot}/skills/**/` are now in lockstep parity.
- **Skill descriptions** include a "Use when…" cue per Open Skills standard — the harness uses this to decide whether to invoke.
- **Progressive loading hardened for UI shapes**:
  - **Claude Code** — UI shapes now plant a consolidated `src/CLAUDE.md` containing component / viewmodel / API / accessibility layer rules. The 0.7 pattern of flat `.claude/rules/{components,viewmodel,ui-api,accessibility}.md` is replaced; Claude's recursive `CLAUDE.md` loader picks up the nested file when working under `src/`.
  - **Codex** — UI shapes add `src/AGENTS.md` as an intermediate subtree map between the root `AGENTS.md` and the per-layer leaf `AGENTS.md` files. Codex's hierarchical loader picks up the right file at each level.
  - **Copilot** — UI instruction `applyTo:` globs are tightened from `**/<layer>/**` to `src/**/<layer>/**` to prevent accidental matching against `node_modules/`, `dist/`, and other non-source paths.
- **CI dispatch is type-aware (`by_type`)** — `variants.ci.{github,azure}` blocks now route per-`--type` value. Backend installs get `l3-quality-gate.yml`; UI installs get the new `l3-ui-quality-gate.yml`. At L5, backend installs get the LLM-specific gates without the UI gates and vice versa (UI installs still get the LLM eval gates because UI features can consume LLM-backed endpoints through the backend).
- **`repo-scope.md` split into backend and UI variants** — `rules/generic/repo-scope-backend.md` references `services/`, `adapters/`, `ports/`; `rules/generic/repo-scope-ui.md` references `src/features/`, `src/shared/` and forbids importing LLM provider SDKs directly. Backend shapes ship the backend variant; UI shapes ship the UI variant. The original `repo-scope.md` is removed.
- **`/architecture-preflight` skill** declares `eval_criteria.yaml` as a third spec input (alongside `nfrs.md` and `acceptance.feature`). The UI variant also gained an explicit Feature specs section.
- **Smoke scripts rewritten** — `smoke.ps1`, `smoke-ui.ps1`, `smoke-dotnet.ps1` drop `--ui none`. `smoke-ui.ps1` uses `--type ui-react`/`--type ui-angular` via a new `-Types` parameter (previously `-Frameworks`). Sandbox features now ship only the 3 spec inputs (`acceptance.feature`, `nfrs.md`, `eval_criteria.yaml`); `plan.md` and `architecture_preflight.md` are intentionally absent so the planning skills can be exercised against the sandbox. L4/L5 validate failures are tolerated by the exit-code logic; only L3 validate must pass.
- **Manifest schema** — `propertyNames` enums on `options` (`["level", "type", "ci"]`) and `variants` (`["type", "ci"]`) actively reject the dropped `ui` dimension. New `by_type` sub-block accepted on `variant_config` and `level_override`.

### Added
- **`docs/MONOREPO_PATTERN.md`** — per-subdir install pattern with per-agent loader specifics (Claude recursive `CLAUDE.md`, Codex hierarchical `AGENTS.md` walk, Copilot `applyTo:` globs with the monorepo-prefix tweak), CI options (path-filtered vs composite), per-app feature governance, upgrade flow, gotchas.
- **6 new L5 UI root files** — `agents/{claude-code,codex,copilot}/{claude-md,agents-md,copilot-instructions}/l5-ui-{react,angular}.md`. Pre-0.8 the L5 UI manifest blocks silently fell back to the L4 UI root file; this is now fixed.
- **2 new L3 UI CI gates** — `ci/{github,azure}/l3-ui-quality-gate.yml`. Mirrors the structure of `l3-quality-gate.yml` but targets the UI toolchain (ESLint with a11y plugin, Vitest/Jest, npm run build, Snyk npm scan).
- **`scripts/smoke-inspect.ps1`** — visual inspection helper for the sandbox matrix. Supports `-Config <name>`, `-Pattern <wildcard>`, `-All` selection; `-Editor explorer|code|tree` output. Tree mode is redirect-safe for baseline capture.
- **`_apply_by_type()` resolver helper** in `cli/govkit.py` — folds `block.by_type[type_value]` into the parent block before merge/replace logic runs. Currently used only by the `ci` dimension; extensible to other dimensions without code changes.
- **`_maybe_warn_shape_migration()`** — one-time stderr warning when a `.govkit` marker carries the legacy `ui` option. Suppressible via `GOVKIT_NO_SHAPE_MIGRATION_WARNING=1`. Mirrors the existing v0.6→v0.7 migration warning pattern.
- **`TestShapeMigrationWarning`, `TestNoUiDimensionInManifests`, `TestValidateUiShapes`** test classes plus 5 by_type dispatch tests in `TestResolveVariantFiles`. Test count grew from 315 to 366 across this release.
- **Schema tests for the new shape** — `test_rejects_options_ui`, `test_rejects_variants_ui`, `test_accepts_new_ui_type_in_choices_and_variants`, `test_accepts_by_type_at_base_and_levels`, `test_rejects_unknown_key_in_by_type_entry`.

### Removed
- **`--ui` flag** from `govkit apply` argparse.
- **`options.ui` and `variants.ui`** from all 3 agent manifests.
- **`rules/generic/repo-scope.md`** and **`instructions/generic/repo-scope.instructions.md`** (Copilot) — superseded by the backend/ui split.
- **Legacy `--starter ui`** option — replaced by `--starter ui-react` / `--starter ui-angular`.
- **`scripts/smoke-ui-new.ps1`** — tactical helper from mid-refactor; its content moved into the rewritten `smoke-ui.ps1`.

### Verification

- 366 pytest tests pass (was 315 pre-refactor).
- Smoke matrix: 36/36 configs apply, all L3 validate PASS, L4/L5 validate FAIL by design.
- Zero cross-shape leakage in either direction (18 backend × 12 UI patterns, 18 UI × 14 backend patterns — all clean).
- Every Claude UI sandbox ships `src/CLAUDE.md`; every Codex UI sandbox has the full nested `AGENTS.md` tree (6 dests); every Copilot UI sandbox carries `applyTo:` globs on every instruction file.

### Support and pinning

- v0.7.x will receive bug-fix-only backports for one minor cycle. Pin with `pip install govkit==0.7.*` if you want to defer the re-apply.
- The full refactor plan and per-increment commit trail are in [plans/PROJECT_SHAPE_REFACTOR_PLAN.md](plans/PROJECT_SHAPE_REFACTOR_PLAN.md).

### Migration commands

```bash
pip install --upgrade govkit

# Backend-only project (was --type api --ui none)
govkit apply --agent <agent> --type api --target /path/to/project

# UI-only project (was --type api --ui react/angular)
govkit apply --agent <agent> --type ui-react --target /path/to/project       # or --type ui-angular

# Fullstack monorepo (was --type api --ui react/angular at repo root)
govkit apply --agent <agent> --type api      --target /path/to/repo/apps/api
govkit apply --agent <agent> --type ui-react --target /path/to/repo/apps/web
```

---

## [0.7.0] — 2026-05-08

### Breaking changes — maturity model reframed

The meaning of Level 3 and Level 4 has changed. **If your project's `.govkit` marker says `level: "3"` or `level: "4"`, please read this section before upgrading.**

| Level | v0.6.x | v0.7.0 |
|---|---|---|
| **L3** | Spec-Driven Development (3 artifacts per feature) | **Governed AI Delivery (Foundations)** — agent rules + architecture docs only; no `features/` directory |
| **L4** | Governed AI Delivery (5 artifacts per feature) | **Spec-Driven Add-On** — adds `features/` and the 5-artifact contract on top of L3 |
| **L5** | GenAI Operations | GenAI Operations *(unchanged)* |

The new model is additive (L4 ⊃ L3) and splits at a clearer boundary: whether your project adopts a `features/` directory model.

### What this means for adopters

After upgrading, govkit prints a one-time stderr migration warning per command invocation until you run `govkit upgrade --migrate-levels`. Suppress with `GOVKIT_NO_MIGRATION_WARNING=1` if needed.

**If your marker says `level: "3"`** (3-artifact features under v0.6.x):

Your project's shape (a `features/` directory with 3-artifact dirs) maps most closely to the new **L4**, but L4 requires 5 artifacts per feature. Run `govkit upgrade --migrate-levels` for an interactive prompt with four options:

1. Migrate to L4 with stub generation — govkit creates `eval_criteria.yaml` and `architecture_preflight.md` stubs in each feature dir; you fill them in over time. Stubs use TBD placeholders that will fail validation until completed.
2. Migrate to L4 without stubs — you author the two new artifacts manually. Validation will fail until you do.
3. Adopt new-L3 (Foundations) — you confirm we should DELETE your `features/` directory and switch to architecture-only governance (no per-feature artifacts).
4. Abort — pin `govkit==0.6.*` in your project until you're ready.

**If your marker says `level: "4"`** (5-artifact features under v0.6.x):

No data migration needed. Your project shape is correct under v0.7.0; only the level label flips from "Governed AI Delivery" to "Spec-Driven Add-On". Run `govkit upgrade --migrate-levels` to clear the migration warning.

**If your marker says `level: "5"`:**

Nothing changes for you. Run `govkit upgrade --migrate-levels` to clear the migration warning.

### Changed
- **CLI default level** — `govkit apply` now defaults to `--level 3` (was `4`). Three agent manifests' `options.level.default` flipped to `"3"`.
- **`govkit init` at L3 errors** — points to `govkit apply --level 4` (Foundations has no `features/` directory model).
- **`govkit validate` at L3 is a no-op** — returns 0 with informational message (Foundations has no per-feature artifacts; CI quality-gate is the L3 compliance surface).
- **`govkit apply --level 3`** — no longer creates an empty `features/` directory in the target.
- **Manifest schema** — `level_3` key removed; `level_4` key added with optional `mode: "merge" | "replace"`. Default mode for `level_4` is `"merge"`; for `level_5` is `"replace"`. The `governed` array property is now formally allowed (previously the schema rejected it despite all live manifests using it — a long-standing schema bug, fixed here).
- **L3 CI gate** (`l3-quality-gate.yml`) rewritten as a lean codebase-wide gate: commit-format, import-linter (architecture boundaries), SonarQube, Snyk. No per-feature artifact checks.
- **Test-first and spec-compliance rules** (`test-first.md`, `spec-compliance.md`) move from L3 to L4. They are still part of the kit; they are now part of the spec-driven add-on (binding rather than recommended).

### Added
- **`govkit upgrade --migrate-levels`** — interactive marker migration for v0.6.x → v0.7.0 maturity model swap.
- **One-time migration warning** — `read_govkit_marker` emits a stderr warning when `version < "0.7.0"`. Suppressible via `GOVKIT_NO_MIGRATION_WARNING=1`. Auto-suppressed once the marker is rewritten to `0.7.0+`.
- **L4 add-on manifest blocks** with `mode: "merge"` semantics — `level_4` entries layer additively over the L3 base, with `dest`-collision resolution preferring the override (used to swap `CLAUDE.md` / `AGENTS.md` / `.github/copilot-instructions.md` between L3 and L4 modes).
- **Twelve new L3 entry-point instruction files** (4 per agent × 3 agents) — Foundations content focused on architecture-aware development without per-feature artifacts. Existing v0.6 governed instructions preserved at `l4-*.md` paths.
- **`tests/test_maturity_model.py`, `tests/test_schemas.py`, `tests/test_l3_instructions.py`** — 200+ new tests locking in the model.

### Removed
- `features/starter_{backend,cli,ui}_l3/` — 3-artifact starters (the new L3 has no `features/` model).
- `governance/{backend,ui}/templates/l3-plan.md` — L3 has no plan.md artifact.
- `agents/<a>/skills/<area>/l3-{spec-planning,implementation-plan}/` — replaced by the L4 add-on skills (which now ship at L4 instead of being level-specific).
- `agents/<a>/<inst>/l3-{backend-api,backend-cli,ui-react,ui-angular}.md` — superseded by the new L3 entry-point files (current top-level paths) and the renamed `l4-*.md` files (preserved L4 content).

### Support and pinning

- v0.6.x will receive bug-fix-only backports through the v0.8.0 release.
- Pin with `pip install govkit==0.6.*` if you want to defer the migration.

### Migration commands

```bash
pip install --upgrade govkit
govkit upgrade --migrate-levels --target /path/to/your/project
```

---

## [0.4.0] — 2026-04-09

### Added
- **Level 5: GenAI Operations** — governed tooling for LLM-powered features
- **Architecture contracts** — LLM_GATEWAY_CONTRACT.md (LiteLLM), OBSERVABILITY_LLM_CONTRACT.md (OpenLLMetry + Langfuse), GUARDRAILS_CONTRACT.md (NeMo + Guardrails AI), EVALUATION_LLM_CONTRACT.md (DeepEval + Promptfoo + RAGAS)
- **Practical guides** — 8 usage guides in `docs/backend/guides/` (one per tool)
- **Guardrails config schema** — `governance/backend/schemas/guardrails_config.schema.json`
- **L5 feature starters** — `starter_backend_l5/`, `starter_cli_l5/` with LLM NFRs, deepeval criteria, L5 preflight sections
- **L5 plan and preflight templates** — extended with LLM gateway, guardrails, and evaluation sections
- **L5 agent rules** — `llm-gateway.md`, `guardrails.md`, `llm-evaluation.md`, `llm-observability.md` (Claude Code + Copilot)
- **L5 agent skills** — `/genai-preflight` (validates L5 architecture decisions), `/eval-suite-planning` (plans DeepEval/Promptfoo/RAGAS suites)
- **L5 CI templates** — `deepeval-gate.yml`, `promptfoo-gate.yml`, `guardrails-check.yml` (GitHub Actions + Azure DevOps)
- **L5 CLAUDE.md variants** — `l5-backend-api.md`, `l5-backend-cli.md`
- **L5 Copilot instruction variants** — `l5-backend-api.md`, `l5-backend-cli.md`
- **L5 validation checks** — `check_llm_nfrs()`, `check_l5_eval_criteria()`, `check_l5_preflight_sections()` (9 total checks at L5)

### Changed
- **eval_criteria.schema.json** — added 11 new eval_class values (deepeval_*, promptfoo_*, ragas_*) and optional `tool` field
- **evaluation_prediction.schema.json** — added optional `llm_evaluation` object for L5 predictions
- **agent-manifest.schema.json** — added `level_5` to variant_config properties
- **TECH_STACK.md** — added sections for LLM Gateway, LLM Evaluation, LLM Observability, Runtime Guardrails
- **AGENT_ARCHITECTURE.md** — updated tool integration, observability, evaluation, added guardrails section
- **EVAL_STACK.md** — replaced LangSmith/Arize with Langfuse, added DeepEval/Promptfoo/RAGAS
- **check_gherkin_nfr_coverage()** — now skips non-standard NFR categories (e.g., LLM-specific)
- **CLI** — `--level` accepts "5", `cmd_init` selects L5 starters, marker version bumped to 0.4.0

---

## [0.3.0] — 2026-04-08

### Added
- **Maturity model** — govkit now supports Level 3 (Spec-Driven Development) and Level 4 (Governed AI Delivery)
- **`--level` flag** — `govkit apply`, `govkit init`, and `govkit validate` accept `--level 3` or `--level 4`
- **`.govkit` marker file** — written after `govkit apply`, tracks level and options for auto-detection by `init` and `validate`
- **Level 3 feature starters** — `starter_backend_l3/`, `starter_cli_l3/`, `starter_ui_l3/` with 3 artifacts (no eval_criteria.yaml, no architecture_preflight.md)
- **Level 3 plan templates** — simplified plan.md without evaluation_prediction blocks
- **Level 3 generic agent rules** — `test-first.md` and `spec-compliance.md` (no path-scoped rules)
- **Level 3 CLAUDE.md variants** — `l3-backend-api.md`, `l3-backend-cli.md`, `l3-ui-react.md`, `l3-ui-angular.md`
- **Level 3 agent skills** — simplified `/spec-planning` and `/implementation-plan` without evaluation scoring
- **Level 3 Copilot equivalents** — L3 copilot-instructions and prompts for all project types
- **Level 3 CI templates** — `l3-quality-gate.yml` for GitHub Actions and Azure DevOps (no eval gates, no boundary checks)
- **Level-aware validation** — `govkit validate` checks 3 artifacts for L3, 5 for L4; skips eval checks at L3
- **Manifest `level_3` sub-key** — variant overrides co-located with parent variants; schema updated

### Changed
- **Manifest schema** — `variant_config` now accepts optional `level_3` override with same shape
- **`resolve_variant_files()`** — respects level selection, uses `level_3` override when level is "3"
- **`run_validation()`** — accepts `level` parameter; auto-detects from `.govkit` marker
- **`check_completeness()`** — parameterized to accept custom artifact list
- **Starter skip list** — includes L3 starters (`starter_backend_l3`, etc.)

---

## [0.2.0] — 2026-04-02

### Added
- **FIRST Scoring Rubric** — concrete 1–5 scoring definitions for each FIRST principle (backend and UI)
- **7 Virtues Scoring Rubric** — concrete 1–5 scoring definitions for each code virtue (backend and UI)
- **Observability Port Contract** — port interface, adapter example, and testing guidance
- **Error Mapping Contract** — domain exception hierarchy and HTTP status mapping
- **Cross-Cutting Concerns** — DTOs, validation boundaries, pagination, timestamps, soft deletes, audit trails, configuration
- **LangGraph vs LangChain decision matrix** in TECH_STACK.md
- **Evaluation prediction schema** — JSON Schema for plan.md prediction blocks
- **Import-linter reference config** — ready-to-merge config for hexagonal architecture enforcement
- **CI governance artifact checks** — jobs to verify architecture preflight exists and commit message format
- **CI README** — documents what's enforced vs predicted vs stubbed vs agent-only
- **README expansion** — prerequisites, concepts, interactive prompt example, post-install verification, troubleshooting, FAQ, glossary, governance structure explanation
- **CONTRIBUTING.md** and **CHANGELOG.md**

### Changed
- **Evaluation prediction format standardized** — UI now uses same `first`/`virtues`/`accessibility` structure as backend
- **UI eval-gate** now checks Virtue scores in addition to FIRST scores (GitHub Actions + Azure DevOps)
- **Copilot prompts enhanced** — added template locations, output paths, scoring rubric references, increment sizing
- **Starter templates** — added mode selection instructions to backend and CLI starters
- **Skill invocation syntax** — corrected `/project:` prefix to `/` in README and all CLAUDE.md variants

### Fixed
- **CLI error handling** — source path validation, UTF-8 encoding, JSON parse error handling, manifest structure validation
- **`cmd_list`** — now skips non-directory entries and handles malformed manifests gracefully

---

## [0.1.0] — 2026-04-01

### Added
- Initial release
- Two agents: `claude-code` and `copilot` with variant-based manifests
- Variant options: `--type` (api/cli), `--ui` (none/react/angular), `--ci` (github/azure)
- CLI: `govkit apply`, `govkit list`, `govkit validate`
- Backend architecture docs: ARCH_CONTRACT, BOUNDARIES, API_CONVENTIONS, CLI_CONVENTIONS, SECURITY_AUTH_PATTERNS, TECH_STACK, TESTING, DESIGN_PRINCIPLES, GHERKIN_CONVENTIONS
- UI architecture docs: MVVM_CONTRACT, COMPONENT_CONVENTIONS, STATE_MANAGEMENT (React + Angular)
- Evaluation standards: eval_criteria.md (backend + UI), EVAL_STACK.md
- Feature starters: starter_backend, starter_cli, starter_ui
- Worked examples: schema_contract_example, ui_task_dashboard
- CI templates: quality-gate, eval-gate, ui-quality-gate, ui-eval-gate (GitHub Actions + Azure DevOps)
- Governance schemas: eval_criteria.schema.json (backend + UI)
