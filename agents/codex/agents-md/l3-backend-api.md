# Spec-Driven Development — Codex Agent Instructions

These instructions are mandatory. Codex operates as a spec-driven delivery system.

Repository artifacts are the source of truth. Chat history is not.

---

## Operating Mode

Codex operates aligned to:

- Product specifications under `features/`
- Design principles under `docs/backend/architecture/DESIGN_PRINCIPLES.md`
- Testing conventions under `docs/backend/architecture/TESTING.md`

Before planning or generating code:

- Read `docs/backend/architecture/DESIGN_PRINCIPLES.md`
- Read `docs/backend/architecture/TESTING.md`
- Confirm required feature artifacts exist

If required inputs are missing, stop and ask.

---

## Mandatory Feature Structure

Every feature must live under `features/<feature_name>` with these required artifacts:

- `acceptance.feature`
- `nfrs.md`
- `plan.md`

Implementation must not begin unless all three artifacts exist.

Before proceeding to planning:

- If `nfrs.md` contains TBD entries in any category, stop and request completion
- If `acceptance.feature` is empty or missing scenarios, stop and request completion

---

## Feature Lifecycle (Mandatory Order — no steps may be skipped)

1. Write acceptance criteria (`acceptance.feature`)
2. Complete NFRs (`nfrs.md`)
3. Plan finalization → invoke `$spec-planning`
4. Implementation planning → invoke `$implementation-plan`
5. Incremental implementation (test-first)
6. Automated tests
7. CI gates (lint, tests)

---

## Planning Discipline

Generate and maintain `features/<feature_name>/plan.md` based on `governance/backend/templates/l3-plan.md`.

The plan must:

- Define explicit increments with deliverables and tests
- Map Gherkin scenarios to integration tests
- List tests before implementation in each increment

---

## Implementation Rules

- Implement one increment at a time
- Write tests before implementation code (test-first)
- Follow design principles from `docs/backend/architecture/DESIGN_PRINCIPLES.md` (SOLID, DRY, YAGNI, KISS)
- Follow testing conventions from `docs/backend/architecture/TESTING.md`

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

### Feature Artifacts

Every feature must live under `features/<feature_name>/` with these required artifacts:

- `acceptance.feature` — Gherkin scenarios with Given/When/Then steps
- `nfrs.md` — Non-functional requirements (no TBD entries permitted)
- `plan.md` — Implementation plan with increments, tests, and deliverables

Implementation must not begin unless all three artifacts exist and are complete.

### Gherkin Conventions

- Every `acceptance.feature` must have a `Feature:` keyword, at least one `Scenario:`, and Given/When/Then steps
- Every populated NFR category in `nfrs.md` must have at least one scenario tagged with the corresponding `@nfr-*` tag
- Features producing shared artifacts should include `@contract` scenarios

### Pre-Implementation Checks

Before writing any implementation code:

- Verify `nfrs.md` contains no TBD entries
- Verify `acceptance.feature` has complete scenarios
- Verify `plan.md` exists with defined increments and tests

If any artifact is incomplete, stop and request completion before proceeding.

### Plan Discipline

- Follow the increments defined in `plan.md`
- Implement one increment at a time
- Each increment must be independently buildable and testable
- Do not expand scope beyond the active increment

---

## Testing Requirements

Each increment must include:

- Unit tests written before implementation code
- Integration tests derived from Gherkin scenarios

Gherkin scenarios must follow conventions:

- Every populated NFR category in `nfrs.md` must have at least one scenario tagged with the corresponding `@nfr-*` tag

---

## Automatic Refactor Conditions

Trigger refactor before proceeding if:

- Duplicate logic detected
- Structural complexity excessive
- Test flakiness detected

---

## Output Expectations

Every plan and implementation output must include:

- Referenced design principles
- Test coverage summary

If alignment is unclear, stop and ask.

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
