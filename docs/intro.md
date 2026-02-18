# 🧭 Governed AI Delivery: Introduction

This project template is designed for teams building AI-powered features with GitHub Copilot in a tightly governed, spec-first workflow.

It brings together:

* 🧠 **Copilot Chat** for AI-assisted planning and implementation
* 📑 **Spec-driven development** using Gherkin, NFRs, and LLM evals
* 🧱 **Hexagonal architecture** enforced with ports and adapters
* 🛡 **Security, layering, and dependency rules** enforced in CI
* 📜 **Architecture docs** and ADR-driven change control

---

## Why Use This Template?

This repo helps teams:

* Enforce architecture standards with automation
* Use GitHub Copilot responsibly and consistently
* Align business specs, LLM evaluation, and implementation
* Move fast while preserving system integrity
* Avoid AI-generated architecture drift or shortcut code

---

## Key Components

| Folder/File              | Purpose                                            |
| ------------------------ | -------------------------------------------------- |
| `.github/instructions/`  | Prompts and agent instructions for Copilot Chat    |
| `docs/architecture/`     | Contracts, boundaries, and ADRs                    |
| `features/**/`           | Per-feature specs and eval criteria                |
| `ports/` and `adapters/` | Hexagonal boundaries for domain and infrastructure |
| `services/`              | Stateless business logic (pure and injectable)     |
| `repos/`                 | Integration logic: DB, APIs, queues, files         |

---

## Example Feature Flow

1. Create your feature spec: `feature_name.feature`, `nfrs.md`, `eval_criteria.yaml`
2. Use `/architecture-preflight` to validate design alignment
3. Use `/adr-author` if changes to architecture are flagged
4. Use `/implementation-plan` to scaffold implementation plan
5. Generate code using Copilot Agent
6. Push, open PR, run CI gates

---

## Enforced by Default

* Import boundaries (`import-linter`)
* Layering rules and statelessness
* SOLID principles
* Security and auth patterns
* Pydantic-based validation
* Logging, observability, error handling

---

## Extend It

You can customize this template to fit your stack:

* Swap FastAPI for another HTTP layer
* Use other LLMs for eval or assistant
* Add data science flows or pipelines
* Connect GitHub Copilot to Azure DevOps via prompts

---

## Questions?

Check the `README.md` for quickstart, or reach out to your platform architect.
