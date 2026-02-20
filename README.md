# 🚧 Project Overview

This template enables spec-driven, evaluation-governed feature delivery using GitHub Copilot.

Every feature is:

* Defined with **Gherkin acceptance criteria**
* Constrained with **NFRs**
* Governed by **LLM evaluation criteria**
* Planned through **Architecture Preflight + Implementation Plan prompts**
* Enforced by **CI gates, quality rules, and evaluation thresholds**

Copilot operates inside a governed system. Architecture, evaluation, and feature artifacts are the source of truth.

---

# ⚡️ Quickstart

## 1️⃣ Create a Repository

```bash
gh repo create my-new-project --template <this-repo>
```

## 2️⃣ Create a Feature Folder

```
features/my_feature/
  ├─ my_feature.feature
  ├─ nfrs.md
  └─ eval_criteria.yaml
```

`eval_criteria.yaml` may start minimal. It will be updated during planning.

## 3️⃣ Open in VS Code

Install dependencies:

```bash
pip install -r requirements.txt
pre-commit install
```

Enable GitHub Copilot Chat (Plan + Agent modes).

---

# 🌝 Feature Workflow (Mandatory Order)

Assume this structure:

```
features/cool_feature/
  ├─ cool_feature.feature
  ├─ nfrs.md
  └─ eval_criteria.yaml
```

---

## Phase 1 — Architecture Preflight

1. Switch Copilot Chat to **Plan** mode.
2. Run:

```
/architecture-preflight
```

3. Provide:

   * Feature name
   * Paths to NFRs, Gherkin, and eval YAML

4. Copilot generates:

   * `architecture_preflight.md`

If ADR is required:

```
/adr-author
```

Commit ADR before proceeding.

---

## Phase 2 — Spec Planning

Run:

```
/spec-planning
```

This generates or updates:

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

Switch to Plan mode and run:

```
/implementation-plan
```

This produces:

* Ordered task checklist
* FIRST-aligned test plan
* LLM evaluation integration steps
* Refactor conditions

Review and approve.

---

## Phase 4 — Agent Implementation

Switch to **Agent** mode.

Implement one increment at a time.

For each increment:

* Add unit tests (FIRST compliant)
* Add contract/integration tests (if applicable)
* Ensure structural simplicity
* Respect Hexagonal boundaries

---

## Phase 5 — CI & Merge

Push branch and open PR.

CI gates run:

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

# 🏗 Architecture

* [`ARCH_CONTRACT.md`](docs/architecture/ARCH_CONTRACT.md)
* [`BOUNDARIES.md`](docs/architecture/BOUNDARIES.md)
* [`API_CONVENTIONS.md`](docs/architecture/API_CONVENTIONS.md)
* [`SECURITY_AUTH_PATTERNS.md`](docs/architecture/SECURITY_AUTH_PATTERNS.md)
* [`docs/evaluation/eval_criteria.md`](docs/evaluation/eval_criteria.md)

---

# 🧱 Structure

* `api/` — FastAPI inbound adapters
* `ports/` — inbound/outbound interfaces
* `services/` — domain logic (stateless)
* `adapters/` — infrastructure implementations
* `repos/` — persistence adapters (if used)
* `common/` — shared utilities
* `features/` — feature specs and plans

---

# 🔐 Security

* JWT auth and RBAC enforced at API layer
* Domain never accesses raw tokens
* See `SECURITY_AUTH_PATTERNS.md`

---

# ⚙️ Configuration

* All secrets must use environment variables via `BaseSettings`

---

# ✅ Testing

Testing is evaluation-driven.

All features must:

* Satisfy FIRST principles
* Achieve minimum virtue averages
* Pass LLM evaluation thresholds (if applicable)

Refer to:

* `docs/evaluation/eval_criteria.md`

---

# 🤝 Contributing

Before contributing:

* Read `docs/architecture/**`
* Read `docs/evaluation/eval_criteria.md`
* Do not bypass ports or adapters
* Submit ADR for boundary, security, or dependency changes

---

# 📄 License

> Add license details here.

---

# Copilot Prompts Explained

[Watch on YouTube](https://youtu.be/0XoXNG65rfg?si=sWwyYr84zgNr5mRz)
