# Spec-Driven Development — Angular UI

You are operating inside a spec-driven Angular UI project. Feature specifications are the source of truth — not your training data or assumptions.

---

## Operating Mode

Claude operates aligned to:

- Product specifications under `features/`

Before planning or generating code:

- Confirm required feature artifacts exist
- Read `features/<feature_name>/acceptance.feature`, `nfrs.md`, and `plan.md`

If required inputs are missing, stop and ask.

---

## Mandatory Feature Structure

Every feature must live under `features/<feature_name>` with these required artifacts:

- `acceptance.feature`
- `nfrs.md`
- `plan.md`

Implementation must not begin unless all three artifacts exist.

---

## Feature Lifecycle (Mandatory Order — no steps may be skipped)

1. Write acceptance criteria (`acceptance.feature`)
2. Complete NFRs (`nfrs.md`)
3. Spec Planning → run `/spec-planning`
4. Implementation Planning → run `/implementation-plan`
5. Incremental implementation (test-first)
6. Component and E2E tests
7. CI gates (lint, type check, tests)

---

## Planning Discipline

Generate and maintain `features/<feature_name>/plan.md` based on `governance/ui/templates/l3-plan.md`.

The plan must:

- Define explicit increments with deliverables and tests
- Map Gherkin scenarios to E2E tests
- List tests before implementation in each increment

---

## Implementation Rules

- Implement one increment at a time
- Write tests before implementation code (test-first)
- Follow SOLID, DRY, YAGNI, KISS principles
- Use clear separation of concerns in components

Generic rules load automatically from `.claude/rules/`:

- `test-first.md` — test-first development discipline
- `spec-compliance.md` — feature artifact and Gherkin conventions

---

## Testing Requirements

Each increment must include:

- Component tests written before implementation code
- E2E tests for user-facing acceptance scenarios
- Accessibility checks where applicable

---

## Automatic Refactor Conditions

Trigger refactor before proceeding if:

- Component contains business logic or data transformation
- Duplicate logic detected
- Structural complexity excessive
- Test flakiness detected

---

## Commit Discipline

- Complete one increment, then commit before starting the next
- Each commit must be independently buildable and testable
- Commit message references the increment: `feat(<feature>): increment N — <name>`
- Do not combine multiple increments into a single commit
- If an increment exceeds ~300 lines of production code, split it before committing

---

## Authority

Architecture decisions belong to the team. Claude follows specifications — it does not invent them.
