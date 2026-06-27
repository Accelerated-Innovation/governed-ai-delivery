# Governance Accelerator Plan — From Template Library to Calibrated Installer

> **Source of truth for implementation.** This plan supersedes drafts under `~/.claude/plans/`. All PRs referenced below must trace back to a section in this document.

## Amendments Log

Decisions captured after expert review against the codebase. The body of the plan below reflects these decisions; this log exists so a reader can see what changed without diffing.

- **A1 — `.govkit` becomes a directory.** Today `.govkit` is a single JSON file ([cli/govkit.py:198](cli/govkit.py#L198)). It is converted to `.govkit/` containing `marker.json` (today's payload) and `skill_context.yaml`. PR 1 handles the migration via the existing one-time-warning pattern. Old single-file markers are read tolerantly and rewritten on the first command.
- **A2 — `cmd_upgrade` adopts the same edit-protection as `stack apply`.** Today [cmd_upgrade at cli/govkit.py:678-684](cli/govkit.py#L678-L684) overwrites `governed` paths without `skip_existing`. This silently destroys user edits. PR 1 routes both `upgrade` and `stack apply` through the same `govkit:editable` header check + mtime-vs-`applied_at` guard.
- **A3 — Stacks live at `cli/stacks/`, shared by all agents.** Original plan put stacks under `agents/<agent>/stacks/` which would 4x-duplicate identical content (stacks are agent-agnostic). They stay at a single bundled location under the wheel.
- **A4 — Skill-naming rule is scoped to architecture vocabulary, not all references.** Skills MAY reference govkit-installed governance docs (`ARCH_CONTRACT.md`, `API_CONVENTIONS.md`, etc.). Skills MAY NOT name architecture-style folders (`ports/`, `adapters/`, `Controllers/`) or stack libraries (`pytest`, `pydantic`, `xunit`) inline.
- **A5 — Overlay metadata gets a `version:` field.** Doctor's D006 (stale baseline) compares the installed doc's header against the overlay's current `version`. Without this, D006 would fire on every patch release.
- **A6 — Assumptions carry `calibrated_at` and `calibrated_against_overlay_version`.** When a stack overlay version bumps past what the assumption was calibrated against, doctor re-opens `review_required`. Calibration is not permanent.
- **A7 — D003 (CI mismatch) is `warning`, not `error`.** Legitimate repos have a `dependabot.yml` alongside Azure Pipelines. Reserve `error` for things that genuinely block shipping.
- **A8 — PR 6 splits into PR 6a (loader), PR 6b (claude-code skills), PR 6c (copilot + codex + TECH_STACK split).** Original PR 6 spanned ~40 files; that won't survive review. Roadmap is now nine PRs.
- **A9 — Doctor/calibrate handle monorepos by `.govkit/` auto-discovery.** If multiple `.govkit/` directories exist under cwd, doctor prints a per-install summary; `--target <subdir>` scopes to one.
- **A10 — Detectors take an explicit target `Path`.** Avoids monorepo cross-contamination where root contains both `*.csproj` and `package.json` for different sub-apps.
- **A11 — JSON schema for `.govkit/marker.json`** ships in PR 1 under `governance/schemas/` so future schema drift is caught by `test_schemas.py`.
- **A12 — Verification uses a built wheel, not editable install.** `pip install -e .` resolves `AGENTS_DIR` to the source tree, masking the wheel layout. Real verification: `python -m build && pip install dist/govkit-*.whl`.

---

## Context

GovKit today installs a Python / FastAPI / hexagonal baseline regardless of what's in the target repo. Stack overlays exist (`docs/stacks/dotnet-aspnet`, `java-spring-boot`, `nodejs-fastify`, `go-gin`) but are not selectable via the CLI — the README tells users to `cp -r` them by hand. Level 5 (LLM/GenAI) content has leaked into Level 3 baseline docs. Rule globs hardcode hexagonal folder names (`**/ports/**`, `**/adapters/**`, `**/services/**`) that may not exist in the target repo. Skills assume Python idioms (`pydantic`, `pytest-bdd`) and hexagonal layer vocabulary. The result: GovKit can quietly install governance that contradicts the repo, and agents then follow that contradictory guidance.

The product direction is not "ship more variants." It is: **install an opinionated baseline, name every assumption, and guide the team through the small set of files they must review.** Repo inference, validation, and calibration replace exhaustive templating.

This plan reshapes GovKit around four primitives — **Overlay**, **RepoProfile**, **Assumption**, **ValidationFinding** — and three new commands (`stack list`/`stack apply`, `doctor`, `calibrate`), without exploding the template surface area.

---

## Distribution & Agent Scope

These two facts shape the entire architecture below.

### Distribution: GovKit is a PyPI wheel installed via `pip`

- `pip install govkit` puts the package under `site-packages/cli/` with all bundled assets force-included in the wheel (`agents/`, `docs/`, `features/`, `governance/`, `ci/` — see [pyproject.toml](pyproject.toml) `[tool.hatch.build.targets.wheel.force-include]`).
- The user's repo never contains a `docs/stacks/` directory, an `agents/` source tree, or any other GovKit asset folder. Only files that `govkit apply` actively copies (CLAUDE.md, .claude/rules/*, docs/backend/architecture/*, ci/*, etc.) land in the client repo.
- **Stack overlays live inside the wheel at a single shared location: `cli/stacks/<id>/` (with `overlay.yaml` + the 6 stack docs).** Stacks are agent-agnostic — duplicating them per agent would 4x the asset footprint with no benefit. `govkit stack list` enumerates bundled stacks from this path; `govkit stack apply <id>` copies the selected stack's files into `docs/backend/architecture/`. There is nothing to delete in the client repo, no unused variants, no `cp -r` ritual.
- The current README guidance to `cp docs/stacks/<stack>/*` only works for users who git-cloned the repo. Pip users have to dig into `site-packages` to find the stacks — that's the discoverability bug that `--stack` and `govkit stack list` fix.
- Asset resolution already handles both modes: `AGENTS_DIR = _HERE / "agents" if (_HERE / "agents").exists() else _HERE.parent / "agents"` ([cli/govkit.py:138](cli/govkit.py#L138)). The new `STACKS_DIR` resolver follows the same pattern (`_HERE / "stacks"` vs `_HERE.parent / "cli" / "stacks"` for repo-checkout).

### Agent scope: three agent targets, one core engine

GovKit ships three agent adapters: `claude-code`, `copilot`, `codex`. Each has its own manifest, instruction-file convention, and rules location:

| Agent | Top-level entry | Rules / instructions location | Skills location |
|---|---|---|---|
| claude-code | `CLAUDE.md` | `.claude/rules/*.md` | `.claude/skills/<name>/` |
| copilot | `.github/copilot-instructions.md` | `.github/instructions/*.instructions.md` | `.github/skills/<name>/` |
| codex | `AGENTS.md` (root + nested per layer) | nested `AGENTS.md` per layer | `.agents/skills/<name>/SKILL.md` |

**Agent-agnostic (build once, applies to all three):**
- CLI surface: `apply`, `stack list`, `stack apply`, `doctor`, `calibrate`, `validate`
- `.govkit` schema and `GOVKIT_SETUP_REVIEW.md` generation
- `RepoProfile` detectors and `Assumption` model
- Doctor findings D003–D012 (most checks)
- `.govkit/skill_context.yaml` writer
- Overlay loader and `overlay.yaml` schema

**Per-agent (touched in PR 2 and PR 6 for all three):**
- Manifest changes: `stack` option added to [agents/claude-code/manifest.json](agents/claude-code/manifest.json), [agents/copilot/manifest.json](agents/copilot/manifest.json), [agents/codex/manifest.json](agents/codex/manifest.json)
- Doctor check D001 (rule-glob): agent-aware — scans `.claude/rules/` for claude-code, `.github/instructions/` for copilot, nested `AGENTS.md` for codex
- Skill externalization: each agent's skill tree gets audited and rewritten to read `.govkit/skill_context.yaml` instead of hardcoding hexagonal vocabulary
- Rule/instruction templates: glob patterns and folder references swapped for values pulled from skill context

**Agent limitations the plan respects:**
- Copilot's `applyTo:` globs (monorepo prefix tweak already documented)
- Codex's directory-walk loader (nested AGENTS.md concatenation)
- Claude-code's recursive CLAUDE.md discovery (subpath governance)

The four primitives and three commands ship once. Per-agent surfaces are mechanical translations of the same source-of-truth data.

---

## Extensions Compatibility

The existing extension system ([cli/extensions.py](cli/extensions.py), `extensions/agentic-skills/manifest.yaml`) is preserved and elevated, not replaced.

**How extensions work today** — extensions live in the client repo at `<target>/extensions/<id>/manifest.yaml`. They are user-authored, in-place ("the in-repo folder *is* the install"), and surfaced by `report_extensions(target)` at the end of `govkit apply`. Each extension declares `contract_sets[].paths`, `applies_to[]` globs, `capabilities[]`, `relates_to.extends|supersedes`, and per-skill `agent_guidance` blocks. The bundled `extensions/agentic-skills/` in the GovKit repo is a reference example users can copy into their own repo — it is not installed by the CLI.

**What changes in this plan:**

- **Skill context absorbs extension capabilities.** `.govkit/skill_context.yaml` (Section 4) gains an `extensions:` block listing each discovered extension's id, version, and capabilities. Skills already read extension `agent_guidance` today; the new helper `load_skill_context()` exposes both stack/architecture facts *and* extension data through one entry point so skills don't have to call `discover_extensions()` directly.
- **Extensions can declare assumptions.** `Assumption.source` gains `"extension"` as a valid value. When an extension declares a capability (e.g. `agent-runtime`, `background-agents`), `apply` records an assumption with `source: "extension"` and `evidence: ["extensions/<id>/manifest.yaml"]`. Doctor uses this to suppress mismatch warnings that the extension legitimately covers.
- **Doctor validates extensions but doesn't second-guess them.** Two new checks (D013, D014) verify that declared extension files exist and that `relates_to.extends` files are present. Doctor does **not** flag extension contract files as "missing baseline" — they have no `govkit:editable` header because they are user-authored, not installed by GovKit.
- **`stack apply` never touches extension files.** Stack overlays copy exactly 6 files into `docs/backend/architecture/`. Extension contract files in the same directory (e.g. `AGENT_RUNTIME_CONTRACT.md`) are not in the overlay manifest, so they are untouched. The doc-header strategy makes this explicit: only files with `govkit:editable` are managed by GovKit.
- **`calibrate` Step 9 confirms extensions.** Skill-context review surfaces any discovered extension and asks the team to confirm its capabilities are intentional (rather than orphaned from a removed feature).
- **Wheel layout unchanged for extensions.** The bundled `extensions/agentic-skills/` reference stays in the GovKit repo for documentation/example purposes; it is not force-included into the wheel because extensions are not installed by the CLI. Users copy or model after the reference manually, as the README already documents.

**What stays the same:** the manifest schema, discovery rules, path-safety checks, `extensions/` directory layout in client repos, and the existing 681 lines of extension tests. No breaking changes to `cli/extensions.py`'s public API.

---

## 1. Executive Recommendation

GovKit should evolve from a **template installer** into a **calibrated governance accelerator** that does four things on every install:

1. **Install a baseline** chosen by the user (or inferred) — small, opinionated, never claiming to fit perfectly.
2. **Declare its assumptions** — write a `GOVKIT_SETUP_REVIEW.md` and extend `.govkit` with an `assumptions[]` block listing every load-bearing choice, its source (`flag`, `default`, `detected`, `prompted`), confidence, and the files affected.
3. **Validate fit** — `govkit doctor` checks installed rules/docs/CI against repo signals and reports mismatches as findings with severities.
4. **Guide adaptation** — `govkit calibrate` walks the team through the editable docs (TECH_STACK, BOUNDARIES, API_CONVENTIONS, TESTING, CLAUDE.md, .claude/rules) with repo-derived suggestions, recording the team's decisions back into `.govkit`.

Skills stop hardcoding architecture vocabulary. Instead, every skill begins by reading installed governance (`docs/<area>/architecture/*.md`, `.govkit`) and a small **skill-context** block generated at install time. One architecture-preflight skill works for hexagonal, layered, clean, vertical-slice, or modular-monolith repos — because the architecture facts live in the installed docs, not the skill.

The success metric is not "GovKit ships every stack." It is: **after `govkit apply` followed by `govkit doctor` and `govkit calibrate`, the team has a coherent governance posture they understand, with no silent assumptions and no rules pointing at folders that don't exist.**

---

## 2. Current-State Findings (Highest-Risk Hardcoded Assumptions)

Ranked by severity. File paths verified during exploration.

| # | Assumption | Where | Risk |
|---|---|---|---|
| 1 | **Python / FastAPI / pydantic / pytest as L3 baseline** | [docs/backend/architecture/TECH_STACK.md:11-23,57-79,211-230](docs/backend/architecture/TECH_STACK.md#L11-L230) | Installed verbatim into every repo regardless of stack. README at [README.md:582-584](README.md#L582-L584) names Python/FastAPI the default. |
| 2 | **Hexagonal vocabulary baked into baseline docs** | [docs/backend/architecture/TECH_STACK.md:27-38](docs/backend/architecture/TECH_STACK.md#L27-L38), `BOUNDARIES.md:7-14` | `api/ ports/ services/ adapters/ common/` declared as the architecture for every L3 install. Teams using layered, clean, or vertical-slice will see contradictory guidance. |
| 3 | **L5 (LLM) content in L3 TECH_STACK** | TECH_STACK.md §4 "Agent Frameworks", §4a "LLM Gateway", §10a, §11 LLM Observability, §11a Guardrails (LangGraph, LiteLLM, NeMo Guardrails, Guardrails AI, OpenLLMetry, Langfuse, DeepEval, Promptfoo, RAGAS) | Non-LLM services get LLM rules they will never honor. Sections are tagged "(Level 5)" but the file ships at L3. |
| 4 | **Rule globs assume hexagonal folders** | [agents/claude-code/rules/backend/adapters.md](agents/claude-code/rules/backend/adapters.md), `ports.md`, `services.md`, `api.md`, `security.md` — globs like `**/adapters/**`, `**/ports/**` | Rules fire on folder match. If repo uses `Controllers/`, `Application/`, `Infrastructure/`, the rules never trigger and offer no guidance. Same pattern in copilot `.github/instructions/` and codex nested `AGENTS.md`. |
| 5 | **No `--stack` flag** | [cli/govkit.py](cli/govkit.py) `resolve_options`, all three agent manifests (only `level`, `type`, `ci`) | Stack selection is manual `cp -r` against bundled wheel assets. Pip users can't discover the stacks dir; non-Python teams silently get Python docs. |
| 6 | **SpecFlow / pytest-bdd as L4 hard requirement** | L4 CLAUDE.md "Gherkin scenarios... must be complete", stack overlays' `TESTING.md` (dotnet-aspnet → SpecFlow; default Python → pytest-bdd) | Teams without BDD discipline cannot satisfy L4 and have no escape hatch. |
| 7 | **GitHub Actions wording in shared content** | Mixed: CI selection is correct (`ci/github` vs `ci/azure`), but doc snippets reference `.github/workflows/` outside the CI templates ([TECH_STACK.md:260](docs/backend/architecture/TECH_STACK.md#L260)) | Azure DevOps installs still get GitHub-flavored doc text. |
| 8 | **`features/<name>/` artifact gate as L4 contract** | L4 CLAUDE.md, `spec-compliance.md` rule | Reasonable default but currently un-opt-out-able; should be declared assumption, not invariant. |
| 9 | **Skill files hardcode hexagonal terms** | `skills/backend/architecture-preflight/`, `spec-planning/`, `implementation-plan/`, `adr-author/` — duplicated across all three agent trees | Skills say "ports," "adapters," "outbound port" inline rather than reading architecture from installed docs. |
| 10 | **Stack overlays only cover backend** | `docs/stacks/<stack>/` is 6 backend files; no UI/CLI overlays | Acceptable for now — should NOT be expanded into a matrix. |

**Pattern across all 10:** assumptions are *implicit* (baked into ship-once-and-forget templates) rather than *explicit* (declared in `.govkit`, surfaced in a review checklist, and validated by `doctor`).

---

## 3. Proposed Command Model

Five commands total (three new, two reshaped). Names match user-supplied vocabulary. All commands apply uniformly to all three agents — agent-specific behavior lives in the manifest/overlay loaders.

### `govkit apply` (reshaped)

New flags:
```
--stack <id>             dotnet-aspnet | java-spring-boot | nodejs-fastify | go-gin | python-fastapi | none
--detect                 run repo inference, print proposed config, exit 0 without writing
--non-interactive        do not prompt; fail if required options missing (for CI)
--review-only            print what would be installed plus assumptions; no writes
```

Behavior changes:
- Always runs repo inference first; prints `detected:` lines before installing.
- If `--stack` omitted and inference is confident, uses the detected stack and says so. If inference is low-confidence, prompts (or fails in `--non-interactive`).
- After install, writes `GOVKIT_SETUP_REVIEW.md` and an extended `.govkit` with `assumptions[]`.
- Prints a post-install **Review Checklist** referencing the exact files the team must read.
- Existing edited-doc protection: governed/shared still skip-existing; new check warns if user-edited file diverges from baseline.

### `govkit stack list` (new)

Lists available stack overlays bundled inside the installed govkit wheel (resolved via `AGENTS_DIR` / `cli/docs/stacks/`). One-liner per stack: id, display name, summary. No network access; works fully offline.

### `govkit stack apply <stack>` (new)

Re-applies stack-scoped docs over an existing install. Refuses without `.govkit` present. Copies only the selected stack's 6 files from the bundled wheel into `docs/backend/architecture/`. Updates `.govkit.stack` and `assumptions[]`. Same edit-protection rules as `apply`.

### `govkit doctor` (new)

Read-only validation pass. Loads `.govkit/marker.json`, builds a `RepoProfile`, runs detectors, emits `ValidationFinding`s grouped by severity (`error`, `warning`, `info`). Non-zero exit on `error`. Designed to run in CI. Detects active agent from `marker.agent` so D001 (rule-glob) checks the right rules tree.

**Monorepo behavior (per A9):** if no `--target` is given and the cwd contains a `.govkit/` directory, doctor scopes to cwd. If no `.govkit/` is found at cwd but ≥1 exists under cwd (e.g. `apps/api/.govkit/`, `apps/web/.govkit/`), doctor enumerates each install and prints a per-install summary. `--target <subdir>` always scopes to one install. Exit code is non-zero if any install reports an error.

### `govkit calibrate` (new)

Interactive (with `--non-interactive` for scripted runs that emit a checklist file). Walks the team through the small set of editable docs, pre-filling suggestions from `RepoProfile`. Writes/updates `GOVKIT_SETUP_REVIEW.md` and `.govkit/marker.json` (`calibration.decisions[]` plus each addressed assumption's `calibrated_at` and `calibrated_against_overlay_version`).

Monorepo behavior matches doctor (per A9): auto-discover or `--target <subdir>`.

### `govkit validate` (unchanged)

Continues to validate feature artifacts against schemas. `doctor` covers governance fit; `validate` covers per-feature compliance. Two separate concerns, kept separate.

---

## 4. Proposed Data Model

### `.govkit/` directory layout (per A1)

`.govkit` becomes a directory in PR 1. Migration is one-way and one-time:

```
<target>/.govkit/
  marker.json          ← today's .govkit file payload, schema-validated
  skill_context.yaml   ← see "Skill context model" below
```

**Migration behavior** (extends [_maybe_warn_migration at cli/govkit.py:69](cli/govkit.py#L69)):
- If `<target>/.govkit` is a **file** (legacy single-file marker), read it, create `<target>/.govkit/` as a directory, write `marker.json` with the original payload (and any new fields), delete the old file. Emit a one-time stderr warning suppressible via `GOVKIT_NO_DIRECTORY_MIGRATION_WARNING=1`.
- If `<target>/.govkit` is already a directory, proceed normally.
- All read paths (`read_govkit_marker`, `read_govkit_level`) tolerate both layouts during the transition window. Write paths only emit the directory layout.

A JSON schema for `marker.json` ships in PR 1 at `governance/schemas/govkit_marker.schema.json` and is exercised by `test_schemas.py`.

### `marker.json` (extended)

```json
{
  "version": "0.10.0",
  "agent": "claude-code",
  "level": "4",
  "options": { "type": "api", "ci": "azure", "stack": "dotnet-aspnet" },
  "applied_at": "2026-05-27T15:00:00Z",
  "stack": {
    "id": "dotnet-aspnet",
    "version": "0.10.0",
    "display_name": "C# 12 / .NET 8 / ASP.NET Core",
    "applied_at": "2026-05-27T15:00:00Z"
  },
  "assumptions": [
    {
      "id": "stack.language",
      "value": "csharp",
      "source": "detected",
      "confidence": "high",
      "evidence": ["*.csproj", "global.json"],
      "files_affected": ["docs/backend/architecture/TECH_STACK.md"],
      "review_required": false
    },
    {
      "id": "architecture.style",
      "value": "hexagonal",
      "source": "default",
      "confidence": "low",
      "evidence": [],
      "files_affected": ["docs/backend/architecture/BOUNDARIES.md", ".claude/rules/ports.md", ".claude/rules/adapters.md"],
      "review_required": true,
      "calibrated_at": null,
      "calibrated_against_overlay_version": null,
      "warning_message": "Hexagonal layout assumed; no ports/ or adapters/ folder detected. Run `govkit calibrate` to pick layered, clean, or vertical-slice."
    },
    {
      "id": "ci.platform",
      "value": "azure",
      "source": "flag",
      "confidence": "high",
      "evidence": ["azure-pipelines.yml"],
      "files_affected": ["ci/azure/*.yml"],
      "review_required": false
    }
  ],
  "calibration": {
    "completed_at": null,
    "decisions": []
  }
}
```

### Overlay metadata (`overlay.yaml` per stack — shipped at `cli/stacks/<id>/`)

```yaml
id: dotnet-aspnet
version: "0.10.0"           # bumps when the overlay's docs change in a way that warrants user re-review (per A5)
display_name: "C# 12 / .NET 8 / ASP.NET Core Minimal APIs"
summary: "Minimal APIs, xUnit, optional SpecFlow for L4 BDD"
default_assumptions:
  - id: stack.language
    value: csharp
  - id: stack.framework
    value: aspnet-core
  - id: testing.unit
    value: xunit
  - id: testing.bdd
    value: specflow
    review_required: true   # L4 BDD is optional discipline
docs:
  - src: TECH_STACK.md
    dest: docs/backend/architecture/TECH_STACK.md
    editable: true
  - src: TESTING.md
    dest: docs/backend/architecture/TESTING.md
    editable: true
rule_templates: []   # stacks do not ship rules; agent adapter does
skill_context:
  language: csharp
  unit_test_framework: xunit
  package_files: ["*.csproj", "Directory.Packages.props"]
  source_folder_hint: ["src/", "Source/"]
review_checklist:
  - "Confirm target framework (net8.0 / net9.0) in TECH_STACK.md §1"
  - "Confirm SpecFlow vs Reqnroll (SpecFlow successor) in TESTING.md"
  - "If repo uses clean/layered structure, update BOUNDARIES.md and run `govkit doctor`"
```

### `RepoProfile` (built fresh on each `doctor`/`apply`/`calibrate`)

Detector signature (per A10): `def build_profile(target: Path) -> RepoProfile:` — always takes an explicit target so monorepo subdirs don't cross-contaminate (e.g., root containing both `apps/api/*.csproj` and `apps/web/package.json` for different shapes). Never walk from cwd.

```python
@dataclass
class RepoProfile:
    target: Path                                  # the install path the profile describes
    detected_languages: list[Language]            # csharp, python, typescript, ...
    detected_frameworks: list[Framework]          # fastapi, aspnet-core, spring-boot, ...
    detected_ci: list[CI]                         # github-actions, azure-pipelines, ...
    detected_test_packages: list[str]             # xunit, pytest, jest, ...
    detected_project_paths: list[Path]            # *.csproj, pyproject.toml, package.json
    detected_api_style: ApiStyle | None           # rest, graphql, grpc, none
    detected_llm_signals: list[str]               # litellm, openai-sdk, langchain, anthropic-sdk
    detected_architecture_signals: list[str]      # ports/, adapters/, Controllers/, Application/
```

**Parser notes for csproj** (per R3): use `xml.etree.ElementTree` from the stdlib — never regex. PackageReference scanning must handle both `<PackageReference Include="..." Version="..." />` and CPM-style `Directory.Packages.props` where versions live elsewhere. The `aspnet-core` signal looks for `<FrameworkReference Include="Microsoft.AspNetCore.App" />` or `<Project Sdk="Microsoft.NET.Sdk.Web">` — not a substring match against `Microsoft.AspNetCore.*` which would false-positive on `AuthenticationCore`.

Inference signals (deliberately small):

| Signal | Evidence |
|---|---|
| `csharp` | `*.csproj`, `*.sln`, `global.json`, `Directory.Packages.props` |
| `python` | `pyproject.toml`, `setup.py`, `requirements*.txt` |
| `typescript` | `tsconfig.json`, `package.json` + `typescript` dep |
| `go` | `go.mod` |
| `java/kotlin` | `pom.xml`, `build.gradle`, `build.gradle.kts` |
| `aspnet-core` | `Microsoft.AspNetCore.App` framework ref in csproj |
| `fastapi` | `fastapi` in pyproject/requirements |
| `github-actions` | `.github/workflows/*.yml` |
| `azure-pipelines` | `azure-pipelines.yml`, `.azure/`, `pipelines/*.yml` |
| `hexagonal-shape` | folders matching `ports`, `adapters` (any depth) |
| `layered-shape` | folders matching `Controllers`, `Services`, `Repositories` |
| `clean-shape` | folders matching `Application`, `Domain`, `Infrastructure`, `Presentation` |
| `llm-signal` | imports/deps of `langchain`, `litellm`, `openai`, `anthropic`, `semantic-kernel` |

Detection is best-effort. **Confidence is reported, not asserted.**

### `Assumption` and `ValidationFinding`

```python
@dataclass
class Assumption:
    id: str                      # "stack.language", "architecture.style", "ci.platform", "testing.bdd", "extension.<id>.<capability>"
    value: str
    source: Literal["flag", "default", "detected", "prompted", "extension"]
    confidence: Literal["high", "medium", "low"]
    evidence: list[str]
    files_affected: list[str]
    review_required: bool
    warning_message: str | None
    # Per A6: track when the team last calibrated and against which overlay version.
    # Doctor re-opens review_required when the installed overlay version > calibrated_against_overlay_version.
    calibrated_at: str | None                       # ISO8601 timestamp or null
    calibrated_against_overlay_version: str | None  # e.g. "0.10.0" or null

@dataclass
class ValidationFinding:
    severity: Literal["error", "warning", "info"]
    category: str                # "rule-glob", "ci-mismatch", "level-leakage", "stack-mismatch"
    file: str | None
    message: str
    suggested_action: str
```

### Doc header strategy (editable baselines)

Every installed doc gets a top header:

```markdown
<!-- govkit:editable
  baseline: dotnet-aspnet@0.10.0
  reason: Stack-specific tech baseline. Edit freely; doctor will warn on contradictions.
  see: GOVKIT_SETUP_REVIEW.md
-->
```

`doctor` parses this header to: (a) know which baseline a file came from, (b) detect when a file's `baseline` is stale, (c) preserve team edits during `stack apply`.

### Skill context model

At install, GovKit writes `.govkit/skill_context.yaml` (alongside `marker.json` in the `.govkit/` directory — see "`.govkit/` directory layout" above):

```yaml
architecture:
  style: hexagonal           # or layered | clean | vertical-slice | unknown
  source_root: src/
  layers:
    inbound: ["api/", "Controllers/"]
    outbound: ["adapters/", "Infrastructure/"]
    domain:   ["services/", "Application/"]
stack:
  language: python
  api_framework: fastapi
  unit_test: pytest
  bdd_test: pytest-bdd       # or specflow | reqnroll | none
ci: github-actions
llm: false
extensions:
  - id: agentic-skills
    version: 0.1.0
    capabilities:
      - agent-runtime
      - agent-skills
      - background-agents
      - human-approval
    contract_paths:
      - docs/backend/architecture/AGENT_RUNTIME_CONTRACT.md
      - docs/backend/architecture/AGENT_SKILL_PACKAGE_CONTRACT.md
```

All three agents' skills read this file via a single shared helper (`load_skill_context()`) and template their guidance accordingly. The `extensions:` block is populated from `discover_extensions(target)` ([cli/extensions.py](cli/extensions.py)) at install time so skills get one entry point to both stack facts and extension capabilities.

**Skill-content rule (per A4):** skills MAY reference govkit-installed governance docs (e.g. `docs/backend/architecture/BOUNDARIES.md`, `ARCH_CONTRACT.md`, `API_CONVENTIONS.md`, `SECURITY_AUTH_PATTERNS.md`) and extension-discovery primitives. Skills MAY NOT name architecture-style folders (`ports/`, `adapters/`, `Controllers/`, `Application/`, `Infrastructure/`) or stack-specific libraries (`pytest`, `pydantic`, `xunit`, `SpecFlow`, `FastAPI`) inline. When a skill needs to reason about layers or frameworks, it reads from `skill_context.yaml` or the installed governance doc — never from a hardcoded string in the skill body.

---

## 5. Proposed Install Flow (before / after)

### Before

```
$ govkit apply --agent claude-code --level 4 --type api --target .
... copies python-flavored docs into a .NET repo, no warnings ...
... writes .claude/rules/ports.md pointing at non-existent ports/ folder ...
... user reads CLAUDE.md, follows Python guidance, opens PR with pydantic imports in a C# project ...
```

### After (existing .NET repo, stack inferred)

```
$ govkit apply --agent claude-code --level 4 --type api --target .

  detecting repo profile...
    [high]   language       csharp           (evidence: 3x *.csproj, global.json)
    [high]   framework      aspnet-core      (evidence: Microsoft.AspNetCore.App)
    [high]   ci             azure-pipelines  (evidence: azure-pipelines.yml)
    [medium] architecture   clean            (evidence: Application/, Domain/, Infrastructure/)
    [low]    llm            none             (no LLM SDK detected)

  proposing config:
    stack:  dotnet-aspnet   (detected, overriding default python-fastapi)
    ci:     azure           (detected; would have overridden --ci flag if given)
    level:  4               (from --level)
    type:   api             (from --type)

  proceed? [Y/n]: y

  installing baseline + dotnet-aspnet overlay...
    copied  CLAUDE.md
    copied  .claude/rules/api.md
    copied  docs/backend/architecture/TECH_STACK.md
    copied  docs/backend/architecture/TESTING.md         (from dotnet-aspnet overlay)
    copied  ci/azure/l3-quality-gate.yml
    ...

  .govkit marker written (level 4, stack dotnet-aspnet, govkit 0.10.0)
  GOVKIT_SETUP_REVIEW.md written

  -----------------------------------------------------------------------------
  REVIEW CHECKLIST — please read before relying on installed governance:
  -----------------------------------------------------------------------------
    1. docs/backend/architecture/TECH_STACK.md
         Confirm .NET version (net8.0 vs net9.0) and approved NuGet packages.
    2. docs/backend/architecture/BOUNDARIES.md
         Detected 'clean' architecture but installed hexagonal vocabulary.
         Edit layer names to match Application/Domain/Infrastructure, or run
         `govkit calibrate` to swap the architecture model.
    3. docs/backend/architecture/TESTING.md
         BDD framework default is SpecFlow. If using Reqnroll or no BDD,
         update this file and re-run `govkit doctor`.
    4. .claude/rules/
         Rule globs (`**/adapters/**`, `**/ports/**`) do not match this repo's
         layout. Run `govkit doctor` to see specific mismatches.

  Next steps:
    govkit doctor        validate fit and surface mismatches
    govkit calibrate     guided review of the docs above
  -----------------------------------------------------------------------------
```

### After (CI / non-interactive)

```
$ govkit apply --agent claude-code --level 4 --type api \
    --stack dotnet-aspnet --ci azure --non-interactive --target .

  applied: stack=dotnet-aspnet level=4 type=api ci=azure
  assumptions: 4 declared, 2 require review (see GOVKIT_SETUP_REVIEW.md)
  warnings: 0
  errors:   0
```

---

## 6. Proposed Doctor Checks

`govkit doctor` runs the checks below. Each produces zero or more `ValidationFinding`s. Severity = `error` exits non-zero; `warning`/`info` exit zero.

| ID | Severity | Category | What it checks |
|---|---|---|---|
| `D001` | error | rule-glob | Every `globs:` (claude-code `.claude/rules/`, copilot `.github/instructions/`, codex nested `AGENTS.md`) resolves to ≥ 1 file in the repo. Agent target read from `.govkit.agent`. |
| `D002` | warning | rule-glob | Rule mentions a folder name (e.g. `ports/`) not present in repo. |
| `D003` | warning | ci-mismatch | `.govkit.options.ci == "azure"` but `.github/workflows/` files added since install (per A7 — downgraded from error; many repos legitimately have a `dependabot.yml` alongside a non-GitHub CI). |
| `D004` | warning | ci-mismatch | Both `.github/workflows/` quality-gate files and `azure-pipelines.yml` build pipelines exist; ambiguous CI for govkit gates. |
| `D005` | warning | stack-mismatch | Detected language differs from `.govkit.stack` declaration. |
| `D006` | warning | stack-mismatch | Installed `TECH_STACK.md` baseline header is stale vs current overlay version. |
| `D007` | warning | level-leakage | LLM-named sections (`LiteLLM`, `Guardrails`, `DeepEval`) present in non-L5 install. |
| `D008` | info | level-leakage | L5 install with no detected LLM SDK in deps. |
| `D009` | warning | testing | TESTING.md names a framework (`pytest`/`xunit`/`specflow`) not in dep manifest. |
| `D010` | warning | assumption | Any `assumption.review_required: true` is still in `.govkit` after 30 days without a calibration entry. |
| `D011` | error | manifest | `.govkit` references files that no longer exist (deleted by user without `calibrate`). |
| `D012` | info | architecture | Skill context `architecture.style` does not match detected `architecture_signals`. |
| `D013` | error | extension | An extension's `contract_sets[].paths` references a file that doesn't exist in the repo. Delegates to existing `cli/extensions.py` validation. |
| `D014` | warning | extension | An extension's `relates_to.extends` file is missing — the extension references a baseline contract that isn't installed. |

Sample output:

```
$ govkit doctor

  reading .govkit ... ok (level 4, stack dotnet-aspnet, agent claude-code, age 12d)
  building repo profile ... ok

  ERRORS (2):
    D001  .claude/rules/ports.md
          globs `**/ports/**` resolves to 0 files in this repo
          fix: edit ports.md `globs:` to match your inbound-port folders
               (suggestion: src/Application/Abstractions/**) — or remove the rule
    D001  .claude/rules/adapters.md
          globs `**/adapters/**` resolves to 0 files
          fix: change to src/Infrastructure/** — or remove

  WARNINGS (3):
    D002  .claude/rules/services.md
          rule body references "domain services" folder — none found
          fix: review services.md and update folder references
    D006  docs/backend/architecture/TECH_STACK.md
          baseline header says python-fastapi@0.9.0, installed stack is dotnet-aspnet
          fix: run `govkit stack apply dotnet-aspnet` to refresh
               (warning: will overwrite — review GOVKIT_SETUP_REVIEW.md first)
    D007  docs/backend/architecture/TECH_STACK.md
          contains L5-only sections (§4a LiteLLM, §10a, §11a) in an L4 install
          fix: remove or move to a separate AGENT_ARCHITECTURE.md and run `govkit calibrate`

  INFO (1):
    D010  GOVKIT_SETUP_REVIEW.md
          2 assumptions marked `review_required: true` have not been resolved (12d)
          fix: run `govkit calibrate`

  exit: 1 (errors present)
```

---

## 7. Proposed Calibration Checklist

`govkit calibrate` walks these files in order. For each, it shows: (a) what's installed, (b) what's detected, (c) what to confirm. Decisions are recorded in `.govkit.calibration.decisions[]` with timestamp and user.

| Step | File | What the review covers | Pre-filled from |
|---|---|---|---|
| 1 | `.govkit` | Confirm agent / level / type / stack / ci. Allow stack swap. | Inference |
| 2 | `docs/<area>/architecture/TECH_STACK.md` | Language version, frameworks, persistence, messaging, observability. Strip L5 sections if not L5. | Stack overlay + deps |
| 3 | `docs/<area>/architecture/BOUNDARIES.md` | Architecture style (hexagonal / layered / clean / vertical-slice / modular-monolith / unknown). Layer names + folder mappings. | `architecture_signals` |
| 4 | `docs/<area>/architecture/API_CONVENTIONS.md` | Route style (REST/GraphQL/gRPC). Versioning policy. Error envelope format. | `api_style` |
| 5 | `docs/<area>/architecture/TESTING.md` | Unit framework, mocking lib, BDD framework (or `none` to disable L4 BDD gate). | Stack overlay + deps |
| 6 | `CLAUDE.md` / `.github/copilot-instructions.md` / `AGENTS.md` (per agent) | Top-level agent guidance; confirm references to architecture docs are accurate. | Step 3 results |
| 7 | `.claude/rules/*` / `.github/instructions/*` / nested `AGENTS.md` (per agent) | For each rule: confirm `globs:` resolves; optionally regenerate from `skill_context`. | `RepoProfile` |
| 8 | `ci/<platform>/*.yml` | Confirm gate selection matches team practice; allow disabling per-gate. | `ci.platform` |
| 9 | Skill context (`.govkit/skill_context.yaml`) + discovered extensions | Final review of injected facts skills will read; confirm each discovered extension under `<target>/extensions/` is intentional. | Steps 2–5, `discover_extensions()` |

Output: rewrites `GOVKIT_SETUP_REVIEW.md` with each decision and a "calibrated_at" timestamp, sets each addressed assumption's `review_required: false`, and prints next-step suggestions (typically `govkit doctor`).

`--non-interactive` mode emits the same checklist as a markdown todo file without prompting — useful for CI bootstraps and for new repos where the team will fill it in later.

---

## 8. Implementation Roadmap (Nine PRs)

Sized for incremental review. Each PR ships with tests. Every PR ships a new patch version to PyPI; the wheel is the only distribution artifact.

### PR 1 — `.govkit/` directory migration, doc headers, GOVKIT_SETUP_REVIEW.md, edit-protection
Bundles A1, A2, A11 because they share the marker/copy code paths and would be expensive to split.
- **Convert `.govkit` from file to directory** (per A1). Add `_maybe_warn_directory_migration` following the existing one-time-warning pattern at [cli/govkit.py:69](cli/govkit.py#L69). Auto-migrate legacy single-file markers on first read.
- Add `governance/schemas/govkit_marker.schema.json` and wire into `test_schemas.py` (per A11).
- Add `govkit:editable` header block writer (with `baseline: <id>@<version>` line per A5); apply to all governed/shared docs as they are copied.
- **Edit-protection in both `apply` and `upgrade`** (per A2): before overwriting any file with a `govkit:editable` header where mtime > `marker.applied_at`, refuse without `--force` and print a diff summary. `cmd_upgrade` ([cli/govkit.py:678-684](cli/govkit.py#L678-L684)) currently overwrites `governed` paths unconditionally; this PR routes both commands through the new guard.
- Generate `GOVKIT_SETUP_REVIEW.md` at end of `apply` and `upgrade`.
- Extend `marker.json` schema with `assumptions[]` and `stack{}` (back-compat read).
- Print post-install Review Checklist.
- **No new commands.** All behavior is additive or strictly safer than today.

### PR 2 — Overlay metadata + first-class `--stack`
- Add `cli/stacks/<id>/overlay.yaml` schema + loader (per A3 — single shared location, not per-agent).
- Move `docs/stacks/<id>/` content under `cli/stacks/<id>/` and update `[tool.hatch.build.targets.wheel.force-include]` in [pyproject.toml](pyproject.toml).
- Add `STACKS_DIR` resolver mirroring `AGENTS_DIR`'s repo-checkout vs pip-install fallback.
- Add `--stack` flag to `apply` for all three agent manifests: [agents/claude-code/manifest.json](agents/claude-code/manifest.json), [agents/copilot/manifest.json](agents/copilot/manifest.json), [agents/codex/manifest.json](agents/codex/manifest.json). Update agent manifest JSON schema in `governance/schemas/`.
- New commands: `govkit stack list` (enumerates `cli/stacks/*/overlay.yaml`), `govkit stack apply <id>`.
- Default stack remains `python-fastapi` for non-breaking behavior.
- Emit `assumption{source: "flag" | "default"}` accordingly.
- Update [README.md](README.md) §"Switching Tech Stacks" — remove the `cp docs/stacks/...` recipe; point at `govkit stack list` / `--stack` / `govkit stack apply`.

### PR 3 — Repo-fit detectors (`RepoProfile`)
- New `cli/detect.py` module with the signals table above. Pure functions; `build_profile(target: Path)` takes explicit target (per A10).
- csproj parsing uses `xml.etree.ElementTree` (per R3); no regex.
- Wire into `apply`: print detected facts, downgrade silent default to "detected" assumption when confidence is high.
- New flag `--detect` on `apply` for dry-run inference.

### PR 4 — `govkit doctor` (with monorepo auto-discovery)
- New `cli/doctor.py` running checks D001–D014.
- D001 reads `marker.json.agent` and scans the corresponding rules tree (`.claude/rules/`, `.github/instructions/`, nested `AGENTS.md`).
- D013–D014 delegate to `cli/extensions.py` validators.
- Monorepo auto-discovery (per A9): walk for `.govkit/` directories under cwd when no `--target` given; print per-install summary.
- Read-only. Exit 1 on errors (any install).
- Add `govkit doctor` to the GovKit repo's own [.github/workflows/test.yml](.github/workflows/test.yml) as a self-check.

### PR 5 — `govkit calibrate`
- Interactive + `--non-interactive` modes.
- Reads `RepoProfile`, walks Section 7 checklist (agent-aware Step 6 and Step 7).
- Writes `GOVKIT_SETUP_REVIEW.md` and updates `marker.json` (`calibration.decisions[]`, per-assumption `calibrated_at` + `calibrated_against_overlay_version`).
- Regenerates `.govkit/skill_context.yaml`.
- Monorepo behavior matches doctor.

### PR 6a — Shared `cli/skill_context.py` loader + install-time writer
- New `cli/skill_context.py` with `load_skill_context(target: Path) -> SkillContext` and `write_skill_context(target: Path, ...) -> None`.
- Calls `discover_extensions()` and includes the `extensions:` block.
- `apply`, `stack apply`, and `calibrate` all write `skill_context.yaml`.
- **No skill files change in this PR.** Loader stands alone, fully tested, ready for consumers.

### PR 6b — Externalize claude-code skills + rule globs
- Audit and rewrite the four claude-code skills (architecture-preflight, spec-planning, implementation-plan, adr-author) to read `skill_context.yaml` and installed governance docs (per A4 — file references allowed, vocabulary not).
- Convert `.claude/rules/*.md` glob frontmatter to load from `skill_context.layers.*`.
- **Preserve existing extension contracts** (per R4): the architecture-preflight skill's §2.6 Extension Discovery block at [SKILL.md:28-44](agents/claude-code/skills/backend/architecture-preflight/SKILL.md#L28-L44) and the extension manifest's `agent_guidance.architecture_preflight` contract must keep working.
- Validates the externalization pattern in one agent before fanning out.

### PR 6c — Replicate to copilot + codex + split TECH_STACK
- Apply PR 6b's pattern to copilot (`.github/instructions/*.instructions.md` `applyTo:` patterns) and codex (nested `AGENTS.md` placement).
- Move L5-only sections of [docs/backend/architecture/TECH_STACK.md](docs/backend/architecture/TECH_STACK.md) (§4, §4a, §10a, §11 LLM, §11a) into a separate `AGENT_ARCHITECTURE.md` installed only at L5.
- Doctor D007 (level-leakage) becomes meaningful once the split lands.

### PR 7 — Tests + fixture repos
- Three fixture repos under `tests/fixtures/`: `dotnet-aspnet-azure/`, `python-fastapi-github/`, `empty/`.
- Golden-file tests for `apply` output + `GOVKIT_SETUP_REVIEW.md` per fixture × per agent.
- `doctor` finding tests covering each of D001–D014, including D001 parametrized across all three agents.
- `calibrate` non-interactive golden tests.
- Monorepo fixture (two `.govkit/` dirs under `apps/`) covering A9 discovery.
- Built-wheel smoke test (per A12): `python -m build && pip install dist/govkit-*.whl` in a clean venv, then `govkit stack list` resolves bundled stacks.
- `TestMergeMode` and existing apply tests continue passing.

**Sequence rationale:** PR 1 is the largest behavioral foundation; everything else builds on the new marker layout and edit-protection. PRs 2–5 are mostly additive and order-independent except PR 5 (calibrate) which depends on PR 3 (detectors). PR 6a unblocks 6b and 6c. PR 7 hardens.

---

## 9. Test Plan

Build on the existing pytest infrastructure ([tests/test_govkit.py](tests/test_govkit.py), [tests/test_validate.py](tests/test_validate.py), `TestMergeMode` pattern).

### Unit tests (per PR)

| Module | Tests |
|---|---|
| `cli/detect.py` | Each signal in isolation against constructed `tmp_path` repos. Confidence calculation. Empty-repo case returns empty profile, not error. |
| `cli/doctor.py` | Each check D001–D012 has a passing-case test and a failing-case test. D001 has three flavors (one per agent). Severity matrix. Exit-code assertion. |
| `cli/calibrate.py` | Decision recording. Non-interactive mode produces stable markdown. Skipping a step preserves assumption. |
| `cli/skill_context.py` | Loads, validates, defaults missing keys. |
| `cli/overlay.py` | Schema validation. Stack discovery from `AGENTS_DIR` resolves correctly in both repo-checkout and pip-install layouts. |

### Fixture repos (new — under `tests/fixtures/`)

Three fixtures, deliberately minimal, designed to exercise the detectors:

```
tests/fixtures/
  dotnet-aspnet-azure/
    .gitignore
    global.json
    src/Api/Api.csproj            # references Microsoft.AspNetCore.App
    src/Application/.gitkeep
    src/Infrastructure/.gitkeep
    azure-pipelines.yml
  python-fastapi-github/
    pyproject.toml                # fastapi + pytest in deps
    src/api/main.py
    src/ports/.gitkeep
    src/adapters/.gitkeep
    .github/workflows/ci.yml
  empty/
    .gitignore                    # one file only — covers the "no signals" case
```

### Golden-output tests

For each fixture × `(agent, level, type)` combination, snapshot:
- list of files written by `apply`
- `.govkit` JSON content
- `GOVKIT_SETUP_REVIEW.md` text
- `doctor` stdout

Stored as `tests/fixtures/<fixture>/expected/<agent>_<level>_<type>.snap`. Comparison uses simple text diff (no new dependency; consistent with existing project style).

### Doctor validation tests

One test per finding type, in `tests/test_doctor.py`:
```python
def test_d001_rule_glob_missing_claude_code(tmp_path):
    # apply governance to empty fixture with agent=claude-code
    # assert: rule files installed point at nonexistent globs
    # run doctor
    # assert: D001 finding with severity error, exit code 1
```

Parametrize D001 across `agent in ("claude-code", "copilot", "codex")`.

### Specific scenarios

- **`.NET ASP.NET Azure DevOps`** — apply with `--stack dotnet-aspnet --ci azure`; doctor should report 0 errors and minimal warnings (just `review_required` info).
- **`Python FastAPI GitHub Actions`** — apply with defaults; doctor should report 0 errors (baseline matches fixture).
- **`empty repo`** — apply with `--non-interactive --stack python-fastapi --ci github`; assumptions all `source: "default" | "flag"`; calibrate produces a populated review checklist.
- **`mismatch`** — apply with `--stack python-fastapi` to the `dotnet-aspnet-azure` fixture; doctor reports D005 (stack-mismatch) warning + D001 (rule-glob) errors.
- **`pip-install layout`** — at least one integration test runs against a fresh `pip install -e .` so `AGENTS_DIR` resolution from the wheel layout is exercised, not just the source-checkout fallback.

### Regression bar

The existing test suite must continue to pass on every PR. `TestMergeMode` is the canary — if overlay metadata changes break merging, the suite catches it. The extension test module (`test_extensions.py`) is the canary for any change touching `cli/extensions.py` consumers.

---

## 10. Usability Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Users skip the Review Checklist | Print it after install AND link to it from `.govkit` first-line comment; `doctor` reminds about unresolved `review_required` assumptions (D010). |
| Inference confidently picks the wrong stack | Print "detected" with evidence; require confirmation in interactive mode; `--non-interactive` requires `--stack` if confidence ≠ high. |
| `doctor` becomes noisy and gets ignored | Keep severity tiers strict — only true blockers are errors. Group warnings by category in output. Allow `.govkitignore` to silence specific findings (with a `reason:`). |
| `calibrate` feels like a long interview | Each step accepts "keep current" with one keystroke. Show estimated remaining steps. Allow `--only <step>` to revisit one decision. |
| `stack apply` overwrites team edits | Refuse without `--force` if any target file's mtime > `.govkit.applied_at`. Print diff summary. Always preserve `GOVKIT_SETUP_REVIEW.md`. |
| Skills break when `skill_context.yaml` is missing or stale | Loader supplies safe defaults + emits `doctor` warning D012 on mismatch. Skills never crash; they degrade to generic guidance. |
| Teams disable BDD-as-L4-gate but eval-gate still demands `acceptance.feature` | Add `.govkit.options.bdd: "none"` recognized by L4 validation; `validate` skips Gherkin checks when set. Document the escape hatch in CLAUDE.md template. |
| Existing repos run `apply` and clobber edited docs | Already protected: `governed`/`shared` are skip-existing. Add `--refresh-baselines` flag for explicit re-install + diff print. |
| Non-Python teams still see Python wording in non-overlay docs (`ARCH_CONTRACT`, `DESIGN_PRINCIPLES`, etc.) | PR 6 audit covers these; doctor D009 flags framework names in non-overlay docs. |
| Confusion between `validate` (feature artifacts) and `doctor` (governance fit) | README + `--help` text explicitly contrast them: "validate = is this feature compliant?", "doctor = does this install fit this repo?" |
| Pip-installed users can't see what stacks exist | `govkit stack list` reads bundled stacks from the installed wheel. README directs users to this command instead of `cp docs/stacks/...`. |
| Different agents fall out of sync (skill drift) | PR 6 establishes the shared `skill_context.yaml` contract. PR 7 golden tests parametrize across all three agents so divergence fails CI. |
| Extension contracts get clobbered or ignored by new commands | `stack apply` only touches files in its overlay manifest (the 6 stack docs); extension files have no `govkit:editable` header so doctor's stale-baseline check (D006) skips them. Doctor delegates extension validation to `cli/extensions.py` rather than re-implementing it. |
| Detectors false-positive in monorepos by walking from cwd | Per A10, `build_profile(target: Path)` always takes an explicit path; `apply` / `doctor` / `calibrate` pass their `--target` argument. Per A9, doctor/calibrate auto-discover `.govkit/` and scope per-install rather than per-repo. Monorepo fixture in PR 7 enforces this. |
| `.govkit` directory migration confuses users who edited the old file | Existing one-time-warning pattern ([cli/govkit.py:69](cli/govkit.py#L69)) extended to cover the file→directory migration; warning is suppressible and self-suppresses once the marker is on the new layout. `cmd_upgrade` is the natural moment to perform the migration explicitly. |
| `cmd_upgrade` silently destroys user edits | Per A2, PR 1 routes `upgrade` through the same edit-protection guard as `apply` and `stack apply`. Repos that ran `govkit upgrade` before PR 1 will continue to be at risk until they upgrade past it — call this out in the PR 1 release notes. |

---

## Critical files to modify

| File | PR | Change |
|---|---|---|
| [cli/govkit.py](cli/govkit.py) | 1, 2, 3 | Marker schema, `--stack` flag, detect wiring, post-install checklist |
| [cli/govkit.py](cli/govkit.py) `resolve_options` | 2 | Add `stack` option |
| [agents/claude-code/manifest.json](agents/claude-code/manifest.json) | 2 | Add `stack` to `options` |
| [agents/copilot/manifest.json](agents/copilot/manifest.json) | 2 | Add `stack` to `options` |
| [agents/codex/manifest.json](agents/codex/manifest.json) | 2 | Add `stack` to `options` |
| `cli/detect.py` (new) | 3 | `RepoProfile` + signal detectors |
| `cli/doctor.py` (new) | 4 | `doctor` command + D001–D012 (D001 agent-aware) |
| `cli/calibrate.py` (new) | 5 | `calibrate` command (agent-aware Step 6, 7) |
| `cli/skill_context.py` (new) | 6a | Skill context loader, used by skills + doctor across all three agents; calls `discover_extensions()` and includes `extensions:` block |
| `cli/overlay.py` (new) | 2 | `overlay.yaml` loader, `stack list`/`stack apply`; `STACKS_DIR` resolver |
| [cli/extensions.py](cli/extensions.py) | 4 | No API breakage. Doctor imports `discover_extensions` + existing validators for D013/D014. Consider exposing a `validate_extension(ext) -> list[ValidationFinding]` adapter. |
| [docs/backend/architecture/TECH_STACK.md](docs/backend/architecture/TECH_STACK.md) | 6c | Strip §4, §4a, §10a, §11 LLM, §11a into new `AGENT_ARCHITECTURE.md` (L5-only) |
| `agents/{claude-code,copilot,codex}/rules/` (per agent) | 6b, 6c | Read `skill_context.layers.outbound` for globs/applyTo; same for ports/api/services/security |
| `agents/{claude-code,copilot,codex}/skills/backend/` (per agent) | 6b, 6c | Replace hardcoded architecture vocabulary (`ports/`, `adapters/`, etc.) with reads from skill context + installed docs. File-path references to govkit-installed docs remain allowed. |
| `cli/stacks/<id>/overlay.yaml` (new — single shared location) | 2 | dotnet-aspnet, java-spring-boot, nodejs-fastify, go-gin, python-fastapi. Replaces `docs/stacks/<id>/`. |
| `governance/schemas/govkit_marker.schema.json` (new) | 1 | JSON schema for `.govkit/marker.json`; wired into `test_schemas.py` |
| `governance/schemas/agent_manifest.schema.json` | 2 | Add `stack` to allowed options keys |
| [pyproject.toml](pyproject.toml) | 2 | Update `[tool.hatch.build.targets.wheel.force-include]` to ship `cli/stacks/` (and drop `docs/stacks/` if removed) |
| [README.md](README.md) §"Switching Tech Stacks" | 2 | Rewrite around `govkit stack list` / `--stack` / calibrate; remove `cp docs/stacks/...` guidance |
| [tests/test_govkit.py](tests/test_govkit.py) | 1–7 | Extend existing classes; add `TestDoctor`, `TestCalibrate`, `TestDetect`, `TestOverlay`, `TestMarkerDirectoryMigration`, `TestEditProtection` |
| `tests/fixtures/{dotnet-aspnet-azure,python-fastapi-github,empty,monorepo}/` (new) | 7 | Minimal fixture repos for golden tests; monorepo fixture covers A9 |

## Existing functions/utilities to reuse

- `copy_entry` ([cli/govkit.py:160](cli/govkit.py#L160)) — keep as the sole copy mechanism; doc-header writer wraps it.
- `_select_variant` ([cli/govkit.py:252](cli/govkit.py#L252)) — extend to take `stack` dimension the same way `level` is handled.
- `_apply_by_type` ([cli/govkit.py:277](cli/govkit.py#L277)) — pattern reused for stack overlay merging.
- `read_govkit_marker` / `write_govkit_marker` ([cli/govkit.py:191-220](cli/govkit.py#L191-L220)) — extend dict shape, keep migration warnings pattern.
- `_maybe_warn_migration` ([cli/govkit.py:69](cli/govkit.py#L69)) — add `_maybe_warn_assumption_review_overdue` using the same one-time-print pattern for D010.
- `AGENTS_DIR` resolution ([cli/govkit.py:138](cli/govkit.py#L138)) — already handles repo-checkout vs pip-install; overlay loader follows the same pattern.
- `discover_extensions` + manifest validators ([cli/extensions.py](cli/extensions.py)) — skill_context loader and doctor both consume this; do not duplicate path-safety checks.
- `report_extensions` ([cli/extensions.py](cli/extensions.py), wired at [cli/govkit.py:493](cli/govkit.py#L493)) — keep call in `apply`; new Review Checklist can reference discovered extensions in its output.
- Validation pattern in [cli/validate.py](cli/validate.py) — reuse the check-function-returning-findings shape for `doctor`.
- pytest fixture style (`tmp_path`, monkeypatch, inline factories) — fixture repos slot in as parametrize sources for existing test classes.

## Verification

End-to-end verification each PR must pass before merge:

1. **Unit tests** — `pytest` clean on Python 3.11 and 3.12 (existing CI matrix).
2. **Smoke install — Python repo:** create empty dir, run `govkit apply --agent claude-code --level 4 --type api --stack python-fastapi --ci github`, confirm files written + `GOVKIT_SETUP_REVIEW.md` present.
3. **Smoke install — .NET repo:** copy `tests/fixtures/dotnet-aspnet-azure/` to tmp, run `govkit apply --agent claude-code --level 4 --type api --target <tmp>` (no `--stack`, no `--ci`), confirm output names `detected: csharp / aspnet-core / azure-pipelines`, confirms `.NET` content installed, prints checklist.
4. **Doctor on mismatch:** apply Python defaults to .NET fixture, run `govkit doctor`, confirm D001 errors + D005 warning.
5. **Calibrate non-interactive:** run on empty fixture, confirm `GOVKIT_SETUP_REVIEW.md` is a populated todo list.
6. **Stack swap preserves edits:** apply python-fastapi, edit `TECH_STACK.md`, run `govkit stack apply dotnet-aspnet`, confirm refusal without `--force`, confirm diff summary printed.
7. **Per-agent parity:** run `apply` + `doctor` against the same fixture for all three agents (`claude-code`, `copilot`, `codex`); confirm `GOVKIT_SETUP_REVIEW.md` content is consistent in substance (file paths differ per agent convention).
8. **Built-wheel smoke (per A12):** in a clean venv, `python -m build && pip install dist/govkit-*.whl`, then run `govkit stack list` and confirm bundled stacks resolve from the wheel layout (`site-packages/cli/stacks/`), not from a source-checkout fallback. Editable installs (`pip install -e .`) mask the wheel layout and must not be used for this check.
9. **Existing regression suite:** every test in `tests/` must continue to pass — the `TestMergeMode` class is the canary for overlay/manifest changes.
10. **Self-doctor:** run `govkit doctor` against the GovKit repo itself in CI; must exit 0 on `main`.
