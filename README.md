# govkit — Governed AI Delivery

[![PyPI version](https://badge.fury.io/py/govkit.svg)](https://badge.fury.io/py/govkit)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://pypi.org/project/govkit/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Publish](https://github.com/Accelerated-Innovation/governed-ai-delivery/actions/workflows/publish.yml/badge.svg)](https://github.com/Accelerated-Innovation/governed-ai-delivery/actions/workflows/publish.yml)

AI coding agents are powerful — but without constraints, they drift. They invent architecture, skip tests, ignore NFRs, and make decisions that belong to your team. **govkit** puts the agent inside a governed system where your architecture contracts, acceptance criteria, and evaluation thresholds are the source of truth, not the agent's training data.

```bash
pip install govkit
govkit apply --agent claude-code --target .
```

One command installs govkit. One more applies it to your project. The governance workflow your team follows from that point on is what keeps the agent aligned, every feature, every time.

> govkit works with any project language — Python, C#, Java, Go, TypeScript, or anything else. It copies Markdown specs, YAML configs, and Gherkin feature files into your project directory. Python is a dev-machine tool requirement only; it is not added as a project dependency.

<!-- TODO: Add terminal recording of `govkit apply --agent claude-code --target .` here using asciinema (https://asciinema.org) or VHS (https://github.com/charmbracelet/vhs) -->

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quickstart](#quickstart)
- [Maturity Levels](#maturity-levels)
- [Supported Agents](#supported-agents)
- [Key Concepts](#key-concepts)
- [Extensions](#extensions)
- [Working With the Agent](#working-with-the-agent)
- [Project Type Details](#project-type-details)
- [Monorepo (Fullstack) Pattern](#monorepo-fullstack-pattern)
- [Switching Tech Stacks](#switching-tech-stacks)
- [Interpreting Validation Failures](#interpreting-validation-failures)
- [Troubleshooting & FAQ](#troubleshooting--faq)
- [Multi-Repository Features](#multi-repository-features)
- [Architecture Reference](#architecture-reference)
- [Evaluation Reference](#evaluation-reference)
- [Getting Help](#getting-help)
- [License](#license)
- [Glossary](#glossary)
- [Resources](#resources)

---

## Prerequisites

- **Python 3.11+** — required to install and run govkit (does not need to be added to your project)
- **pip** — for installation (`pip install govkit`)
- **An AI coding agent** — Claude Code, GitHub Copilot, or OpenAI Codex (govkit provides the configuration, not the agent itself)

---

## Quickstart

### 1. Install govkit

```bash
pip install govkit
```

### 2. List available agents

```bash
govkit list
```

### 3. Apply to your project

From your project root, run `govkit apply` and answer the prompts:

```bash
govkit apply --agent claude-code --target .
```

Or specify all options explicitly. Each `govkit apply` configures **one project shape**: backend (`api` / `cli`) or UI (`ui-react` / `ui-angular`). Fullstack-in-one-repo is supported via the [monorepo pattern](docs/MONOREPO_PATTERN.md) — one `govkit apply` per subdirectory.

```bash
# Level 3: Governed AI Delivery (Foundations) — agent rules + architecture docs only (default)
govkit apply --agent claude-code --level 3 --type api --ci github --target .

# Level 4: Spec-Driven Add-On — adds the features/ directory and 5-artifact contract
govkit apply --agent claude-code --level 4 --type api --ci github --target .

# Level 5: GenAI Operations (LLM routing, evaluation, guardrails)
govkit apply --agent claude-code --level 5 --type api --ci github --target .

# Python CLI tool + Azure DevOps
govkit apply --agent copilot --type cli --ci azure --target .

# React UI project (L4)
govkit apply --agent copilot --level 4 --type ui-react --ci github --target .

# Angular UI project (L4) on OpenAI Codex
govkit apply --agent codex --level 4 --type ui-angular --ci github --target .
```

A `.govkit` marker file is written to your project root, tracking the agent, level, options, and govkit version. This enables `govkit init`, `govkit validate`, and `govkit upgrade` to auto-detect your configuration without re-specifying flags.

When using interactive mode (no `--type`, `--ci` flags), you'll see prompts like:

```
$ govkit apply --agent claude-code --target .

Applying govkit agent 'claude-code' to /path/to/your/project

  Project type? [api / cli / ui-react / ui-angular] (default: api): ui-react
  CI platform? [github / azure] (default: github): github

  Configuration: {'type': 'ui-react', 'ci': 'github'}

Agent files:
  copied  /path/to/your/project/CLAUDE.md
  copied  /path/to/your/project/src/CLAUDE.md
  copied  /path/to/your/project/.claude/rules/repo-scope.md
  ...
```

### 4. Verify installation

After applying, your project will contain artifacts appropriate to the shape you picked.

**Backend shape** (`--type api` or `--type cli`):

```
your-project/
├── CLAUDE.md (or .github/copilot-instructions.md, or AGENTS.md)
├── .claude/rules/ (or .github/instructions/, or nested AGENTS.md per layer)
│   └── api.md, services.md, ports.md, adapters.md, security.md, repo-scope.md
├── .claude/skills/ (or .github/skills/, or .agents/skills/)
│   └── architecture-preflight/, spec-planning/, implementation-plan/, adr-author/
├── docs/backend/
│   ├── architecture/   — ARCH_CONTRACT, API_CONVENTIONS, TECH_STACK, etc.
│   └── evaluation/     — eval_criteria.md, scoring rubrics
├── features/           — created empty at L4+; scaffold your first feature with govkit init
├── governance/backend/schemas/   — eval_criteria.schema.json
└── ci/github/ (or azure/)        — l3-quality-gate.yml + L4/L5 gates
```

**UI shape** (`--type ui-react` or `--type ui-angular`):

```
your-project/
├── CLAUDE.md (or .github/copilot-instructions.md, or AGENTS.md)
├── src/CLAUDE.md       — Claude only: nested UI layer rules under src/
│                         (Codex uses src/AGENTS.md + nested AGENTS.md per layer;
│                          Copilot uses .github/instructions/ with src-scoped applyTo: globs)
├── .claude/rules/ (or .github/instructions/)
│   └── repo-scope.md, test-first.md (L4+), spec-compliance.md (L4+)
├── .claude/skills/
│   └── ui-architecture-preflight/, ui-spec-planning/, ui-implementation-plan/, ui-adr-author/
├── docs/ui/
│   ├── architecture/   — MVVM_CONTRACT, ACCESSIBILITY_STANDARDS, react|angular subdirs
│   └── evaluation/     — eval_criteria.md, scoring rubrics
├── governance/ui/      — schemas, templates
└── ci/github/ (or azure/)  — l3-ui-quality-gate.yml + L4/L5 UI gates
```

Backend installs ship no UI artifacts; UI installs ship no backend artifacts. The CI dispatch is type-aware: backend types get `l3-quality-gate.yml`, UI types get `l3-ui-quality-gate.yml`. For fullstack monorepos, run one `govkit apply` per app subdirectory — see the [monorepo pattern](docs/MONOREPO_PATTERN.md).

> **Starter templates and worked examples** are bundled inside the govkit package, not copied into your project by `govkit apply`. Use `govkit init <feature-name>` to scaffold a new feature from the appropriate starter, or run `govkit list` to see what is available.

### 5. Customize your governance artifacts

> [!WARNING]
> **This step is not optional.** The installed `docs/` files are authoritative starting points — they reflect sound defaults, but they are written for a generic project. Your agent will treat them as law. If you skip this step, the agent will govern your project against someone else's architecture decisions.

Before writing a single line of feature code, review and update the following to match your project:

**Backend projects (API or CLI):**
- `docs/backend/architecture/TECH_STACK.md` — replace with your actual approved libraries, frameworks, and versions
- `docs/backend/architecture/ARCH_CONTRACT.md` — confirm the hexagonal layer names and boundaries match your codebase structure
- `docs/backend/architecture/API_CONVENTIONS.md` (API) or `docs/backend/architecture/CLI_CONVENTIONS.md` (CLI) — update conventions to match your project standards
- `docs/backend/architecture/SECURITY_AUTH_PATTERNS.md` — replace with your actual auth provider, token pattern, and scope conventions
- `docs/backend/evaluation/eval_criteria.md` — confirm FIRST and 7 Virtue thresholds are appropriate for your team's standards

**React UI projects:**
- `docs/ui/architecture/react/TECH_STACK.md` — confirm your React version, state management libraries, and testing stack
- `docs/ui/architecture/react/COMPONENT_CONVENTIONS.md` — update to reflect your project's folder structure and naming conventions
- `docs/ui/evaluation/eval_criteria.md` — confirm accessibility standard and FIRST thresholds

**Angular UI projects:**
- `docs/ui/architecture/angular/TECH_STACK.md` — confirm your Angular version, TanStack Query setup, and testing stack
- `docs/ui/architecture/angular/COMPONENT_CONVENTIONS.md` — update to reflect your project's folder structure and naming conventions
- `docs/ui/evaluation/eval_criteria.md` — confirm accessibility standard and FIRST thresholds

These files are the source of truth for your AI agent. The agent reads them before every planning and implementation step. Keep them accurate and up to date as your project evolves.

### 6. Keep governance contracts up to date

When you upgrade govkit, run `govkit upgrade` to refresh the files that govkit owns — architecture contracts, CI gate pipelines, plan templates — without touching the files your team owns.

```bash
pip install --upgrade govkit
govkit upgrade --target .
```

govkit distinguishes three categories of files:

| Category | Examples | `apply` | `upgrade` |
|---|---|---|---|
| **Agent config** | `CLAUDE.md`, `.claude/rules/`, `.agents/skills/` | Always overwrite | Always overwrite |
| **Governed contracts** | `docs/backend/architecture/`, `governance/backend/templates/`, `ci/github/` | Write once (skip if present) | **Overwrite** |
| **Project artifacts** | `features/starter_*/`, your ADRs, filled-in feature files | Write once (skip if present) | Skip |

After upgrading, review the diff and commit:

```bash
git diff
git add -p
git commit -m "chore: upgrade govkit governance contracts to vX.Y.Z"
```

Use `--force` to re-apply even when the version is already current — useful for resetting a contract file to govkit defaults after an accidental edit:

```bash
govkit upgrade --target . --force
```

### 7. Validate governance compliance

```bash
govkit validate --target .
```

Validation is level-aware. **Level 3** is a no-op (Foundations ships agent rules + architecture docs only — there are no per-feature artifacts to check; the CI quality-gate is the L3 compliance surface). **Level 4** runs the full 5-artifact governed contract check (existence + Gherkin structure + NFR completeness + tag coverage + eval_criteria.yaml schema + evaluation prediction thresholds). **Level 5** adds LLM-specific NFR + DeepEval/Promptfoo checks. The level is auto-detected from `.govkit` or can be overridden:

```bash
govkit validate --level 4 --target .
```

---

## Maturity Levels

govkit supports three operating levels in an additive ladder. Each level commits the team to a different **way of working**, not just a different artifact count. The boundary between L3 and L4 sits at the most meaningful place: whether the team adopts a `features/` directory model and per-feature spec contracts.

| Level | Name | What it ships | What the team commits to |
|-------|------|---------------|--------------------------|
| **Level 3** | Governed AI Delivery (Foundations) | Agent rules, architecture contracts under `docs/*/architecture/`, `/adr-author` skill, lean CI gate (commit-format + import-linter + sonar/snyk). **No `features/` directory, no per-feature artifacts.** | "Our AI agents follow our architecture contracts." Lowest-friction entry; no project-structure change required. |
| **Level 4** | Spec-Driven Add-On | Adds the `features/<name>/` 5-artifact contract (`acceptance.feature`, `nfrs.md`, `eval_criteria.yaml`, `plan.md`, `architecture_preflight.md`), feature-coupled skills (`/spec-planning`, `/architecture-preflight`, `/implementation-plan`), test-first + spec-compliance rules (binding), governance CI jobs, and per-feature evaluation prediction (FIRST + 7 Virtues, average ≥ 4.0). | "We adopt spec-first, test-first feature delivery on top of L3." `govkit init` becomes meaningful here. |
| **Level 5** | GenAI Operations | LLM-specific NFR categories (latency, cost, fallback, safety), `agent_topology.md` for multi-agent features, deepeval/promptfoo/guardrails CI gates, LLM gateway/observability/multi-agent rules, LiteLLM routing, OpenLLMetry + Langfuse, RAGAS, NeMo Guardrails. | "Our LLM features are governed (routing, evaluation, safety)." Builds on L4. |

**Start at Level 3 (default)** if you want governed AI agents without restructuring your codebase. **Move to Level 4** when your team is ready to commit to spec-first feature delivery. **Move to Level 5** when shipping LLM-powered features that need governed model routing, evaluation, and safety.

The ladder is **additive**: L4 ⊃ L3, L5 ⊃ L4. Files installed at lower levels are not replaced by higher levels (with one exception: the agent's top-level entry point — `CLAUDE.md` / `.github/copilot-instructions.md` / `AGENTS.md` — is re-issued at each level so the agent sees the right operating mode).

### Level 3 — Governed AI Delivery (Foundations)

Your AI agent operates aligned to your architecture contracts:

- Reads `docs/<area>/architecture/` (ARCH_CONTRACT, BOUNDARIES, TESTING, SECURITY_AUTH_PATTERNS, etc.) on every turn
- Path-scoped rules trigger when editing files in each layer (api/, services/, ports/, adapters/, security/)
- ADRs required for any standard extension, override, or boundary change — scaffolded with `/adr-author`
- Test-first is recommended (the binding rule lives at L4)
- CI quality-gate enforces commit-format, import-linter (architecture boundaries), SonarQube, Snyk
- **No `features/` directory is created.** `govkit init` errors at L3 with a pointer to `--level 4`.
- `govkit validate` is a no-op (returns 0 with informational message).

### Level 4 — Spec-Driven Add-On

Everything in Level 3, plus:

Every feature lives under `features/<name>/` with five required artifacts:

- Defined with **Gherkin acceptance criteria** tagged to NFR categories
- Constrained with **fully populated NFRs** (no TBD entries permitted)
- Governed by **evaluation criteria** validated against a JSON Schema
- Planned through **Architecture Preflight + Spec Planning + Implementation Plan** skills
- Bounded by **hexagonal architecture contracts** with FIRST + 7 Virtues prediction (average ≥ 4.0)
- Enforced by **governance CI jobs** (artifact existence, eval-criteria schema, prediction thresholds, contract compatibility)

### Level 5 — GenAI Operations

Everything in Level 4, plus:

- Routed through **LiteLLM** as the sole LLM gateway (model routing, fallback, cost tracking)
- Observed via **OpenLLMetry + Langfuse** (LLM-specific telemetry, trace storage, prompt versioning)
- Evaluated with **DeepEval** (quality metrics), **Promptfoo** (adversarial testing), and **RAGAS** (retrieval evaluation)
- Guarded by **NeMo Guardrails** (conversational safety) and **Guardrails AI** (structured output validation)
- Extended with **LLM-specific NFRs** (latency, cost, fallback, safety) and **3 additional CI gates**

The AI agent operates inside a governed system. Architecture, evaluation, and feature artifacts are the source of truth — not the agent.

### Migrating from v0.6.x

The L3 / L4 maturity-model meaning changed in v0.7.0. If your `.govkit` marker says `level: "3"` (the v0.6 simpler 3-artifact model), run:

```bash
govkit upgrade --migrate-levels --target .
```

You'll be prompted to choose: migrate your existing 3-artifact features to the new L4 (with stub generation for the two new artifacts), or adopt new-L3 (no `features/`). See [CHANGELOG.md](CHANGELOG.md) for the full migration guide.

---

## Supported Agents

govkit installs agent-specific configuration files into your target project at the paths shown below. Three agents are supported, each with the same variant options:

| Agent | AI Tool | Files installed into your project |
|---|---|---|
| `claude-code` | Claude Code | `CLAUDE.md`, `.claude/rules/`, `.claude/skills/` |
| `copilot` | GitHub Copilot | `.github/copilot-instructions.md`, `.github/instructions/`, `.github/skills/` |
| `codex` | OpenAI Codex | `AGENTS.md` (root + nested per layer), `.agents/skills/` |

All agents support the same variant options:

| Option | Choices | Default |
|---|---|---|
| `--level` | `3`, `4`, `5` | `3` |
| `--type` | `api`, `cli`, `ui-react`, `ui-angular` | `api` |
| `--ci` | `github`, `azure` | `github` |

The `--type` choices are flat — one install configures one project shape. The legacy `--ui` cross-product was removed in v0.8. For fullstack monorepos see the [monorepo pattern](docs/MONOREPO_PATTERN.md).

---

## Key Concepts

**Hexagonal Architecture (Ports & Adapters)** — Your domain logic lives at the center, isolated from infrastructure. Inbound adapters (API routes, CLI commands) call inbound ports. Outbound ports define contracts that adapters (databases, APIs, message queues) implement. Domain code never imports infrastructure libraries.

**MVVM (UI projects)** — Model-View-ViewModel. Components (View) render UI. Hooks or inject functions (ViewModel) provide data and actions. API functions (Model) call the backend. Components never call APIs directly.

**FIRST Principles** — Test quality framework. Tests must be **F**ast, **I**solated, **R**epeatable, **S**elf-verifying, and **T**imely. Each principle is scored 1–5 with a minimum average of 4.0.

**7 Code Virtues** — Implementation quality framework. Code must be **Working**, **Unique**, **Simple**, **Clear**, **Easy** to maintain, **Developed** (tested and clean), and **Brief**. Each virtue is scored 1–5 with a minimum average of 4.0.

**Gherkin Acceptance Criteria** — Features are specified using Given/When/Then scenarios. Scenarios are tagged with NFR categories (`@nfr-performance`, `@nfr-security`) to ensure non-functional requirements have test coverage.

**Governed Development** — The agent reads architecture contracts, evaluation criteria, and feature specs before generating code. CI gates enforce compliance. The agent proposes; your governance artifacts decide.

---

## Extensions

Govkit supports **optional, self-describing extension packs** that layer additional architecture contracts and governance templates on top of the core kit. Extensions are discovered at the root-level `extensions/` folder of your project — a sibling of `docs/`, `governance/`, and `features/`:

```text
<project>/
├── docs/
├── governance/
├── features/
├── extensions/
│   └── <extension-id>/
│       ├── manifest.yaml
│       ├── README.md
│       ├── docs/
│       └── governance/
└── .govkit
```

**Discovery contract:**
- **Scan** — `govkit apply` and `govkit validate` scan `extensions/*/manifest.yaml`.
- **Self-describing** — each extension declares its own `id`, `version`, `contract_sets`, `capabilities`, and agent guidance in its manifest. Govkit needs no per-extension code.
- **In-place** — extensions are not installed by the CLI. The folder under `extensions/<id>/` *is* the install. All paths in the manifest are relative to that folder.
- **No-extension behavior** — when `extensions/` is absent, govkit behaves exactly as it does today. Extensions are entirely optional.

**Minimal manifest (`extensions/<id>/manifest.yaml`):**

```yaml
id: my-extension
name: My Extension
version: 0.1.0
extension_type: architecture
contract_sets:
  - id: my_contracts
    description: ...
    paths:
      - docs/backend/architecture/MY_CONTRACT.md
    capabilities:
      - my-capability
```

### Resolving overlap with core contracts

When an extension contract covers the same topic as a core govkit contract (e.g. an `AGENT_EVALUATION_CONTRACT.md` extension alongside core `EVALUATION_LLM_CONTRACT.md`), the manifest declares the relationship explicitly via `relates_to`:

```yaml
contract_sets:
  - id: my_contracts
    paths: [docs/backend/architecture/AGENT_EVALUATION_CONTRACT.md]
    relates_to:
      extends:    [docs/backend/architecture/EVALUATION_LLM_CONTRACT.md]   # both apply; stricter rule wins
      supersedes: []                                                        # extension replaces core (requires ADR)
```

- `relates_to.extends` — the extension layers additional constraints on top of the core contract. The agent reads both and applies whichever is stricter on any specific point.
- `relates_to.supersedes` — the extension replaces the listed core contract for rules in its scope. Requires an ADR in the consuming project.

**Undeclared overlap is detected.** `govkit validate` runs a filename-token heuristic: if an extension contract shares a topic token with a core contract under `docs/backend/architecture/` and `relates_to` does not declare the relationship, the validator emits a WARN (or FAIL under `--strict`) asking the extension author to declare the intent. This prevents silent drift when extension authors and core authors update the same topic area independently.

**Agent reading order at preflight time.** The architecture-preflight skill reads core contracts first, then extension contracts; it prefers extensions only when `supersedes` is declared. If an applicable extension and a core contract conflict and `relates_to` does not declare the relationship, the agent halts and requests either a manifest update or an ADR rather than silently picking one.

See `extensions/agentic-skills/` in this repository for a complete reference example.

---

## Working With the Agent

Once govkit is installed, here is how you interact with the agent to deliver a feature. This lifecycle applies to **every feature**, regardless of project type or agent.

### Step 1: Create a Feature Folder

Use `govkit init` to create a feature from the appropriate starter:

```bash
govkit init my_feature --target .
```

Or specify the starter type explicitly:

```bash
govkit init my_feature --starter backend --target .
```

The command auto-detects your maturity level from `.govkit`. **`govkit init` requires Level 4 or higher** — Level 3 (Foundations) ships agent rules and architecture contracts only and has no `features/` directory model. Running `govkit init` at L3 errors with a pointer to `govkit apply --level 4`. At L4 the bundled starter has all 5 artifacts; at L5 the starter adds `agent_topology.md` for multi-agent features.

For Level 4 projects, each starter's `eval_criteria.yaml` includes mode selection instructions at the top. Set the `mode` field to match your feature type: `llm` (LLM generation/retrieval), `deterministic` (pure logic), or `none` (configuration artifacts). If the mode is `deterministic` or `none`, delete the `llm_evaluation` section.

### Step 2: Write Your Acceptance Criteria

Edit `features/my_feature/acceptance.feature` with your Gherkin scenarios:

- Write happy path and failure/edge case scenarios
- Tag NFR scenarios with `@nfr-performance`, `@nfr-security`, etc.
- Tag E2E scenarios with `@e2e` (UI projects)
- Add `@contract` scenarios if the feature produces shared artifacts

### Step 3: Complete Your NFRs

Edit `features/my_feature/nfrs.md` — replace every TBD entry with concrete requirements. The agent will refuse to proceed if any TBD entries remain.

### Step 4: Run Architecture Preflight

Ask the agent to validate your feature against the architecture contracts:

| Agent | Command |
|---|---|
| Claude Code | `/architecture-preflight my_feature` |
| Copilot | `/architecture-preflight` (with feature context) |
| Codex | `$architecture-preflight my_feature` |

The agent produces `architecture_preflight.md` covering boundary analysis, security impact, evaluation impact, and whether an ADR is needed. If an ADR is required, create it next:

| Agent | Command |
|---|---|
| Claude Code | `/adr-author my_feature` |
| Copilot | `/adr-author` |
| Codex | `$adr-author my_feature` |

### Step 5: Generate the Plan

Ask the agent to create the implementation plan:

| Agent | Command |
|---|---|
| Claude Code | `/spec-planning my_feature` |
| Copilot | `/spec-planning` |
| Codex | `$spec-planning my_feature` |

The agent generates `plan.md` and `eval_criteria.yaml`. The plan includes:
- Increments with deliverables and tests
- An **Evaluation Compliance Summary** predicting FIRST and 7 Virtue scores
- Each increment sized as a single committable unit (~300 lines)

**The agent will not proceed if predicted averages are below 4.0.**

### Step 6: Review the Implementation Plan

Ask the agent to break the plan into a detailed task checklist:

| Agent | Command |
|---|---|
| Claude Code | `/implementation-plan my_feature` |
| Copilot | `/implementation-plan` |
| Codex | `$implementation-plan my_feature` |

Review and approve before implementation begins.

### Step 7: Implement Incrementally

Work through the plan one increment at a time. For each increment:

1. The agent writes production code respecting architecture boundaries
2. The agent writes tests (unit, integration, contract as needed)
3. You review and commit: `feat(my_feature): increment 1 — <name>`
4. Move to the next increment

**Do not skip increments or combine multiple increments into one commit.**

### Step 8: Push and Merge

Open a PR. CI gates automatically run:

- Schema validation of `eval_criteria.yaml`
- FIRST and 7 Virtue prediction completeness
- Unit, component, and E2E tests
- Architecture boundary enforcement
- Security scan and quality gates
- Accessibility checks (UI projects)

All gates must pass before merge.

---

## Project Type Details

The 8-step workflow above applies to all project types. Key differences by type:

### Backend API

**Architecture:** Hexagonal Architecture — ports and adapters. API routes are the inbound adapter layer. See `docs/backend/architecture/API_CONVENTIONS.md`.

**Layer rules** (load automatically when editing files):
- `api.md` for `**/api/**`
- `services.md` for `**/services/**`
- `ports.md` for `**/ports/**`
- `adapters.md` for `**/adapters/**`
- `security.md` for `**/security/**` and `**/auth/**`

**CI gates:** `ci/github/quality-gate.yml`, `ci/github/eval-gate.yml` (or `ci/azure/` for Azure DevOps)

### CLI

**Architecture:** Hexagonal Architecture — CLI commands are the inbound adapter layer (same position as API routes). See `docs/backend/architecture/CLI_CONVENTIONS.md`.

**Layer rules** (load automatically):
- `cli.md` for `**/cli/**` and `**/commands/**`
- `services.md`, `ports.md`, `adapters.md`, `security.md` as above

**CI gates:** Same backend gates — `ci/github/quality-gate.yml`, `ci/github/eval-gate.yml`

### React UI

**Architecture:** MVVM with vertical slice feature structure. Layer order is API → ViewModel → View. See `docs/ui/architecture/MVVM_CONTRACT.md`.

**Layer rules** (load automatically):
- `components.md` for View layer
- `viewmodel.md` for hooks and store
- `api.md` for API client functions
- `accessibility.md` for accessibility concerns

**Implementation order:** API functions → React Query hooks → Zustand stores → Components → E2E tests

**CI gates:** `ci/github/ui-quality-gate.yml`, `ci/github/ui-eval-gate.yml`

### Angular UI

**Architecture:** MVVM with vertical slice feature structure. Standalone components with `OnPush`. See `docs/ui/architecture/MVVM_CONTRACT.md`.

**Layer rules:** Same as React, with Angular-specific content.

**Implementation order:** API functions → TanStack Query inject functions → Signal stores → Standalone components → E2E tests

**CI gates:** `ci/github/ui-quality-gate.yml`, `ci/github/ui-eval-gate.yml`

---

## Monorepo (Fullstack) Pattern

Each `govkit apply` configures **one project shape**. There is no `--type fullstack`. Teams that need both backend and UI in a single repo run `govkit apply` once per subdirectory:

```bash
govkit apply --agent claude-code --type api      --level 4 --ci github --target apps/api
govkit apply --agent claude-code --type ui-react --level 4 --ci github --target apps/web
```

Each subdir becomes a self-contained govkit install — separate `.govkit` marker, separate `features/`, separate CI gates. The three agents all support subpath governance natively:

- **Claude Code** — recursive `CLAUDE.md` discovery picks up the right shape based on the open file's directory
- **Codex** — directory-walk loader concatenates `AGENTS.md` from leaf to root
- **Copilot** — `applyTo:` globs in each instructions file (one small post-install adjustment to prefix the app path so globs don't cross app boundaries)

For the complete setup — directory layout, CI workflow examples, the Copilot `applyTo:` prefix tweak, feature governance per app, upgrade flow, and gotchas — see [docs/MONOREPO_PATTERN.md](docs/MONOREPO_PATTERN.md).

If your backend and UI live in **separate repositories** instead of subdirectories of a monorepo, see [Multi-Repository Features](#multi-repository-features) below — different coordination problem.

---

## Switching Tech Stacks

The default installed stack is **Python / FastAPI**. To switch to a different backend language, copy the 6 stack-specific architecture doc files from `docs/stacks/<stack>/` into `docs/backend/architecture/`. The AI agents read those files as the authoritative source of truth — no agent rules, manifests, or CLI configuration changes needed.

### Why only 6 files?

The agent rules and most architecture docs are language-agnostic. Only these 6 files define stack-specific conventions:

| File | What it defines |
|---|---|
| `TECH_STACK.md` | Languages, versions, approved frameworks |
| `API_CONVENTIONS.md` | Route patterns and request/response idioms |
| `TESTING.md` | Test framework, mocking library, BDD tool |
| `LAYER_IMPLEMENTATION.md` | DI patterns, interface idioms, DTO style |
| `SECURITY_AUTH_PATTERNS.md` | Auth libraries, token handling, hashing |
| `OBSERVABILITY_PORT_CONTRACT.md` | Structured logging library, OTel SDK |

All other docs (DESIGN_PRINCIPLES, ARCH_CONTRACT, BOUNDARIES, GHERKIN_CONVENTIONS, ERROR_MAPPING, etc.) are universal and require no changes.

### Available stacks

| Directory | Stack |
|---|---|
| `docs/stacks/dotnet-aspnet/` | C# 12 / .NET 8 / ASP.NET Core Minimal APIs |
| `docs/stacks/java-spring-boot/` | Java 21 / Spring Boot 3 / Spring Web MVC |
| `docs/stacks/nodejs-fastify/` | Node.js 20 LTS / TypeScript 5 / Fastify 4 |
| `docs/stacks/go-gin/` | Go 1.22+ / Gin |

### How to switch

```bash
# Switch to C# / ASP.NET Core
cp docs/stacks/dotnet-aspnet/* docs/backend/architecture/

# Switch to Java / Spring Boot
cp docs/stacks/java-spring-boot/* docs/backend/architecture/

# Switch to Node.js / Fastify
cp docs/stacks/nodejs-fastify/* docs/backend/architecture/

# Switch to Go / Gin
cp docs/stacks/go-gin/* docs/backend/architecture/
```

After copying, review the files and update any project-specific details (approved library versions, internal service names, etc.). Consider raising an ADR to document the stack decision.

See [`docs/stacks/README.md`](docs/stacks/README.md) for the complete guide, including how to add new stacks.

---

## Interpreting Validation Failures

When `govkit validate --target .` reports failures, here's what they mean and how to fix them:

| Failure | Meaning | Fix |
|---|---|---|
| `acceptance.feature not found` | Feature folder is missing its Gherkin spec | Copy from starter and write scenarios |
| `no Feature: keyword` or `no Scenario: keyword` | Gherkin file exists but is malformed | Add `Feature:` header and at least one `Scenario:` with Given/When/Then |
| `nfrs.md contains TBD entries` | NFR categories have placeholder values | Replace every TBD with a concrete, measurable requirement |
| `eval_criteria.yaml missing or invalid` | Eval config doesn't match the JSON Schema | Check `governance/*/schemas/eval_criteria.schema.json` for required fields |
| `plan.md missing evaluation_prediction` | Plan exists but has no prediction block | Add the `evaluation_prediction` YAML block (see worked examples) |
| `predicted FIRST average below 4.0` | Predicted test quality is below threshold | Revise the plan — improve test strategy or split complex increments |
| `predicted Virtue average below 4.0` | Predicted code quality is below threshold | Revise the plan — simplify design, reduce complexity, improve separation |
| `NFR tag coverage incomplete` | Some NFR categories lack corresponding Gherkin tags | Add `@nfr-<category>` tags to relevant scenarios in acceptance.feature |

---

## Troubleshooting & FAQ

**Q: `govkit: command not found` after installation**
A: Ensure your Python scripts directory is on your PATH. Try `python -m cli.govkit` as a fallback, or reinstall with `pip install --user govkit`.

**Q: `govkit apply` fails with "no agent found"**
A: Check that you're using a valid agent name (`claude-code`, `copilot`, or `codex`). Run `govkit list` to see available agents.

**Q: The agent ignores my architecture rules**
A: Verify the rules files were copied to the correct location (`.claude/rules/`, `.github/instructions/`, or the nested `AGENTS.md` files for Codex). Check that file paths match what the agent expects — Claude Code loads rules based on the file path you're editing, Codex walks the directory tree from repo root down to the current working directory and concatenates each `AGENTS.md` it finds.

**Q: How do I update to a newer version of govkit?**
A: Run `pip install --upgrade govkit`. Then re-run `govkit apply` — it will skip files that already exist. To force update a specific file, delete it first.

**Q: Can I use govkit on an existing project with existing code?**
A: Yes. `govkit apply` copies governance artifacts into your project without modifying existing code. You may need to adjust `docs/backend/architecture/ARCH_CONTRACT.md` and other docs to reflect your existing architecture rather than the defaults.

**Q: What if my architecture doesn't match the Hexagonal defaults?**
A: Customize the architecture docs after install. The agent follows whatever `ARCH_CONTRACT.md` says — if your project uses a different pattern, document it there. Consider creating an ADR explaining the architectural choice.

**Q: Can I use multiple agents in the same project?**
A: Yes. Run `govkit apply` once for each agent. They install to different paths (`.claude/`, `.github/`, and `AGENTS.md` + `.agents/` for Codex) and share the same `docs/`, `governance/`, and `features/` artifacts. All agents read the same architecture contracts.

**Q: How do I add a new NFR category?**
A: Add the category as a `## Heading` in your feature's `nfrs.md`, add corresponding `@nfr-<category>` tags to acceptance scenarios, and update `cli/validate.py`'s `category_to_tag` mapping if you want automated tag coverage validation.

**Q: The CI pipeline fails because SonarQube/Snyk isn't configured**
A: These tools are optional. If your team doesn't use them, remove or comment out those jobs from the CI pipeline files. See `ci/README.md` for details on required secrets.

**Q: What does "thresholds_met: false" mean in my plan?**
A: Your predicted FIRST or Virtue average is below 4.0, or a predicted accessibility violation count is above zero. Revise the plan — simplify the design, improve test strategy, or split large increments before proceeding.

---

## Multi-Repository Features

If your feature spans multiple repositories (e.g., Auth Service + Client SDK + API Gateway), see:

- [CROSS_REPO_FEATURES.md](docs/CROSS_REPO_FEATURES.md) — Complete guide to planning, implementing, and testing features across repos
- [REPO_SCOPE_ANALYSIS_GUIDANCE.md](docs/REPO_SCOPE_ANALYSIS_GUIDANCE.md) — How to declare repo ownership in your feature spec
- `features/example-jwt-unification/` — Worked example of a 3-repo JWT authentication feature

The key principle: **Every feature must declare which repositories own which parts.** This prevents agents from writing code in the wrong repo.

### Multi-Repo FAQ

**Q: My feature needs changes in Auth Service, API Gateway, and Frontend. Where do I document this?**
A: In the primary owner repo's `features/<feature>/nfrs.md`, add a "Repository Scope" section with a table listing each repo, owner team, modules, and contracts. See [CROSS_REPO_FEATURES.md#repository-ownership-table](docs/CROSS_REPO_FEATURES.md#repository-ownership-table).

**Q: Can we implement the feature in just one repo and copy code to the others later?**
A: No — this violates ownership and creates duplication. Each repo implements its own portion against the shared contract. See [CROSS_REPO_FEATURES.md#common-pitfalls](docs/CROSS_REPO_FEATURES.md#common-pitfalls).

**Q: Should we wait for Repo A to finish before Repo B starts?**
A: No. Each repo implements in parallel using mocks for external dependencies. Only the final integration tests (after all repos merge) verify cross-repo contracts. See [CROSS_REPO_FEATURES.md#implementation-stage-parallel](docs/CROSS_REPO_FEATURES.md#implementation-stage-parallel).

**Q: How do we test a feature that depends on another repo's code?**
A: Each repo has unit tests (mocking externals) and contract tests (verifying its own implementation). After all repos merge to main, run integration tests to verify end-to-end behavior. See [CROSS_REPO_FEATURES.md#testing-strategy](docs/CROSS_REPO_FEATURES.md#testing-strategy).

**Q: What if the repos have deployment dependencies (one must be live before the other)?**
A: Document the order in your `nfrs.md` "Key Cross-Repo Contracts" section. Ideally, design contracts to be backward-compatible so deployment order is flexible. See [CROSS_REPO_FEATURES.md#integration-stage-sequential](docs/CROSS_REPO_FEATURES.md#integration-stage-sequential).

---

## Architecture Reference

> The files linked below are installed into your project by `govkit apply`. Links point to their source in the govkit repository for reference.

### Backend (Core — Level 4)

- [ARCH_CONTRACT.md](docs/backend/architecture/ARCH_CONTRACT.md) — Hexagonal Architecture contract
- [BOUNDARIES.md](docs/backend/architecture/BOUNDARIES.md) — Layer dependency rules
- [API_CONVENTIONS.md](docs/backend/architecture/API_CONVENTIONS.md) — FastAPI conventions
- [CLI_CONVENTIONS.md](docs/backend/architecture/CLI_CONVENTIONS.md) — Click/Typer conventions
- [DESIGN_PRINCIPLES.md](docs/backend/architecture/DESIGN_PRINCIPLES.md) — SOLID, DRY, YAGNI, KISS
- [GHERKIN_CONVENTIONS.md](docs/backend/architecture/GHERKIN_CONVENTIONS.md) — NFR tags, coverage rules
- [GHERKIN_TAGS.md](docs/backend/architecture/GHERKIN_TAGS.md) — Standard tag reference
- [SECURITY_AUTH_PATTERNS.md](docs/backend/architecture/SECURITY_AUTH_PATTERNS.md)
- [TECH_STACK.md](docs/backend/architecture/TECH_STACK.md)
- [TESTING.md](docs/backend/architecture/TESTING.md)
- [AGENT_ARCHITECTURE.md](docs/backend/architecture/AGENT_ARCHITECTURE.md) — AI agent design patterns (LangGraph, tools, evaluation)
- [ERROR_MAPPING.md](docs/backend/architecture/ERROR_MAPPING.md) — Domain exception to HTTP status mapping
- [OBSERVABILITY_PORT_CONTRACT.md](docs/backend/architecture/OBSERVABILITY_PORT_CONTRACT.md) — Observability port interface
- [CROSS_CUTTING_CONCERNS.md](docs/backend/architecture/CROSS_CUTTING_CONCERNS.md) — DTOs, validation, pagination, timestamps
- [ADR/TEMPLATE.md](docs/backend/architecture/ADR/TEMPLATE.md)

### Backend (GenAI Contracts — Level 5)

- [LLM_GATEWAY_CONTRACT.md](docs/backend/architecture/LLM_GATEWAY_CONTRACT.md) — LiteLLM as sole LLM gateway, provider abstraction, fallback, cost tracking
- [OBSERVABILITY_LLM_CONTRACT.md](docs/backend/architecture/OBSERVABILITY_LLM_CONTRACT.md) — OpenLLMetry (telemetry emission) + Langfuse (trace storage, prompt versioning)
- [GUARDRAILS_CONTRACT.md](docs/backend/architecture/GUARDRAILS_CONTRACT.md) — NeMo Guardrails (conversational safety) + Guardrails AI (structured output validation)
- [EVALUATION_LLM_CONTRACT.md](docs/backend/architecture/EVALUATION_LLM_CONTRACT.md) — DeepEval (quality), Promptfoo (adversarial), RAGAS (retrieval)

### Backend (Practical Guides — Level 5)

- [litellm-setup.md](docs/backend/guides/litellm-setup.md) — LiteLLM proxy config, model aliases, fallback chains
- [openllmetry-setup.md](docs/backend/guides/openllmetry-setup.md) — Auto-instrumentation, export to Langfuse
- [langfuse-integration.md](docs/backend/guides/langfuse-integration.md) — Trace viewing, prompt management, dashboards
- [deepeval-usage.md](docs/backend/guides/deepeval-usage.md) — Writing DeepEval test cases, metrics, CI integration
- [promptfoo-usage.md](docs/backend/guides/promptfoo-usage.md) — Adversarial configs, red-team suites
- [nemo-guardrails-setup.md](docs/backend/guides/nemo-guardrails-setup.md) — Colang dialog definitions, rail configs
- [guardrails-ai-setup.md](docs/backend/guides/guardrails-ai-setup.md) — Guard definitions, validator config
- [ragas-evaluation.md](docs/backend/guides/ragas-evaluation.md) — RAG-specific metrics, dataset preparation

### UI (Shared)

- [MVVM_CONTRACT.md](docs/ui/architecture/MVVM_CONTRACT.md) — framework-agnostic MVVM contract
- [ADR/TEMPLATE.md](docs/ui/architecture/ADR/TEMPLATE.md)

### React UI

- [COMPONENT_CONVENTIONS.md](docs/ui/architecture/react/COMPONENT_CONVENTIONS.md)
- [STATE_MANAGEMENT.md](docs/ui/architecture/react/STATE_MANAGEMENT.md) — React Query + Zustand
- [TECH_STACK.md](docs/ui/architecture/react/TECH_STACK.md)

### Angular UI

- [COMPONENT_CONVENTIONS.md](docs/ui/architecture/angular/COMPONENT_CONVENTIONS.md)
- [STATE_MANAGEMENT.md](docs/ui/architecture/angular/STATE_MANAGEMENT.md) — TanStack Angular Query + Signals
- [TECH_STACK.md](docs/ui/architecture/angular/TECH_STACK.md)

---

## Evaluation Reference

### Standards (All Levels)

- [eval_criteria.md](docs/backend/evaluation/eval_criteria.md) — FIRST, 7 Code Virtues, LLM eval, scoring model
- [FIRST_SCORING_RUBRIC.md](docs/backend/evaluation/FIRST_SCORING_RUBRIC.md) — 1-5 scoring definitions per FIRST principle
- [VIRTUE_SCORING_RUBRIC.md](docs/backend/evaluation/VIRTUE_SCORING_RUBRIC.md) — 1-5 scoring definitions per virtue
- [EVAL_STACK.md](docs/backend/evaluation/EVAL_STACK.md) — Evaluation tooling by environment (Langfuse, DeepEval, Promptfoo, RAGAS, home-grown)

### Schemas

- [eval_criteria.schema.json](governance/backend/schemas/eval_criteria.schema.json) — Validates feature eval_criteria.yaml (includes L5 eval_class values)
- [evaluation_prediction.schema.json](governance/schemas/evaluation_prediction.schema.json) — Schema for plan.md prediction blocks (includes optional L5 llm_evaluation section)
- [guardrails_config.schema.json](governance/backend/schemas/guardrails_config.schema.json) — Validates guardrails configuration (L5)

### UI Evaluation

- [eval_criteria.md](docs/ui/evaluation/eval_criteria.md) — FIRST, accessibility, E2E coverage
- [FIRST_SCORING_RUBRIC.md](docs/ui/evaluation/FIRST_SCORING_RUBRIC.md) — UI-adapted FIRST scoring
- [VIRTUE_SCORING_RUBRIC.md](docs/ui/evaluation/VIRTUE_SCORING_RUBRIC.md) — UI-adapted virtue scoring
- [eval_criteria.schema.json](governance/ui/schemas/eval_criteria.schema.json)

### Evaluation by Level

| Level | What's Evaluated | Tools |
|-------|-----------------|-------|
| L3 | Architecture-boundary compliance + commit format + lint/security (codebase-wide; no per-feature artifacts) | `l3-quality-gate.yml` (import-linter + sonar/snyk + commit-format) |
| L4 | L3 + spec completeness, Gherkin structure, NFR coverage, FIRST + 7 Virtue scores, eval_criteria schema | `govkit validate` + `quality-gate.yml` + `eval-gate.yml` |
| L5 | L4 + LLM quality (DeepEval), adversarial safety (Promptfoo), retrieval quality (RAGAS), guardrails config, multi-agent topology | `govkit validate` + deepeval-gate + promptfoo-gate + guardrails-check + multi-agent-gate |

---

## Getting Help

- **Issues and feature requests:** [github.com/Accelerated-Innovation/governed-ai-delivery/issues](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues)
- **Contributing:** See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, project structure, and contribution guidelines
- **Changelog:** See [CHANGELOG.md](CHANGELOG.md) for release history
- **CI Reference:** See [ci/README.md](ci/README.md) for what's enforced vs predicted in each CI gate

---

## License

Copyright 2026 Accelerated Innovation

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.

---

## Glossary

| Term | Definition |
|---|---|
| **Agent** | The AI coding tool (Claude Code, GitHub Copilot, or OpenAI Codex) that reads governance artifacts and generates code |
| **Rule** (Claude Code) | A path-scoped `.md` file in `.claude/rules/` that loads automatically when editing files matching its path |
| **Skill** (Claude Code) | A reusable prompt in `.claude/skills/` invoked via slash command (e.g., `/architecture-preflight`) |
| **Instruction** (Copilot) | A path-scoped `.md` file in `.github/instructions/` — Copilot equivalent of a rule |
| **Skill** (Copilot) | A reusable task in `.github/skills/` invoked via slash command — open agent skills standard |
| **AGENTS.md** (Codex) | A markdown instructions file read by Codex. A root `AGENTS.md` applies globally; nested `AGENTS.md` files at layer directories scope rules to that subtree via directory walk |
| **Skill** (Codex) | A `SKILL.md` under `.agents/skills/<name>/` invoked via `$skill-name` |
| **Port** | An interface defining a contract between layers (inbound ports for API entry, outbound ports for infrastructure) |
| **Adapter** | An implementation of a port that connects to infrastructure (database, external API, message queue) |
| **Domain** | Business logic that has no dependencies on frameworks or infrastructure |
| **FIRST** | Test quality framework — Fast, Isolated, Repeatable, Self-verifying, Timely (scored 1–5) |
| **7 Virtues** | Code quality framework — Working, Unique, Simple, Clear, Easy, Developed, Brief (scored 1–5) |
| **ADR** | Architecture Decision Record — documents and gates architectural changes |
| **NFR** | Non-Functional Requirement — performance, security, availability, etc. |
| **Evaluation Prediction** | Predicted FIRST and Virtue scores in `plan.md` — must average >= 4.0 before implementation |
| `govkit validate` | CLI command that checks all features for governance compliance (artifact completeness, thresholds) |
| `/architecture-preflight` | Agent skill that validates a feature against architecture contracts before planning (`$architecture-preflight` in Codex) |
| `/genai-preflight` | L5 agent skill that validates LLM gateway, observability, guardrails, and evaluation decisions (`$genai-preflight` in Codex) |
| `/eval-suite-planning` | L5 agent skill that plans DeepEval, Promptfoo, and RAGAS test suites (`$eval-suite-planning` in Codex) |
| **LiteLLM** | L5 sole LLM gateway — model routing, provider abstraction, fallback, cost tracking |
| **OpenLLMetry** | L5 LLM telemetry emission standard (OpenTelemetry for LLMs) |
| **Langfuse** | Trace storage, prompt versioning, and production evaluation visibility |
| **DeepEval** | L5 LLM quality evaluation — faithfulness, relevancy, hallucination metrics |
| **Promptfoo** | L5 adversarial and regression testing — jailbreak, injection, safety |
| **RAGAS** | L5 retrieval-specific evaluation — context recall, precision (RAG pipelines only) |
| **NeMo Guardrails** | L5 conversational safety — dialog flow control, topic boundaries, jailbreak prevention |
| **Guardrails AI** | L5 structured output validation — JSON schema enforcement on LLM responses |

---

## Resources

### Video Demo (COMING SOON)

[Watch govkit apply on a FastAPI project — GitHub Copilot Prompts Explained]()
