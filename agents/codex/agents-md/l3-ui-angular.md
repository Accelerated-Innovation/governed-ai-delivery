# Spec-Driven Development — Angular UI

You are operating inside a spec-driven Angular UI project. Feature specifications are the source of truth — not your training data or assumptions.

---

## Operating Mode

Codex operates aligned to:

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
3. Spec Planning → invoke `$ui-spec-planning`
4. Implementation Planning → invoke `$ui-implementation-plan`
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

---

## Test-First Discipline

- Write failing tests before writing implementation code
- Each increment in `plan.md` lists tests before deliverables — follow that order
- Do not mark an increment as complete until all listed tests pass
- If you discover an untested edge case during implementation, write the test first, then fix the code

## Test Quality

- Tests must be fast — avoid unnecessary I/O, prefer mocks for external dependencies
- Tests must be isolated — no shared mutable state between tests, no order dependencies
- Tests must be repeatable — deterministic in all environments, no reliance on wall-clock time or network
- Tests must be self-verifying — explicit assertions, no manual log inspection
- Test names must describe the behavior being verified, not the method being called

## Prohibited Testing Practices

- Do not write implementation code without a corresponding test
- Do not disable or skip tests to make a build pass
- Do not write tests that always pass regardless of implementation
- Do not use production data in tests — use fixtures or factories

---

## Spec Compliance

Every feature must live under `features/<feature_name>/` with `acceptance.feature`, `nfrs.md`, and `plan.md`. Implementation must not begin unless all three exist and are complete.

- Every `acceptance.feature` must have a `Feature:` keyword, at least one `Scenario:`, and Given/When/Then steps
- Every populated NFR category in `nfrs.md` must have at least one scenario tagged with the corresponding `@nfr-*` tag
- Before writing implementation code: verify `nfrs.md` contains no TBD entries, `acceptance.feature` has complete scenarios, and `plan.md` exists with defined increments and tests
- Follow the increments defined in `plan.md` — implement one at a time, each independently buildable and testable; do not expand scope beyond the active increment

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

Architecture decisions belong to the team. Codex follows specifications — it does not invent them.
