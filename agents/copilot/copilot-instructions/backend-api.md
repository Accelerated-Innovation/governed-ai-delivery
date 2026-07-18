---
applyTo: "**"
---
# GitHub Copilot Instructions — Foundations (Level 3)

These instructions govern how GitHub Copilot plans, reasons, and generates
code in this repository. They are mandatory.

Copilot must treat this repository as a governed delivery system, not an open
coding environment. Repository artifacts are the source of truth. Chat memory
is not.

> **Feature artifacts are not part of L3.** If your team adopts spec-driven
> feature delivery (per-feature `acceptance.feature`, `nfrs.md`, `plan.md`,
> `eval_criteria.yaml`, and `architecture_preflight.md`), upgrade with
> `govkit apply --level 4`.

---

## 1. Operating Mode

Copilot operates aligned to:

* Architecture contracts under `docs/backend/architecture/`
* Path-scoped instructions under `.github/instructions/govkit/`

Before generating or modifying code:

* Read the architecture contracts relevant to the layer you are touching
  (see Architecture Contracts below)
* Apply architecture, testing, technology, and security contracts as binding
  constraints
* Confirm boundary rules in `docs/backend/architecture/BOUNDARIES.md`

If required inputs are missing or unclear, stop and ask.

---

## 2. Architecture Contracts

Your project's language- and framework-specific conventions are documented in
`docs/backend/architecture/`. Before implementing in each layer, read the
corresponding document:

| Layer                     | Document                             | Content                                                               |
| ------------------------- | ------------------------------------ | --------------------------------------------------------------------- |
| API / inbound adapter     | `API_CONVENTIONS.md`                 | Routing style, request/response models, authentication, error mapping |
| Services / domain         | `ARCH_CONTRACT.md`                   | Architecture model, layering, approved libraries                      |
| Ports                     | `ARCH_CONTRACT.md`                   | Port interface guidelines                                             |
| Adapters / infrastructure | `ARCH_CONTRACT.md` + `BOUNDARIES.md` | Integration patterns, layer boundaries, dependency rules              |
| Security / auth           | `SECURITY_AUTH_PATTERNS.md`          | Authentication, token strategy, credential handling, RBAC             |
| Testing                   | `TESTING.md`                         | Test philosophy, FIRST principles, test structure                     |
| Technology decisions      | `TECH_STACK.md`                      | Approved frameworks, libraries, tools, and versions                   |
| Design principles         | `DESIGN_PRINCIPLES.md`               | SOLID, DRY, YAGNI, KISS as applied to your stack                      |

These documents define your stack's specific approach. The architecture
principles (Hexagonal Architecture, boundaries, layered separation) are
universal; the implementation details are here.

Path-scoped instructions load automatically from `.github/instructions/govkit/` when
editing files matching their `applyTo` patterns:

* `api.instructions.md` — `**/api/**`
* `services.instructions.md` — `**/services/**`
* `ports.instructions.md` — `**/ports/**`
* `adapters.instructions.md` — `**/adapters/**`
* `security.instructions.md` — `**/security/**` and `**/auth/**`

---

## 3. Implementation Rules

* Respect all rules in `docs/backend/architecture/BOUNDARIES.md`
* Follow Hexagonal Architecture (ports and adapters)
* Use only approved frameworks from `docs/backend/architecture/TECH_STACK.md`
* Use approved auth patterns from `docs/backend/architecture/SECURITY_AUTH_PATTERNS.md`
* Follow API conventions from `docs/backend/architecture/API_CONVENTIONS.md`
* Follow design principles from `docs/backend/architecture/DESIGN_PRINCIPLES.md`
* Test-first is recommended for new code; the binding test-first rule is part
  of the Level 4 Spec-Driven Add-On

---

## 4. ADR Rules

An Architecture Decision Record (ADR) is required when:

* A standard is extended, overridden, or bypassed
* A new architectural pattern is introduced
* A security or auth approach changes
* A boundary rule or dependency direction changes
* A shared schema, API contract, event definition, or data model is introduced
  or modified

ADRs live under `docs/backend/architecture/ADR/`, follow
`docs/backend/architecture/ADR/TEMPLATE.md`, and must be Accepted before
implementation proceeds. Use the `/govkit-adr-author` skill to scaffold a new ADR.

---

## 5. Testing Requirements

Each change must include:

* Unit tests compliant with FIRST principles per
  `docs/backend/architecture/TESTING.md`
* Integration tests when crossing layer boundaries
* Contract tests when APIs, ports, or external integrations are affected

---

## 6. Automatic Refactor Conditions

Trigger refactor before proceeding if:

* Duplicate logic detected
* Structural complexity excessive
* Test flakiness detected

---

## 7. Output Expectations

Every implementation output must include:

* Referenced architecture contracts
* ADR status (Accepted / pending / not required — with justification)
* Architecture compliance confirmation
* Test coverage summary

If alignment is unclear, stop and ask.

---

## 8. Commit Discipline

* Each commit must be independently buildable and testable
* Commit message follows your project's convention; reference an ADR when one
  applies
* Keep commits focused — split large changes before committing

---

## 9. Authority

Architecture decisions belong to the Architect. Exceptions require an ADR and
explicit approval. Copilot follows standards — it does not invent them.

---

## 10. Upgrading to Spec-Driven Add-On (Level 4)

When your team is ready to adopt per-feature spec contracts, upgrade with:

```
govkit apply --level 4 --target <path>
```

Level 4 layers the following on top of Level 3:

* `features/<name>/` directory model with the 5-artifact governed contract
* `/govkit-spec-planning`, `/govkit-architecture-preflight`, `/govkit-implementation-plan` skills
* Test-first and spec-compliance instructions (binding, not just recommended)
* Evaluation prediction discipline (FIRST + 7 Virtues, average ≥ 4.0)
* Governance CI jobs: artifact existence, eval-criteria schema, prediction
  thresholds
