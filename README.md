# Governed AI Delivery

AI coding agents are powerful — but without constraints, they drift. They invent architecture, skip tests, ignore NFRs, and make decisions that belong to your team. **Governed AI Delivery** puts the agent inside a governed system where your architecture contracts, acceptance criteria, and evaluation thresholds are the source of truth, not the agent's training data.

Install it into any project with one command. The agent gets the rules. You stay in control.

---

A spec-driven, evaluation-governed scaffolding kit for AI-assisted software delivery. Supports multiple AI coding agents and project types with clean separation of concerns.

Every feature is:

* Defined with **Gherkin acceptance criteria** tagged to NFR categories
* Constrained with **fully populated NFRs** (no TBD entries permitted)
* Governed by **evaluation criteria** validated against a JSON Schema
* Planned through **Architecture Preflight + Implementation Plan prompts**
* Enforced by **CI gates, quality rules, and evaluation thresholds**

The AI agent operates inside a governed system. Architecture, evaluation, and feature artifacts are the source of truth — not the agent.

---

# Supported Agents

govkit ships two agents, each supporting multiple project types through variant selection at install time:

| Agent | AI Tool | Installs To |
|---|---|---|
| `claude-code` | Claude Code | `CLAUDE.md`, `.claude/rules/`, `.claude/skills/` |
| `copilot` | GitHub Copilot | `.github/copilot-instructions.md`, `.github/instructions/`, `.github/prompts/` |

Both agents support the same variant options:

| Option | Choices | Default |
|---|---|---|
| `--type` | `api`, `cli` | `api` |
| `--ui` | `none`, `react`, `angular` | `none` |
| `--ci` | `github`, `azure` | `github` |

---

# Quickstart

## 1. Install govkit

```bash
pip install git+https://github.com/Accelerated-Innovation/governed-ai-delivery.git
```

## 2. List available agents

```bash
govkit list
```

## 3. Apply to your project

From your project root, run `govkit apply` and answer the prompts:

```bash
govkit apply --agent claude-code --target .
```

Or specify all options explicitly:

```bash
# Python API backend + React UI + GitHub Actions
govkit apply --agent claude-code --type api --ui react --ci github --target .

# Python CLI tool + Azure DevOps (no UI)
govkit apply --agent copilot --type cli --ui none --ci azure --target .

# API backend only + GitHub Actions
govkit apply --agent copilot --type api --ui none --ci github --target .
```

This installs agent-specific config files, architecture docs, feature starters, governance schemas, and CI templates into your project.

## 4. Customize Your Governance Artifacts — REQUIRED

> **This step is not optional.** The installed `docs/` files are authoritative starting points — they reflect sound defaults, but they are written for a generic project. Your agent will treat them as law. If you skip this step, the agent will govern your project against someone else's architecture decisions.

Before writing a single line of feature code, review and update the following to match your project:

**Backend projects (API or CLI)** — review and update:
- `docs/backend/architecture/TECH_STACK.md` — replace with your actual approved libraries, frameworks, and versions
- `docs/backend/architecture/ARCH_CONTRACT.md` — confirm the hexagonal layer names and boundaries match your codebase structure
- `docs/backend/architecture/API_CONVENTIONS.md` (API) or `docs/backend/architecture/CLI_CONVENTIONS.md` (CLI) — update conventions to match your project standards
- `docs/backend/architecture/SECURITY_AUTH_PATTERNS.md` — replace with your actual auth provider, token pattern, and scope conventions
- `docs/backend/evaluation/eval_criteria.md` — confirm FIRST and 7 Virtue thresholds are appropriate for your team's standards

**React UI projects** — review and update:
- `docs/ui/architecture/react/TECH_STACK.md` — confirm your React version, state management libraries, and testing stack
- `docs/ui/architecture/react/COMPONENT_CONVENTIONS.md` — update to reflect your project's folder structure and naming conventions
- `docs/ui/evaluation/eval_criteria.md` — confirm accessibility standard and FIRST thresholds

**Angular UI projects** — review and update:
- `docs/ui/architecture/angular/TECH_STACK.md` — confirm your Angular version, TanStack Query setup, and testing stack
- `docs/ui/architecture/angular/COMPONENT_CONVENTIONS.md` — update to reflect your project's folder structure and naming conventions
- `docs/ui/evaluation/eval_criteria.md` — confirm accessibility standard and FIRST thresholds

