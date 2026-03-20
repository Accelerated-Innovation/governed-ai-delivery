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

| Agent | Type | Status |
|---|---|---|
| `copilot` | Backend (Python / Hexagonal) | Supported |
| `claude-code` | Backend (Python / Hexagonal) | Supported |
| `copilot-ui-react` | React UI (MVVM) | Supported |
| `claude-code-ui-react` | React UI (MVVM) | Supported |

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

From your project root, choose the agent that matches your project type:

**Backend (Python / Hexagonal Architecture):**
```bash
govkit apply --agent copilot --target .
govkit apply --agent claude-code --target .
```

**React UI (MVVM / React Query + Zustand):**
```bash
govkit apply --agent copilot-ui-react --target .
govkit apply --agent claude-code-ui-react --target .
```

This installs the agent-specific config files and shared governance artifacts into your project.

## 4. Create a Feature Folder

Copy the starter scaffolding from `features/feature_name/`:

```
features/my_feature/
  ├─ acceptance.feature       ← Gherkin scenarios with @nfr-* and @contract tags
  ├─ nfrs.md                  ← Must be fully populated — no TBD entries
  ├─ eval_criteria.yaml       ← Validated against the agent's eval schema
  ├─ plan.md                  ← Includes structured evaluation prediction block
  └─ architecture_preflight.md
```

> **Important:** `nfrs.md` must have no TBD entries before Architecture Preflight begins.

---

# Feature Workflow — Backend

The workflow is the same regardless of which backend agent you use. Commands differ by agent.

## Phase 1 — Architecture Preflight

| Agent | Command |
|---|---|
| Copilot | `/architecture-preflight` |
| Claude Code | `/project:architecture-preflight` |

Generates `architecture_preflight.md` covering boundary and API impact, security impact, evaluation impact, shared contract analysis, and ADR determination.

If an ADR is required:

| Agent | Command |
|---|---|
| Copilot | `/adr-author` |
| Claude Code | `/project:adr-author` |

ADR must be Accepted before implementation proceeds. ADR templates live under `docs/backend/architecture/ADR/`.

---

## Phase 2 — Spec Planning

| Agent | Command |
|---|---|
| Copilot | `/spec-planning` |
| Claude Code | `/project:spec-planning` |

Generates or updates `plan.md` and `eval_criteria.yaml`. The plan must include an **Evaluation Compliance Summary** with predicted FIRST and 7 Virtue scores. Implementation must not begin if predicted averages are below 4.0 or `thresholds_met` is false.

---

## Phase 3 — Implementation Planning

| Agent | Command |
|---|---|
| Copilot | `/implementation-plan` |
| Claude Code | `/project:implementation-plan` |

Produces an ordered task checklist, FIRST-aligned test plan, LLM evaluation integration steps, and refactor conditions. Review and approve before proceeding.

---

## Phase 4 — Agent Implementation

Implement one increment at a time:

* Add unit tests (FIRST compliant)
* Add contract/integration tests (if applicable)
* Ensure structural simplicity
* Respect Hexagonal boundaries

---

## Phase 5 — CI & Merge

Push branch and open PR. CI gates run:

* Unit and integration tests
* `eval_criteria.yaml` schema validation
* FIRST and 7 Code Virtue prediction completeness check
* LLM eval suite and regression check (if `mode: llm`)
* SonarQube quality gate
* Architecture boundary enforcement (`import-linter`)
* Security scan (Snyk)
* Contract backward-compatibility check (`@contract`-tagged scenarios)

See `ci/quality-gate-example.yml` and `ci/eval-gate-example.yml`.

---

# Feature Workflow — React UI

The workflow follows the same 5-phase structure. MVVM layer order is enforced: API → ViewModel → View.

## Phase 1 — Architecture Preflight

| Agent | Command |
|---|---|
| Copilot | `/architecture-preflight` |
| Claude Code | `/project:architecture-preflight` |

Covers MVVM layer impact, backend contract availability, shared component impact, state management decision, accessibility impact, and ADR determination.

ADR templates live under `docs/ui/architecture/ADR/`.

---

## Phase 2 — Spec Planning

| Agent | Command |
|---|---|
| Copilot | `/spec-planning` |
| Claude Code | `/project:spec-planning` |

Generates `plan.md` with MVVM breakdown, increment sequence, backend contract dependencies, accessibility plan, and Evaluation Compliance Summary (FIRST scores + predicted axe violations).

---

## Phase 3 — Implementation Planning

| Agent | Command |
|---|---|
| Copilot | `/implementation-plan` |
| Claude Code | `/project:implementation-plan` |

Produces an ordered checklist following MVVM layer sequence: types → API → hooks → store → components → E2E.

