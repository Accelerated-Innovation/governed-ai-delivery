# Governed AI Delivery

A spec-driven, evaluation-governed scaffolding kit for AI-assisted software delivery. Supports multiple AI coding agents with clean separation of concerns.

Every feature is:

* Defined with **Gherkin acceptance criteria**
* Constrained with **NFRs**
* Governed by **LLM evaluation criteria**
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

Add the following files for each feature you want to implement:

```
features/my_feature/
  ├─ acceptance.feature
  ├─ nfrs.md
  ├─ eval_criteria.yaml
  ├─ plan.md
  └─ architecture_preflight.md
```

`eval_criteria.yaml` may start minimal — it will be updated during planning.

## 4. Open in VS Code

No dependencies are required yet. If/when dependencies are added, this section will be updated.

---

# Feature Workflow

The workflow is the same regardless of which agent you use. Commands differ by agent — see the table in each phase.

Assume this feature structure:

```
features/cool_feature/
  ├─ acceptance.feature
  ├─ nfrs.md
  ├─ eval_criteria.yaml
  ├─ plan.md
  └─ architecture_preflight.md
```

---

## Phase 1 — Architecture Preflight

| Agent | Command |
|---|---|
| Copilot | `/architecture-preflight` |
| Claude Code | `/project:architecture-preflight` |

Provide the feature name and paths to NFRs, Gherkin, and eval YAML. The agent generates `architecture_preflight.md`.

If an ADR is required:

| Agent | Command |
|---|---|
| Copilot | `/adr-author` |
| Claude Code | `/project:adr-author` |

Commit the ADR before proceeding.

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
* Evaluation Compliance Summary
* Predicted FIRST score
* Predicted 7 Virtue score
* Refactor triggers

Implementation must not begin if predicted thresholds are not met.

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
* FIRST enforcement
* 7 Code Virtue enforcement
* SonarQube
* Boundary rules (`import-linter`)
* Security scans
* LLM eval checks (if enabled)

Before merge confirm:

* Plan was followed
* Specs are satisfied
* ADR present (if required)
* Evaluation thresholds met

Merge only after all gates pass.

---

# Repository Structure

```
governed-ai-delivery/
├── agents/
│   ├── copilot/            # Copilot-specific config (installs to .github/)
│   └── claude-code/        # Claude Code-specific config (installs to root + .claude/)
├── cli/                    # govkit CLI source
├── docs/                   # Architecture and evaluation docs (agent-agnostic)
├── features/               # Feature spec examples (agent-agnostic)
├── governance/             # Templates and schemas (agent-agnostic)
└── ci/                     # CI gate examples (agent-agnostic)
```

---

# Architecture

* [ARCH_CONTRACT.md](docs/architecture/ARCH_CONTRACT.md)
* [BOUNDARIES.md](docs/architecture/BOUNDARIES.md)
* [API_CONVENTIONS.md](docs/architecture/API_CONVENTIONS.md)
* [SECURITY_AUTH_PATTERNS.md](docs/architecture/SECURITY_AUTH_PATTERNS.md)
* [docs/evaluation/eval_criteria.md](docs/evaluation/eval_criteria.md)

---

# Security

* JWT auth and RBAC enforced at API layer
* Domain never accesses raw tokens
* See [SECURITY_AUTH_PATTERNS.md](docs/architecture/SECURITY_AUTH_PATTERNS.md)

---

# Testing

Testing is evaluation-driven. All features must:

* Satisfy FIRST principles
* Achieve minimum virtue averages
* Pass LLM evaluation thresholds (if applicable)

Refer to [docs/evaluation/eval_criteria.md](docs/evaluation/eval_criteria.md).

---

# Contributing

Before contributing:

* Read `docs/architecture/**`
* Read `docs/evaluation/eval_criteria.md`
* Do not bypass ports or adapters
* Submit ADR for boundary, security, or dependency changes

---

# License

Copyright 2026 Accelerated Innovation

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.

---

# Resources

[Copilot Prompts Explained — Watch on YouTube](https://youtu.be/0XoXNG65rfg?si=sWwyYr84zgNr5mRz)