These files are the source of truth for your AI agent. The agent reads them before every planning and implementation step. Keep them accurate and up to date as your project evolves.

## 5. Validate governance compliance (anytime)

```bash
govkit validate --target .
```

Checks all features for: required artifacts, Gherkin structure, NFR completeness, evaluation prediction thresholds, and tag coverage.

---

# Working With the Agent — Step by Step

Once govkit is installed, here is how you interact with the agent to deliver a feature. This lifecycle applies to **every feature**, regardless of project type or agent.

## Step 1: Create a Feature Folder

Copy the appropriate starter to a new folder under `features/`:

```bash
# Backend API feature
cp -r features/starter_backend/ features/my_feature/

# CLI tool feature
cp -r features/starter_cli/ features/my_feature/

# UI feature (React or Angular)
cp -r features/starter_ui/ features/my_feature/
```

## Step 2: Write Your Acceptance Criteria

Edit `features/my_feature/acceptance.feature` with your Gherkin scenarios:

- Write happy path and failure/edge case scenarios
- Tag NFR scenarios with `@nfr-performance`, `@nfr-security`, etc.
- Tag E2E scenarios with `@e2e` (UI projects)
- Add `@contract` scenarios if the feature produces shared artifacts

## Step 3: Complete Your NFRs

Edit `features/my_feature/nfrs.md` — replace every TBD entry with concrete requirements. The agent will refuse to proceed if any TBD entries remain.

## Step 4: Run Architecture Preflight

Ask the agent to validate your feature against the architecture contracts:

| Agent | Command |
|---|---|
| Claude Code | `/project:architecture-preflight my_feature` |
| Copilot | `/architecture-preflight` (with feature context) |

The agent produces `architecture_preflight.md` covering boundary analysis, security impact, evaluation impact, and whether an ADR is needed. If an ADR is required, create it next:

| Agent | Command |
|---|---|
| Claude Code | `/project:adr-author my_feature` |
| Copilot | `/adr-author` |

## Step 5: Generate the Plan

Ask the agent to create the implementation plan:

| Agent | Command |
|---|---|
| Claude Code | `/project:spec-planning my_feature` |
| Copilot | `/spec-planning` |

The agent generates `plan.md` and `eval_criteria.yaml`. The plan includes:
- Increments with deliverables and tests
- An **Evaluation Compliance Summary** predicting FIRST and 7 Virtue scores
- Each increment sized as a single committable unit (~300 lines)

**The agent will not proceed if predicted averages are below 4.0.**

## Step 6: Review the Implementation Plan

Ask the agent to break the plan into a detailed task checklist:

| Agent | Command |
|---|---|
| Claude Code | `/project:implementation-plan my_feature` |
| Copilot | `/implementation-plan` |

Review and approve before implementation begins.

## Step 7: Implement Incrementally

Work through the plan one increment at a time. For each increment:

1. The agent writes production code respecting architecture boundaries
2. The agent writes tests (unit, integration, contract as needed)
3. You review and commit: `feat(my_feature): increment 1 — <name>`
4. Move to the next increment

**Do not skip increments or combine multiple increments into one commit.**

## Step 8: Push and Merge

Open a PR. CI gates automatically run:

- Schema validation of `eval_criteria.yaml`
- FIRST and 7 Virtue prediction completeness
- Unit, component, and E2E tests
- Architecture boundary enforcement
- Security scan and quality gates
- Accessibility checks (UI projects)

All gates must pass before merge.

---

# Feature Workflow — Backend API

The workflow follows the step-by-step guide above. Key details for API projects:

**Architecture:** Hexagonal Architecture — ports and adapters. API routes are the inbound adapter layer. See `docs/backend/architecture/API_CONVENTIONS.md`.

**Layer rules** load automatically when editing files:
- `api.md` for `**/api/**`
- `services.md` for `**/services/**`
- `ports.md` for `**/ports/**`
- `adapters.md` for `**/adapters/**`
- `security.md` for `**/security/**` and `**/auth/**`

