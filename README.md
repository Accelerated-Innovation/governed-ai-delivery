# Governed AI Delivery

AI coding agents are powerful — but without constraints, they drift. They invent architecture, skip tests, ignore NFRs, and make decisions that belong to your team. **Governed AI Delivery** puts the agent inside a governed system where your architecture contracts, acceptance criteria, and evaluation thresholds are the source of truth, not the agent's training data.

Install it into any project with one command. The agent gets the rules. You stay in control.

---

A spec-driven, evaluation-governed scaffolding kit for AI-assisted software delivery. Supports multiple AI coding agents and project types with clean separation of concerns.

## Maturity Levels

govkit supports three maturity levels, allowing teams to adopt incrementally:

| Level | Name | What You Get |
|-------|------|-------------|
| **Level 3** | Spec-Driven Development | Spec-first, test-first workflow. 3 artifacts per feature (acceptance.feature, nfrs.md, plan.md). Generic agent rules. Basic CI gates. No architecture changes imposed. |
| **Level 4** | Governed AI Delivery | Full governance. 5 artifacts per feature (adds eval_criteria.yaml, architecture_preflight.md). Architecture contracts, FIRST/Virtues scoring, evaluation prediction thresholds, boundary enforcement, path-scoped rules. |
| **Level 5** | GenAI Operations | Everything in L4 plus governed GenAI tooling: LiteLLM (model routing), OpenLLMetry + Langfuse (observability), DeepEval + Promptfoo + RAGAS (evaluation), NeMo Guardrails + Guardrails AI (runtime safety). LLM-specific NFRs, CI evaluation gates, and adversarial testing. |

**Start at Level 3** if your team wants spec-driven development without changing their existing project structure. **Move to Level 4** when ready for full architectural governance and evaluation scoring. **Move to Level 5** when building LLM-powered features that need governed model routing, evaluation, and safety.

### Level 3 — Spec-Driven Development

Every feature is:

* Defined with **Gherkin acceptance criteria** tagged to NFR categories
* Constrained with **fully populated NFRs** (no TBD entries permitted)
* Planned with **increments that list tests before implementation** (test-first)
* Enforced by **basic CI gates** (artifact checks, commit format, lint, tests)

### Level 4 — Governed AI Delivery

Everything in Level 3, plus:

* Governed by **evaluation criteria** validated against a JSON Schema
* Planned through **Architecture Preflight + Implementation Plan prompts**
* Enforced by **CI gates, quality rules, and evaluation thresholds**
* Bounded by **hexagonal architecture contracts** with import-linter enforcement

### Level 5 — GenAI Operations

Everything in Level 4, plus:

* Routed through **LiteLLM** as the sole LLM gateway (model routing, fallback, cost tracking)
* Observed via **OpenLLMetry + Langfuse** (LLM-specific telemetry, trace storage, prompt versioning)
* Evaluated with **DeepEval** (quality metrics), **Promptfoo** (adversarial testing), and **RAGAS** (retrieval evaluation)
* Guarded by **NeMo Guardrails** (conversational safety) and **Guardrails AI** (structured output validation)
* Extended with **LLM-specific NFRs** (latency, cost, fallback, safety) and **3 additional CI gates**

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
| `--level` | `3`, `4`, `5` | `4` |
| `--type` | `api`, `cli` | `api` |
| `--ui` | `none`, `react`, `angular` | `none` |
| `--ci` | `github`, `azure` | `github` |

---

# Key Concepts

Before diving in, here are the foundational ideas behind this toolkit:

**Hexagonal Architecture (Ports & Adapters)** — Your domain logic lives at the center, isolated from infrastructure. Inbound adapters (API routes, CLI commands) call inbound ports. Outbound ports define contracts that adapters (databases, APIs, message queues) implement. Domain code never imports infrastructure libraries.

**MVVM (UI projects)** — Model-View-ViewModel. Components (View) render UI. Hooks or inject functions (ViewModel) provide data and actions. API functions (Model) call the backend. Components never call APIs directly.

**FIRST Principles** — Test quality framework. Tests must be **F**ast, **I**solated, **R**epeatable, **S**elf-verifying, and **T**imely. Each principle is scored 1–5 with a minimum average of 4.0.

**7 Code Virtues** — Implementation quality framework. Code must be **Working**, **Unique**, **Simple**, **Clear**, **Easy** to maintain, **Developed** (tested and clean), and **Brief**. Each virtue is scored 1–5 with a minimum average of 4.0.

