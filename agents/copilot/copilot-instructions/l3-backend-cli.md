# GitHub Copilot Instructions — Level 3 Spec-Driven Development (CLI)

These instructions govern how GitHub Copilot plans, reasons, and generates code in this repository.

They are mandatory.

Copilot must treat this repository as a spec-driven delivery system.

Repository artifacts are the source of truth. Chat memory is not.

---

## 1. Operating Mode

Copilot operates aligned to:

* Product specifications under `features/`
* Design principles under `docs/backend/architecture/DESIGN_PRINCIPLES.md`
* Testing conventions under `docs/backend/architecture/TESTING.md`

Before planning or generating code:

* Read `docs/backend/architecture/DESIGN_PRINCIPLES.md`
* Read `docs/backend/architecture/TESTING.md`
* Confirm required feature artifacts exist

If required inputs are missing, stop and ask.

---

## 2. Mandatory Feature Structure

Every feature must live under:

`features/<feature_name>`

Required artifacts:

* `acceptance.feature`
* `nfrs.md`
* `plan.md`

Implementation must not begin unless these artifacts exist.

Before proceeding to planning:

* If `nfrs.md` contains TBD entries in any category, stop and request completion
* If `acceptance.feature` is empty or missing scenarios, stop and request completion

---

## 3. Feature Lifecycle (Mandatory Order)

All work follows this sequence:

1. Write acceptance criteria
2. Complete NFRs
3. Plan finalization
4. Implementation planning
5. Incremental implementation (test-first)
6. Automated tests
7. CI gates (lint, tests)

Steps may not be skipped.

---

## 4. Planning Discipline

Copilot must not rely on chat output as a plan.

For every feature:

* Generate and maintain `features/<feature_name>/plan.md`
* Base it on `governance/backend/templates/l3-plan.md`

### Plan Requirements

The plan must:

* Define explicit increments (`### Increment 1`, etc.)
* List tests before deliverables per increment (test-first)
* Map Gherkin scenarios to integration tests
* Reference design principles

---

## 5. Implementation Rules

### 5.1 Incremental Delivery

* Implement one increment at a time
* Do not expand scope beyond the active increment

### 5.2 Test-First Development

* Write failing tests before implementation code
* Do not skip or disable tests
* All listed tests must pass before moving to the next increment

### 5.3 Design Principles

* Follow SOLID, DRY, YAGNI, KISS from `docs/backend/architecture/DESIGN_PRINCIPLES.md`

### 5.4 Security

* Use approved auth patterns
* No custom crypto or token logic
* Avoid sensitive data in logs or stdout

---

## 6. Testing Requirements

Each increment must include:

* Unit tests written before implementation code
* Integration tests derived from Gherkin scenarios

Gherkin scenarios must follow conventions:

* Every populated NFR category in `nfrs.md` must have at least one scenario tagged with the corresponding `@nfr-*` tag

If a Gherkin scenario is not automated, the gap must be documented in `plan.md`.

---

## 7. Automatic Refactor Conditions

Copilot must trigger refactor before proceeding if:

* Duplicate logic detected
* Structural complexity excessive
* Test flakiness detected

Refactor must occur before expanding scope.

---

## 8. Output Expectations

Plans and implementations must include:

* Referenced design principles
* Test coverage summary

If alignment is unclear, stop and ask.

---

## 9. Authority

Architecture decisions belong to the team.

Copilot follows specifications. It does not invent them.

---

## 10. Commit Discipline

- Complete one increment, then commit before starting the next
- Each commit must be independently buildable and testable
- Commit message references the increment: `feat(<feature>): increment N — <name>`
- Do not combine multiple increments into a single commit
- If an increment exceeds ~300 lines of production code, split it before committing
