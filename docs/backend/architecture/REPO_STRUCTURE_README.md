# Repository Structure

This document explains how the repository is organized and where specific responsibilities belong.

The goal of this structure is to support:

- Spec-driven development
- Hexagonal architecture
- Evaluation-driven AI delivery
- Governance across AI coding assistants (Copilot, Claude, etc.)

This repository is designed as a **governed delivery template**.

---

# Application Structure for Projects Using This Kit

This repository is a **spec kit** that defines governance, architecture rules, and development workflow.  
It is not intended to contain the runtime application code itself.

Projects created using this kit should place their application code in a package under `src/`.

Recommended structure for adopting projects:
```
src/<project_pacakage_name>/
├── api/
├── ports/
├── services/
├── adapters/
├── common/
```
Example:
```
src/customer_support_ai/
api/
ports/
services/
adapters/
common/
```

Where:

| Folder | Purpose |
|------|------|
| `api/` | HTTP or inbound adapters (FastAPI, webhooks, etc.) |
| `ports/` | inbound and outbound interfaces for hexagonal architecture |
| `services/` | domain logic and orchestration |
| `adapters/` | infrastructure implementations (DB, APIs, LLM providers, etc.) |
| `common/` | shared utilities and data models |

This keeps application code isolated from governance artifacts such as:
- `docs/`
- `governance/`
- `features/`
- `agents/`


Benefits of the `src/<project_package_name>` layout:

- prevents accidental imports from the project root
- supports Python packaging best practices
- allows multiple services to reuse the governance kit
- keeps governance artifacts separate from runtime code

---

# Top-Level Structure
```
docs/
governance/
features/
agents/
cli/
src/api/
src/ports/
src/services/
src/adapters/
src/common/
```

Each folder has a specific responsibility.

---

# docs/

The `docs/` folder contains **architectural and evaluation standards** that apply across the repository.
```
docs/
architecture/
evaluation/
```

These documents are the **source of truth** for architecture and system behavior.

---

# docs/backend/architecture/

Architecture policy and design contracts.
```
docs/backend/architecture/
ARCH_CONTRACT.md
BOUNDARIES.md
API_CONVENTIONS.md
SECURITY_AUTH_PATTERNS.md
TESTING.md
TECH_STACK.md
AGENT_ARCHITECTURE.md
ADR/
```

Purpose of each file:

| File | Purpose |
|-----|--------|
| ARCH_CONTRACT.md | Core architectural rules |
| BOUNDARIES.md | Dependency and layer enforcement |
| API_CONVENTIONS.md | API design rules |
| SECURITY_AUTH_PATTERNS.md | Auth and security model |
| TESTING.md | Testing strategy (FIRST + BDD) |
| TECH_STACK.md | Approved technologies |
| AGENT_ARCHITECTURE.md | AI agent architecture rules |
| ADR/ | Architecture Decision Records |

These documents rarely change and define **how systems must be built**.

---

# docs/evaluation/

Defines how AI-generated behavior is evaluated.
```
docs/evaluation/
eval_criteria.md
```

This document defines:

- FIRST testing principles
- 7 Code Virtues
- evaluation workflow
- scoring thresholds
- refactor triggers

Feature-specific evaluation settings live in:
```
features/<feature>/eval_criteria.yaml
``` 

---

# governance/

Governance templates and schemas used during development.
```
governance/
templates/
schemas/
``` 

These templates guide:

- architecture validation
- implementation planning
- evaluation compliance

## schemas/

Machine-readable validation rules.

Example:
```
schemas/
eval_criteria.schema.json
```

Schemas validate feature configuration files.

---

# features/

Each feature is defined with specifications and planning artifacts.
```
features/<feature_name>/
acceptance.feature
nfrs.md
eval_criteria.yaml
architecture_preflight.md
plan.md
```

Purpose of each artifact:

| File | Purpose |
|-----|--------|
| acceptance.feature | Gherkin feature scenarios |
| nfrs.md | Non-functional requirements |
| eval_criteria.yaml | Feature-level evaluation configuration |
| architecture_preflight.md | Architecture validation |
| plan.md | Implementation plan |

Features are **spec-first**.

Implementation must not begin without these artifacts.

---

# api/

HTTP layer.
```
api/
```

Responsibilities:

- FastAPI route handlers
- authentication enforcement
- request/response mapping
- calling inbound ports

Rules:

- API layer must not contain business logic
- All logic must delegate to **ports**

---

# ports/

Interfaces between layers.
```
ports/
inbound/
outbound/
```

Inbound ports define **how the system is invoked**.

Outbound ports define **external capabilities required by the domain**.

Ports are pure Python interfaces.

---

# services/

Domain logic.
```
services/
```

Responsibilities:

- business rules
- orchestration
- state transitions

Services must:

- remain framework-agnostic
- depend only on ports
- remain stateless and testable

---

# adapters/

Infrastructure implementations.
```
adapters/
```

Examples:

- database adapters
- external APIs
- vector stores
- file storage
- LLM provider adapters

Adapters implement outbound ports.

---

# common/

Shared utilities.
```
common/
```

Examples:

- logging helpers
- data models
- tracing utilities

`common` must remain dependency-light.

---

# agents/

AI coding agent configurations. Each subdirectory contains the config files for one agent, installed into target projects via `govkit`.

```
agents/
  copilot/        ← installs to .github/ in the target project
  claude-code/    ← installs CLAUDE.md and .claude/ in the target project
```

Each agent folder contains:
- Agent-specific instructions (global and layer-scoped)
- Planning commands/prompts
- A `manifest.json` describing where each file installs

To install an agent into a project:

```bash
govkit apply --agent copilot --target /path/to/project
govkit apply --agent claude-code --target /path/to/project
```

---

# cli/

Source for the `govkit` CLI installer.

```
cli/
  govkit.py
```

Install govkit:

```bash
pip install git+https://github.com/Accelerated-Innovation/governed-ai-delivery.git
```

---

# Customization for New Projects

After running `govkit apply`, review and update:
```
docs/backend/architecture/TECH_STACK.md
docs/backend/architecture/AGENT_ARCHITECTURE.md
docs/backend/architecture/API_CONVENTIONS.md
```

You may also update:
```
docs/backend/architecture/SECURITY_AUTH_PATTERNS.md
docs/backend/architecture/TESTING.md
```

Feature specifications must always be created under `features/`.

---

# Summary

This repository separates responsibilities across:

- architecture policy
- evaluation policy
- governance templates
- feature specifications
- implementation layers
- AI coding assistant configuration

This structure enables:

- controlled AI code generation
- consistent architecture enforcement
- evaluation-driven development
- reusable project templates.