**Gherkin Acceptance Criteria** — Features are specified using Given/When/Then scenarios. Scenarios are tagged with NFR categories (`@nfr-performance`, `@nfr-security`) to ensure non-functional requirements have test coverage.

**Governed Development** — The agent reads architecture contracts, evaluation criteria, and feature specs before generating code. CI gates enforce compliance. The agent proposes; your governance artifacts decide.

---

# Prerequisites

- **Python 3.11+** — required to install and run govkit
- **pip** — for installation (`pip install git+...`)
- **git** — govkit is installed from a git repository
- **An AI coding agent** — Claude Code or GitHub Copilot (govkit provides the configuration, not the agent itself)

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
# Level 3: Spec-driven development (no architecture changes imposed)
govkit apply --agent claude-code --level 3 --type api --ui none --ci github --target .

# Level 4: Full governed AI delivery (default)
govkit apply --agent claude-code --level 4 --type api --ui react --ci github --target .

# Level 5: GenAI operations (LLM routing, evaluation, guardrails)
govkit apply --agent claude-code --level 5 --type api --ui none --ci github --target .

# Python CLI tool + Azure DevOps (no UI)
govkit apply --agent copilot --type cli --ui none --ci azure --target .

# API backend only + GitHub Actions
govkit apply --agent copilot --type api --ui none --ci github --target .
```

A `.govkit` marker file is written to your project root, tracking the applied level and options. This enables `govkit init` and `govkit validate` to auto-detect your level.

This installs agent-specific config files, architecture docs, feature starters, governance schemas, and CI templates into your project.

When using interactive mode (no `--type`, `--ui`, `--ci` flags), you'll see prompts like:

```
$ govkit apply --agent claude-code --target .

Applying govkit agent 'claude-code' to /path/to/your/project

  Project type? [api / cli] (default: api): api
  UI framework? [none / react / angular] (default: none): react
  CI platform? [github / azure] (default: github): github

  Configuration: {'type': 'api', 'ui': 'react', 'ci': 'github'}

Agent files:
  copied  /path/to/your/project/CLAUDE.md
  copied  /path/to/your/project/.claude/rules/api.md
  ...
```

### Verify Installation

After applying, your project should contain:

```
your-project/
├── CLAUDE.md (or .github/copilot-instructions.md)
├── .claude/rules/ (or .github/instructions/)
│   ├── api.md, services.md, ports.md, adapters.md, security.md
│   └── (UI rules if --ui was specified)
├── .claude/skills/ (or .github/prompts/)
│   ├── architecture-preflight/, spec-planning/, implementation-plan/, adr-author/
│   └── (UI skills if --ui was specified)
├── docs/
│   ├── backend/architecture/   — ARCH_CONTRACT, API_CONVENTIONS, TECH_STACK, etc.
│   └── backend/evaluation/     — eval_criteria.md, scoring rubrics
├── features/
│   ├── starter_backend/        — template for new features (5 artifacts)
│   └── schema_contract_example/ — worked example
├── governance/
│   └── backend/schemas/        — eval_criteria.schema.json
└── ci/
    └── github/ (or azure/)     — quality-gate.yml, eval-gate.yml
