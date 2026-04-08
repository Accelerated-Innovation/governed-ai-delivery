# GitHub Copilot Instructions — Level 3 Spec-Driven Development (Angular UI)

These instructions govern how GitHub Copilot plans, reasons, and generates code in this Angular UI repository.

They are mandatory.

Copilot must treat this repository as a spec-driven delivery system.

Repository artifacts are the source of truth. Chat memory is not.

---

## 1. Operating Mode

Copilot operates aligned to:

* Product specifications under `features/`

Before planning or generating code:

* Confirm required feature artifacts exist
* Read `features/<feature_name>/acceptance.feature`, `nfrs.md`, and `plan.md`

If required inputs are missing, stop and ask.

---

## 2. Mandatory Feature Structure

Every feature must live under `features/<feature_name>/` with these artifacts:

* `acceptance.feature`
* `nfrs.md`
* `plan.md`

Implementation must not begin unless all artifacts exist and are complete.

---

## 3. Feature Lifecycle (Mandatory Order)

All work follows this sequence:

1. Write acceptance criteria
2. Complete NFRs
3. Spec Planning
4. Implementation Planning
5. Incremental implementation (test-first)
6. Component and E2E tests
7. CI gates (lint, type check, tests)

Steps may not be skipped.

---

## 4. Planning Discipline

For every feature:

* Generate and maintain `features/<feature_name>/plan.md`
* Base it on `governance/ui/templates/l3-plan.md`

The plan must:

* Define explicit increments with tests listed before deliverables
* Map Gherkin scenarios to E2E tests

---

## 5. Implementation Rules

* Implement one increment at a time
* Write tests before implementation code (test-first)
* Follow SOLID, DRY, YAGNI, KISS principles
* Use clear separation of concerns in components

---

## 6. Testing Requirements

Each increment must include:

* Component tests written before implementation code
* E2E tests for user-facing acceptance scenarios
* Accessibility checks where applicable

---

## 7. Automatic Refactor Conditions

Copilot must trigger refactor before proceeding if:

* Component contains business logic or data transformation
* Duplicate logic detected
* Structural complexity excessive
* Test flakiness detected

---

## 8. Authority

Architecture decisions belong to the team.

Copilot follows specifications. It does not invent them.

---

## 9. Commit Discipline

- Complete one increment, then commit before starting the next
- Each commit must be independently buildable and testable
- Commit message references the increment: `feat(<feature>): increment N — <name>`
- Do not combine multiple increments into a single commit
- If an increment exceeds ~300 lines of production code, split it before committing