**CI gates:** `ci/github/quality-gate.yml`, `ci/github/eval-gate.yml` (or `ci/azure/` for Azure DevOps)

---

# Feature Workflow — CLI

Same step-by-step workflow. Key details for CLI projects:

**Architecture:** Hexagonal Architecture — CLI commands are the inbound adapter layer (same position as API routes). See `docs/backend/architecture/CLI_CONVENTIONS.md`.

**Layer rules** load automatically when editing files:
- `cli.md` for `**/cli/**` and `**/commands/**`
- `services.md` for `**/services/**`
- `ports.md` for `**/ports/**`
- `adapters.md` for `**/adapters/**`
- `security.md` for `**/security/**` and `**/auth/**`

**CI gates:** Same backend gates — `ci/github/quality-gate.yml`, `ci/github/eval-gate.yml` (or `ci/azure/`)

---

# Feature Workflow — React UI

Same step-by-step workflow. Key details for React UI projects:

**Architecture:** MVVM with vertical slice feature structure. Layer order is API -> ViewModel -> View. See `docs/ui/architecture/MVVM_CONTRACT.md`.

**Layer rules** load automatically:
- `components.md` for View layer
- `viewmodel.md` for hooks and store
- `api.md` for API client functions
- `accessibility.md` for accessibility concerns

**Implementation order:** API functions -> React Query hooks -> Zustand stores -> Components -> E2E tests

**CI gates:** `ci/github/ui-quality-gate.yml`, `ci/github/ui-eval-gate.yml` (or `ci/azure/`)

---

# Feature Workflow — Angular UI

Same step-by-step workflow. Key details for Angular UI projects:

**Architecture:** MVVM with vertical slice feature structure. Standalone components with `OnPush`. See `docs/ui/architecture/MVVM_CONTRACT.md`.

**Layer rules** load automatically (same as React, with Angular-specific content).

**Implementation order:** API functions -> TanStack Query inject functions -> Signal stores -> Standalone components -> E2E tests

**CI gates:** `ci/github/ui-quality-gate.yml`, `ci/github/ui-eval-gate.yml` (or `ci/azure/`)

---

# Repository Structure

```
governed-ai-delivery/
├── agents/
│   ├── claude-code/                  # Claude Code agent (variant-based)
│   │   ├── manifest.json            # Variant options: type, ui, ci
│   │   ├── claude-md/               # CLAUDE.md variants per project type
│   │   ├── rules/                   # Path-scoped rules (backend/, cli/, ui-react/, ui-angular/)
│   │   └── skills/                  # Skills (backend/, ui/)
│   └── copilot/                     # Copilot agent (variant-based)
│       ├── manifest.json
│       ├── copilot-instructions/    # Instruction variants per project type
│       ├── instructions/            # Path-scoped instructions (backend/, cli/, ui-react/, ui-angular/)
│       └── prompts/                 # Chat prompts (backend/, ui/)
├── cli/
│   ├── govkit.py                    # CLI — apply, list, validate
│   └── validate.py                  # Governance compliance checker
├── docs/
│   ├── backend/
│   │   ├── architecture/            # ARCH_CONTRACT, BOUNDARIES, API_CONVENTIONS, CLI_CONVENTIONS, ADR/, etc.
│   │   └── evaluation/              # eval_criteria.md — FIRST, 7 Virtues, scoring model
│   └── ui/
│       ├── architecture/
│       │   ├── MVVM_CONTRACT.md     # Shared contract — framework-agnostic
│       │   ├── ADR/TEMPLATE.md
│       │   ├── react/               # COMPONENT_CONVENTIONS, STATE_MANAGEMENT, TECH_STACK
│       │   └── angular/             # COMPONENT_CONVENTIONS, STATE_MANAGEMENT, TECH_STACK
│       └── evaluation/              # eval_criteria.md — FIRST, accessibility, E2E
├── features/
│   ├── starter_backend/             # API backend starter (5 artifacts)
│   ├── starter_cli/                 # CLI project starter (5 artifacts)
│   ├── starter_ui/                  # UI starter (5 artifacts)
│   ├── schema_contract_example/     # Worked backend example
│   └── ui_task_dashboard/           # Worked React UI example
├── governance/
│   ├── backend/
│   │   ├── schemas/                 # eval_criteria.schema.json
│   │   └── templates/               # architecture_preflight.md, plan.md
│   └── ui/
│       ├── schemas/                 # eval_criteria.schema.json (UI)
│       └── templates/               # architecture_preflight.md, plan.md (UI)
└── ci/
    ├── github/                      # GitHub Actions CI templates
    │   ├── quality-gate.yml         # Schema validation, boundaries, SonarQube, Snyk
    │   ├── eval-gate.yml            # Eval prediction check, LLM eval, regression gate
    │   ├── ui-quality-gate.yml      # Type check, ESLint, component tests, jest-axe, bundle size
    │   └── ui-eval-gate.yml         # Eval prediction check, Playwright E2E, axe scans
    └── azure/                       # Azure DevOps CI equivalents
        ├── quality-gate.yml
        ├── eval-gate.yml
        ├── ui-quality-gate.yml
        └── ui-eval-gate.yml
```