```

If `--ui react` or `--ui angular` was specified, you'll also see `docs/ui/`, `features/starter_ui/`, `governance/ui/`, and UI-specific CI pipelines.

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

Validation is level-aware. Level 3 checks: 3 required artifacts, Gherkin structure, NFR completeness, and tag coverage. Level 4 adds: eval_criteria.yaml schema, evaluation prediction thresholds. The level is auto-detected from `.govkit` or can be overridden:

```bash
govkit validate --level 3 --target .
```

---

# Working With the Agent — Step by Step

Once govkit is installed, here is how you interact with the agent to deliver a feature. This lifecycle applies to **every feature**, regardless of project type or agent.

## Step 1: Create a Feature Folder

Use `govkit init` to create a feature from the appropriate starter:

```bash
govkit init my_feature --target .
```

Or specify the starter type explicitly:

```bash
govkit init my_feature --starter backend --target .
```

The command auto-detects your maturity level from `.govkit` and selects the appropriate starter template. Level 3 starters have 3 artifacts; Level 4 starters have 5. You can override with `--level 3` or `--level 4`.

For Level 4 projects, each starter's `eval_criteria.yaml` includes mode selection instructions at the top. Set the `mode` field to match your feature type: `llm` (LLM generation/retrieval), `deterministic` (pure logic), or `none` (configuration artifacts). If the mode is `deterministic` or `none`, delete the `llm_evaluation` section.

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
| Claude Code | `/architecture-preflight my_feature` |
| Copilot | `/architecture-preflight` (with feature context) |

The agent produces `architecture_preflight.md` covering boundary analysis, security impact, evaluation impact, and whether an ADR is needed. If an ADR is required, create it next:

| Agent | Command |
|---|---|
| Claude Code | `/adr-author my_feature` |
| Copilot | `/adr-author` |

## Step 5: Generate the Plan

Ask the agent to create the implementation plan:

| Agent | Command |
|---|---|
| Claude Code | `/spec-planning my_feature` |
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
| Claude Code | `/implementation-plan my_feature` |
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

# Directory Roles

Understanding the separation between `docs/`, `governance/`, and `features/`:

| Directory | Contains | Who maintains it | When to update |
|---|---|---|---|
| `docs/` | Human-readable architecture contracts and evaluation standards | Architect / tech lead | When architecture decisions change, new patterns are adopted, or standards evolve |
| `governance/` | Machine-readable schemas (JSON Schema) and templates (Markdown) | Architect / govkit maintainer | When artifact structure changes or new validation rules are added |
| `features/` | Feature specifications — one folder per feature with 5 required artifacts | Developer / AI agent | Every feature — create from starter, populate, and plan before implementing |

The AI agent reads `docs/` to understand what rules to follow, validates against `governance/` schemas, and produces artifacts in `features/`.

---

# Interpreting Validation Failures

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

# Troubleshooting & FAQ

**Q: `govkit: command not found` after installation**
A: Ensure your Python scripts directory is on your PATH. Try `python -m cli.govkit` as a fallback, or reinstall with `pip install --user git+...`.

**Q: `govkit apply` fails with "no agent found"**
A: Check that you're using a valid agent name (`claude-code` or `copilot`). Run `govkit list` to see available agents.

**Q: The agent ignores my architecture rules**
A: Verify the rules files were copied to the correct location (`.claude/rules/` or `.github/instructions/`). Check that file paths match what the agent expects — Claude Code loads rules based on the file path you're editing.

**Q: How do I update to a newer version of govkit?**
A: Run `pip install --upgrade git+https://github.com/Accelerated-Innovation/governed-ai-delivery.git`. Then re-run `govkit apply` — it will skip files that already exist. To force update a specific file, delete it first.

**Q: Can I use govkit on an existing project with existing code?**
A: Yes. `govkit apply` copies governance artifacts into your project without modifying existing code. You may need to adjust `docs/backend/architecture/ARCH_CONTRACT.md` and other docs to reflect your existing architecture rather than the defaults.

**Q: What if my architecture doesn't match the Hexagonal defaults?**
A: Customize the architecture docs after install. The agent follows whatever `ARCH_CONTRACT.md` says — if your project uses a different pattern, document it there. Consider creating an ADR explaining the architectural choice.

**Q: Can I use both Claude Code and Copilot in the same project?**
A: Yes. Run `govkit apply` once for each agent. They install to different paths (`.claude/` vs `.github/`) and share the same `docs/`, `governance/`, and `features/` artifacts. Both agents read the same architecture contracts.

**Q: How do I add a new NFR category?**
A: Add the category as a `## Heading` in your feature's `nfrs.md`, add corresponding `@nfr-<category>` tags to acceptance scenarios, and update `cli/validate.py`'s `category_to_tag` mapping if you want automated tag coverage validation.

**Q: The CI pipeline fails because SonarQube/Snyk isn't configured**
A: These tools are optional. If your team doesn't use them, remove or comment out those jobs from the CI pipeline files. See `ci/README.md` for details on required secrets.

**Q: What does "thresholds_met: false" mean in my plan?**
A: Your predicted FIRST or Virtue average is below 4.0, or a predicted accessibility violation count is above zero. Revise the plan — simplify the design, improve test strategy, or split large increments before proceeding.

---

# Architecture — Backend

