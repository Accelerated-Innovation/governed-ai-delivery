# Governed AI Delivery

A spec-driven, evaluation-governed scaffolding kit for AI-assisted software delivery. Supports multiple AI coding agents with clean separation of concerns.

Every feature is:

* Defined with **Gherkin acceptance criteria** tagged to NFR categories
* Constrained with **fully populated NFRs** (no TBD entries permitted)
* Governed by **evaluation criteria** validated against a JSON Schema
* Planned through **Architecture Preflight + Implementation Plan prompts**
* Enforced by **CI gates, quality rules, and evaluation thresholds**

The AI agent operates inside a governed system. Architecture, evaluation, and feature artifacts are the source of truth — not the agent.

---

# Supported Agents

| Agent | Status |
|---|---|
| GitHub Copilot | Supported |
| Claude Code | Supported |

---

# Quickstart

## 1. Install govkit

```bash
pip install git+https://github.com/Accelerated-Innovation/governed-ai-delivery.git
```

## 2. Apply to your project

From your project root, run:

```bash
govkit apply --agent copilot --target .
```
or
```bash
govkit apply --agent claude-code --target .
```

This installs the agent-specific config files and shared governance artifacts into your project.

## 3. Create a Feature Folder

Copy the starter scaffolding from `features/feature_name/`:

```
features/my_feature/
  ├─ acceptance.feature       ← Gherkin scenarios with @nfr-* and @contract tags
  ├─ nfrs.md                  ← Must be fully populated — no TBD entries
  ├─ eval_criteria.yaml       ← Validated against governance/backend/schemas/eval_criteria.schema.json
  ├─ plan.md                  ← Includes structured evaluation prediction block
  └─ architecture_preflight.md
```

Each file in `features/feature_name/` contains inline instructions and points to the worked example at `features/schema_contract_example/`.

> **Important:** `nfrs.md` must have no TBD entries before Architecture Preflight begins. The agent will stop and ask if any category is incomplete.

## 4. Open in VS Code

No dependencies are required yet. If/when dependencies are added, this section will be updated.

---

# Feature Workflow

The workflow is the same regardless of which agent you use. Commands differ by agent — see the table in each phase.

---

## Phase 1 — Architecture Preflight

| Agent | Command |
|---|---|
| Copilot | `/architecture-preflight` |
| Claude Code | `/project:architecture-preflight` |

Provide the feature name and paths to NFRs, Gherkin, and eval YAML. The agent generates `architecture_preflight.md` covering:

* Boundary and API impact
* Security impact
* Evaluation impact
* **Shared contract analysis** — if the feature produces a schema, event definition, or API contract consumed by other services, an ADR is required before proceeding
* ADR determination

If an ADR is required:

| Agent | Command |
|---|---|
| Copilot | `/adr-author` |
| Claude Code | `/project:adr-author` |

ADR must be Accepted before implementation proceeds. ADR templates and examples live under `docs/backend/architecture/ADR/`.

---

## Phase 2 — Spec Planning

| Agent | Command |
|---|---|
| Copilot | `/spec-planning` |
| Claude Code | `/project:spec-planning` |

Generates or updates:

* `plan.md`
* `eval_criteria.yaml`

The plan must include:

* Increment breakdown
* Shared contract artifacts (if applicable)
* **Evaluation Compliance Summary** — a structured YAML block with predicted FIRST and 7 Virtue scores, each with a numeric value and one-sentence evidence rationale

Implementation must not begin if predicted averages are below 4.0 or `thresholds_met` is false.

---

## Phase 3 — Implementation Planning

| Agent | Command |
|---|---|
| Copilot | `/implementation-plan` |
| Claude Code | `/project:implementation-plan` |

Produces:

* Ordered task checklist
* FIRST-aligned test plan
* LLM evaluation integration steps
* Refactor conditions

Review and approve before proceeding.

---

## Phase 4 — Agent Implementation

Implement one increment at a time. For each increment:

* Add unit tests (FIRST compliant)
* Add contract/integration tests (if applicable)
* Ensure structural simplicity
* Respect Hexagonal boundaries

---

## Phase 5 — CI & Merge

Push branch and open PR. CI gates run:

* Unit tests
* Integration tests
* `eval_criteria.yaml` schema validation (all feature instances validated against `governance/backend/schemas/eval_criteria.schema.json`)
* FIRST and 7 Code Virtue prediction completeness check
* LLM eval suite and regression check (if `mode: llm`)
* SonarQube quality gate
* Architecture boundary enforcement (`import-linter`)
* Security scan (Snyk)
* Contract backward-compatibility check (triggered by `@contract`-tagged scenarios)

See `ci/quality-gate-example.yml` and `ci/eval-gate-example.yml` for setup instructions — each file opens with a comment block explaining what to configure.

Before merge confirm:

* Plan was followed
* Specs are satisfied
* ADR present and Accepted (if required)
* Evaluation thresholds met

Merge only after all gates pass.

---

# Worked Example

`features/schema_contract_example/` is a fully completed feature demonstrating every governance rule:

* Tagged Gherkin covering all NFR categories and shared contract scenarios
* Fully populated `nfrs.md`
* Schema-valid `eval_criteria.yaml`
* `plan.md` with completed evaluation prediction block and shared contract artifacts
* Completed `architecture_preflight.md` including Shared Contract Analysis
* `docs/backend/architecture/ADR/ADR-001-schema-contract-ownership.md` — a complete accepted ADR

Use this as your reference when completing the starter scaffolding.

---

# Repository Structure

```
governed-ai-delivery/
├── agents/
│   ├── copilot/                    # Copilot-specific config (installs to .github/)
│   │   ├── copilot-instructions.md
│   │   ├── instructions/           # Phase-specific instruction files
│   │   └── prompts/                # Slash command prompt files
│   └── claude-code/                # Claude Code config (installs to root + .claude/)
│       ├── CLAUDE.md
│       ├── rules/                  # Layer-specific rules (auto-loaded by file path)
│       └── skills/                 # Slash command skill definitions
├── cli/                            # govkit CLI source
├── docs/
│   ├── architecture/
│   │   ├── ADR/                    # Architecture Decision Records
│   │   │   ├── TEMPLATE.md         # ADR template
│   │   │   └── ADR-001-*.md        # Accepted ADRs
│   │   ├── ARCH_CONTRACT.md
│   │   ├── BOUNDARIES.md
│   │   ├── API_CONVENTIONS.md
│   │   ├── DESIGN_PRINCIPLES.md    # SOLID, DRY, YAGNI, KISS — mapped to 7 Virtues
│   │   ├── GHERKIN_CONVENTIONS.md  # NFR tags, @contract tag, coverage rules
│   │   ├── SECURITY_AUTH_PATTERNS.md
│   │   ├── TECH_STACK.md
│   │   └── TESTING.md
│   └── evaluation/
│       └── eval_criteria.md        # FIRST, 7 Virtues, scoring model, eval workflow
├── features/
│   ├── feature_name/               # Starter scaffolding — copy to begin a new feature
│   └── schema_contract_example/    # Fully worked example — reference implementation
├── governance/
│   ├── schemas/
│   │   └── eval_criteria.schema.json   # JSON Schema for eval_criteria.yaml instances
│   └── templates/
│       ├── architecture_preflight.md
│       └── plan.md
└── ci/
    ├── quality-gate-example.yml    # Schema validation, boundaries, SonarQube, Snyk, contracts
    └── eval-gate-example.yml       # Eval prediction check, LLM eval run, regression gate
```

---

# Architecture

* [ARCH_CONTRACT.md](docs/backend/architecture/ARCH_CONTRACT.md)
* [BOUNDARIES.md](docs/backend/architecture/BOUNDARIES.md)
* [API_CONVENTIONS.md](docs/backend/architecture/API_CONVENTIONS.md)
* [DESIGN_PRINCIPLES.md](docs/backend/architecture/DESIGN_PRINCIPLES.md) — SOLID, DRY, YAGNI, KISS
* [GHERKIN_CONVENTIONS.md](docs/backend/architecture/GHERKIN_CONVENTIONS.md) — NFR tags, coverage rules
* [SECURITY_AUTH_PATTERNS.md](docs/backend/architecture/SECURITY_AUTH_PATTERNS.md)
* [TESTING.md](docs/backend/architecture/TESTING.md)
* [ADR/TEMPLATE.md](docs/backend/architecture/ADR/TEMPLATE.md)

---

# Evaluation

* [eval_criteria.md](docs/backend/evaluation/eval_criteria.md) — FIRST principles, 7 Code Virtues, scoring model
* [eval_criteria.schema.json](governance/backend/schemas/eval_criteria.schema.json) — JSON Schema for feature eval YAML instances

---

# Security

* JWT auth and RBAC enforced at API layer
* Domain never accesses raw tokens
* See [SECURITY_AUTH_PATTERNS.md](docs/backend/architecture/SECURITY_AUTH_PATTERNS.md)

---

# Testing

Testing is evaluation-driven. All features must:

* Satisfy FIRST principles (minimum average 4.0)
* Achieve minimum Virtue averages (minimum average 4.0)
* Pass LLM evaluation thresholds (if `mode: llm`)
* Have Gherkin scenarios tagged per [GHERKIN_CONVENTIONS.md](docs/backend/architecture/GHERKIN_CONVENTIONS.md)

See [docs/backend/evaluation/eval_criteria.md](docs/backend/evaluation/eval_criteria.md) and [docs/backend/architecture/TESTING.md](docs/backend/architecture/TESTING.md).

---

# Contributing

Before contributing:

* Read `docs/backend/architecture/`
* Read `docs/backend/evaluation/eval_criteria.md`
* Do not bypass ports or adapters
* Submit an ADR for boundary, security, dependency, or shared contract changes

---

# License

Copyright 2026 Accelerated Innovation

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.

---

# Resources

[Copilot Prompts Explained — Watch on YouTube](https://youtu.be/0XoXNG65rfg?si=sWwyYr84zgNr5mRz)