---

## Phase 4 — Agent Implementation

Implement one increment at a time following layer order:

* API functions first, with unit tests
* ViewModel hooks and stores, with hook tests (MSW)
* View components last, with React Testing Library tests and axe checks

---

## Phase 5 — CI & Merge

CI gates run:

* TypeScript strict mode (`tsc --noEmit`)
* ESLint including `jsx-a11y`
* Component tests (Vitest + React Testing Library)
* Accessibility — zero critical axe-core violations
* E2E — Playwright with axe scan per flow
* `eval_criteria.yaml` schema validation

---

# Repository Structure

```
governed-ai-delivery/
├── agents/
│   ├── copilot/                      # Backend — Copilot (installs to .github/)
│   ├── claude-code/                  # Backend — Claude Code (installs to root + .claude/)
│   ├── copilot-ui-react/             # React UI — Copilot (installs to .github/)
│   └── claude-code-ui-react/         # React UI — Claude Code (installs to root + .claude/)
├── cli/
│   └── govkit.py                     # govkit CLI installer
├── docs/
│   ├── backend/
│   │   ├── architecture/             # ARCH_CONTRACT, BOUNDARIES, API_CONVENTIONS, ADR/, etc.
│   │   └── evaluation/               # eval_criteria.md — FIRST, 7 Virtues, scoring model
│   └── ui/
│       ├── architecture/             # MVVM_CONTRACT, COMPONENT_CONVENTIONS, STATE_MANAGEMENT, etc.
│       └── evaluation/               # eval_criteria.md — FIRST, accessibility, E2E standards
├── features/
│   ├── feature_name/                 # Starter scaffolding — copy to begin a new feature
│   └── schema_contract_example/      # Fully worked backend example
├── governance/
│   ├── backend/
│   │   ├── schemas/                  # eval_criteria.schema.json
│   │   └── templates/                # architecture_preflight.md, plan.md
│   └── ui/
│       ├── schemas/                  # eval_criteria.schema.json (UI)
│       └── templates/                # architecture_preflight.md, plan.md (UI)
└── ci/
    ├── quality-gate-example.yml      # Schema validation, boundaries, SonarQube, Snyk
    └── eval-gate-example.yml         # Eval prediction check, LLM eval, regression gate
```

---

# Architecture — Backend

* [ARCH_CONTRACT.md](docs/backend/architecture/ARCH_CONTRACT.md)
* [BOUNDARIES.md](docs/backend/architecture/BOUNDARIES.md)
* [API_CONVENTIONS.md](docs/backend/architecture/API_CONVENTIONS.md)
* [DESIGN_PRINCIPLES.md](docs/backend/architecture/DESIGN_PRINCIPLES.md) — SOLID, DRY, YAGNI, KISS
* [GHERKIN_CONVENTIONS.md](docs/backend/architecture/GHERKIN_CONVENTIONS.md) — NFR tags, coverage rules
* [SECURITY_AUTH_PATTERNS.md](docs/backend/architecture/SECURITY_AUTH_PATTERNS.md)
* [TECH_STACK.md](docs/backend/architecture/TECH_STACK.md)
* [TESTING.md](docs/backend/architecture/TESTING.md)
* [ADR/TEMPLATE.md](docs/backend/architecture/ADR/TEMPLATE.md)

# Architecture — React UI

* [MVVM_CONTRACT.md](docs/ui/architecture/MVVM_CONTRACT.md)
* [COMPONENT_CONVENTIONS.md](docs/ui/architecture/COMPONENT_CONVENTIONS.md)
* [STATE_MANAGEMENT.md](docs/ui/architecture/STATE_MANAGEMENT.md)
* [TECH_STACK.md](docs/ui/architecture/TECH_STACK.md)

---

# Evaluation

**Backend**
* [eval_criteria.md](docs/backend/evaluation/eval_criteria.md) — FIRST, 7 Code Virtues, LLM eval, scoring model
* [eval_criteria.schema.json](governance/backend/schemas/eval_criteria.schema.json)
* [EVAL_STACK.md](docs/backend/evaluation/EVAL_STACK.md) — LangSmith, Arize, home-grown framework

**React UI**
* [eval_criteria.md](docs/ui/evaluation/eval_criteria.md) — FIRST, accessibility, E2E coverage
* [eval_criteria.schema.json](governance/ui/schemas/eval_criteria.schema.json)

---

# License

Copyright 2026 Accelerated Innovation

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.

---

# Resources

[Copilot Prompts Explained — Watch on YouTube](https://youtu.be/0XoXNG65rfg?si=sWwyYr84zgNr5mRz)