**Core (Level 4)**
* [ARCH_CONTRACT.md](docs/backend/architecture/ARCH_CONTRACT.md) — Hexagonal Architecture contract
* [BOUNDARIES.md](docs/backend/architecture/BOUNDARIES.md) — Layer dependency rules
* [API_CONVENTIONS.md](docs/backend/architecture/API_CONVENTIONS.md) — FastAPI conventions
* [CLI_CONVENTIONS.md](docs/backend/architecture/CLI_CONVENTIONS.md) — Click/Typer conventions
* [DESIGN_PRINCIPLES.md](docs/backend/architecture/DESIGN_PRINCIPLES.md) — SOLID, DRY, YAGNI, KISS
* [GHERKIN_CONVENTIONS.md](docs/backend/architecture/GHERKIN_CONVENTIONS.md) — NFR tags, coverage rules
* [GHERKIN_TAGS.md](docs/backend/architecture/GHERKIN_TAGS.md) — Standard tag reference
* [SECURITY_AUTH_PATTERNS.md](docs/backend/architecture/SECURITY_AUTH_PATTERNS.md)
* [TECH_STACK.md](docs/backend/architecture/TECH_STACK.md)
* [TESTING.md](docs/backend/architecture/TESTING.md)
* [AGENT_ARCHITECTURE.md](docs/backend/architecture/AGENT_ARCHITECTURE.md) — AI agent design patterns (LangGraph, tools, evaluation)
* [ERROR_MAPPING.md](docs/backend/architecture/ERROR_MAPPING.md) — Domain exception to HTTP status mapping
* [OBSERVABILITY_PORT_CONTRACT.md](docs/backend/architecture/OBSERVABILITY_PORT_CONTRACT.md) — Observability port interface
* [CROSS_CUTTING_CONCERNS.md](docs/backend/architecture/CROSS_CUTTING_CONCERNS.md) — DTOs, validation, pagination, timestamps
* [ADR/TEMPLATE.md](docs/backend/architecture/ADR/TEMPLATE.md)

**GenAI Contracts (Level 5)**
* [LLM_GATEWAY_CONTRACT.md](docs/backend/architecture/LLM_GATEWAY_CONTRACT.md) — LiteLLM as sole LLM gateway, provider abstraction, fallback, cost tracking
* [OBSERVABILITY_LLM_CONTRACT.md](docs/backend/architecture/OBSERVABILITY_LLM_CONTRACT.md) — OpenLLMetry (telemetry emission) + Langfuse (trace storage, prompt versioning)
* [GUARDRAILS_CONTRACT.md](docs/backend/architecture/GUARDRAILS_CONTRACT.md) — NeMo Guardrails (conversational safety) + Guardrails AI (structured output validation)
* [EVALUATION_LLM_CONTRACT.md](docs/backend/architecture/EVALUATION_LLM_CONTRACT.md) — DeepEval (quality), Promptfoo (adversarial), RAGAS (retrieval)

**Practical Guides (Level 5)**
* [litellm-setup.md](docs/backend/guides/litellm-setup.md) — LiteLLM proxy config, model aliases, fallback chains
* [openllmetry-setup.md](docs/backend/guides/openllmetry-setup.md) — Auto-instrumentation, export to Langfuse
* [langfuse-integration.md](docs/backend/guides/langfuse-integration.md) — Trace viewing, prompt management, dashboards
* [deepeval-usage.md](docs/backend/guides/deepeval-usage.md) — Writing DeepEval test cases, metrics, CI integration
* [promptfoo-usage.md](docs/backend/guides/promptfoo-usage.md) — Adversarial configs, red-team suites
* [nemo-guardrails-setup.md](docs/backend/guides/nemo-guardrails-setup.md) — Colang dialog definitions, rail configs
* [guardrails-ai-setup.md](docs/backend/guides/guardrails-ai-setup.md) — Guard definitions, validator config
* [ragas-evaluation.md](docs/backend/guides/ragas-evaluation.md) — RAG-specific metrics, dataset preparation

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

**Standards (All Levels)**
* [eval_criteria.md](docs/backend/evaluation/eval_criteria.md) — FIRST, 7 Code Virtues, LLM eval, scoring model
* [FIRST_SCORING_RUBRIC.md](docs/backend/evaluation/FIRST_SCORING_RUBRIC.md) — 1-5 scoring definitions per FIRST principle
* [VIRTUE_SCORING_RUBRIC.md](docs/backend/evaluation/VIRTUE_SCORING_RUBRIC.md) — 1-5 scoring definitions per virtue
* [EVAL_STACK.md](docs/backend/evaluation/EVAL_STACK.md) — Evaluation tooling by environment (Langfuse, DeepEval, Promptfoo, RAGAS, home-grown)

**Schemas**
* [eval_criteria.schema.json](governance/backend/schemas/eval_criteria.schema.json) — Validates feature eval_criteria.yaml (includes L5 eval_class values: deepeval_*, promptfoo_*, ragas_*)
* [evaluation_prediction.schema.json](governance/schemas/evaluation_prediction.schema.json) — Schema for plan.md prediction blocks (includes optional L5 llm_evaluation section)
* [guardrails_config.schema.json](governance/backend/schemas/guardrails_config.schema.json) — Validates guardrails configuration (L5)

