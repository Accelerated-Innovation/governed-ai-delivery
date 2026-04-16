---
name: l3-implementation-plan
description: Generate an ordered implementation checklist from a feature plan — Level 3 Spec-Driven
---

# Implementation Plan (Level 3)

You are writing an implementation plan for a feature. Determine the feature name from the user's request; if it is not provided, ask before proceeding.

## Inputs

Read these artifacts before planning:

- `features/<feature_name>/nfrs.md`
- `features/<feature_name>/acceptance.feature`
- `features/<feature_name>/plan.md`
- `docs/backend/architecture/DESIGN_PRINCIPLES.md`
- `docs/backend/architecture/TESTING.md`

## Planning Requirements

The plan must:

- Enforce test-first development (tests before implementation in every step)
- Follow SOLID, DRY, YAGNI, KISS principles
- Respect existing project structure and conventions

## Output Format

### Feature Summary

- Business goal, user value, success criteria

### Task Breakdown (Ordered Checklist)

List all implementation steps in order. Each step must:

- Specify files/modules touched
- Reference the spec or design principle driving it
- Mark test steps explicitly (write tests before implementation)

### Test Plan

- Unit test strategy (mocking, isolation)
- Integration test strategy (derived from Gherkin scenarios)
- Simplicity and duplication risks

### Refactor Triggers

List conditions under which refactoring must occur:

- Duplication detected
- Complexity threshold exceeded
- Test flakiness detected

### Risks & Unknowns

Missing constraints, integration risks, performance concerns, security implications.

---

Do not generate implementation code. Plan must be executable as-is.