---

# Architecture — Backend

* [ARCH_CONTRACT.md](docs/backend/architecture/ARCH_CONTRACT.md) — Hexagonal Architecture contract
* [BOUNDARIES.md](docs/backend/architecture/BOUNDARIES.md) — Layer dependency rules
* [API_CONVENTIONS.md](docs/backend/architecture/API_CONVENTIONS.md) — FastAPI conventions
* [CLI_CONVENTIONS.md](docs/backend/architecture/CLI_CONVENTIONS.md) — Click/Typer conventions
* [DESIGN_PRINCIPLES.md](docs/backend/architecture/DESIGN_PRINCIPLES.md) — SOLID, DRY, YAGNI, KISS
* [GHERKIN_CONVENTIONS.md](docs/backend/architecture/GHERKIN_CONVENTIONS.md) — NFR tags, coverage rules
* [SECURITY_AUTH_PATTERNS.md](docs/backend/architecture/SECURITY_AUTH_PATTERNS.md)
* [TECH_STACK.md](docs/backend/architecture/TECH_STACK.md)
* [TESTING.md](docs/backend/architecture/TESTING.md)
* [ADR/TEMPLATE.md](docs/backend/architecture/ADR/TEMPLATE.md)

# Architecture — UI (Shared)

* [MVVM_CONTRACT.md](docs/ui/architecture/MVVM_CONTRACT.md) — framework-agnostic MVVM contract
* [ADR/TEMPLATE.md](docs/ui/architecture/ADR/TEMPLATE.md)

# Architecture — React UI

* [COMPONENT_CONVENTIONS.md](docs/ui/architecture/react/COMPONENT_CONVENTIONS.md)
* [STATE_MANAGEMENT.md](docs/ui/architecture/react/STATE_MANAGEMENT.md) — React Query + Zustand
* [TECH_STACK.md](docs/ui/architecture/react/TECH_STACK.md)

# Architecture — Angular UI

* [COMPONENT_CONVENTIONS.md](docs/ui/architecture/angular/COMPONENT_CONVENTIONS.md)
* [STATE_MANAGEMENT.md](docs/ui/architecture/angular/STATE_MANAGEMENT.md) — TanStack Angular Query + Signals
* [TECH_STACK.md](docs/ui/architecture/angular/TECH_STACK.md)

---

# Evaluation

**Backend**
* [eval_criteria.md](docs/backend/evaluation/eval_criteria.md) — FIRST, 7 Code Virtues, LLM eval, scoring model
* [eval_criteria.schema.json](governance/backend/schemas/eval_criteria.schema.json)
* [EVAL_STACK.md](docs/backend/evaluation/EVAL_STACK.md) — LangSmith, Arize, home-grown framework

**UI**
* [eval_criteria.md](docs/ui/evaluation/eval_criteria.md) — FIRST, accessibility, E2E coverage
* [eval_criteria.schema.json](governance/ui/schemas/eval_criteria.schema.json)

---

# License

Copyright 2026 Accelerated Innovation

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.

---

# Resources

[Copilot Prompts Explained — Watch on YouTube](https://youtu.be/0XoXNG65rfg?si=sWwyYr84zgNr5mRz)