**UI Evaluation**
* [eval_criteria.md](docs/ui/evaluation/eval_criteria.md) — FIRST, accessibility, E2E coverage
* [FIRST_SCORING_RUBRIC.md](docs/ui/evaluation/FIRST_SCORING_RUBRIC.md) — UI-adapted FIRST scoring
* [VIRTUE_SCORING_RUBRIC.md](docs/ui/evaluation/VIRTUE_SCORING_RUBRIC.md) — UI-adapted virtue scoring
* [eval_criteria.schema.json](governance/ui/schemas/eval_criteria.schema.json)

**Evaluation by Level**

| Level | What's Evaluated | Tools |
|-------|-----------------|-------|
| L3 | Spec completeness, Gherkin structure, NFR coverage | govkit validate |
| L4 | L3 + FIRST scores, 7 Virtue scores, eval_criteria schema | govkit validate + CI quality/eval gates |
| L5 | L4 + LLM quality (DeepEval), adversarial safety (Promptfoo), retrieval quality (RAGAS), guardrails config | govkit validate + deepeval-gate + promptfoo-gate + guardrails-check |

---

# License

Copyright 2026 Accelerated Innovation

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.

---

# Glossary

| Term | Definition |
|---|---|
| **Agent** | The AI coding tool (Claude Code or GitHub Copilot) that reads governance artifacts and generates code |
| **Rule** (Claude Code) | A path-scoped `.md` file in `.claude/rules/` that loads automatically when editing files matching its path |
| **Skill** (Claude Code) | A reusable prompt in `.claude/skills/` invoked via slash command (e.g., `/architecture-preflight`) |
| **Instruction** (Copilot) | A path-scoped `.md` file in `.github/instructions/` — Copilot equivalent of a rule |
| **Prompt** (Copilot) | A reusable Chat prompt in `.github/prompts/` — Copilot equivalent of a skill |
| **Port** | An interface defining a contract between layers (inbound ports for API entry, outbound ports for infrastructure) |
| **Adapter** | An implementation of a port that connects to infrastructure (database, external API, message queue) |
| **Domain** | Business logic that has no dependencies on frameworks or infrastructure |
| **FIRST** | Test quality framework — Fast, Isolated, Repeatable, Self-verifying, Timely (scored 1–5) |
| **7 Virtues** | Code quality framework — Working, Unique, Simple, Clear, Easy, Developed, Brief (scored 1–5) |
| **ADR** | Architecture Decision Record — documents and gates architectural changes |
| **NFR** | Non-Functional Requirement — performance, security, availability, etc. |
| **Evaluation Prediction** | Predicted FIRST and Virtue scores in `plan.md` — must average >= 4.0 before implementation |
| `govkit validate` | CLI command that checks all features for governance compliance (artifact completeness, thresholds) |
| `/architecture-preflight` | Agent skill/prompt that validates a feature against architecture contracts before planning |
| `/genai-preflight` | L5 agent skill that validates LLM gateway, observability, guardrails, and evaluation decisions |
| `/eval-suite-planning` | L5 agent skill that plans DeepEval, Promptfoo, and RAGAS test suites |
| **LiteLLM** | L5 sole LLM gateway — model routing, provider abstraction, fallback, cost tracking |
| **OpenLLMetry** | L5 LLM telemetry emission standard (OpenTelemetry for LLMs) |
| **Langfuse** | Trace storage, prompt versioning, and production evaluation visibility |
| **DeepEval** | L5 LLM quality evaluation — faithfulness, relevancy, hallucination metrics |
| **Promptfoo** | L5 adversarial and regression testing — jailbreak, injection, safety |
| **RAGAS** | L5 retrieval-specific evaluation — context recall, precision (RAG pipelines only) |
| **NeMo Guardrails** | L5 conversational safety — dialog flow control, topic boundaries, jailbreak prevention |
| **Guardrails AI** | L5 structured output validation — JSON schema enforcement on LLM responses |

---

# Getting Help

- **Issues:** [github.com/Accelerated-Innovation/governed-ai-delivery/issues](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues)
- **Contributing:** See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Changelog:** See [CHANGELOG.md](CHANGELOG.md)
- **CI Reference:** See [ci/README.md](ci/README.md) for what's enforced vs predicted

---

# Resources

[Copilot Prompts Explained — Watch on YouTube](https://youtu.be/0XoXNG65rfg?si=sWwyYr84zgNr5mRz)
