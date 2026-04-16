---
name: ui-implementation-plan
description: Generate an ordered UI implementation checklist from a feature plan — Level 3 Spec-Driven
---

# Implementation Plan — UI (Level 3)

You are producing an Implementation Plan for a UI feature. Determine the feature name from the user's request; if it is not provided, ask before proceeding.

## Inputs

Read the following before proceeding:

- `features/<feature_name>/plan.md`
- `features/<feature_name>/acceptance.feature`
- `features/<feature_name>/nfrs.md`

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

- Specify files/components touched
- Reference the spec driving it
- Mark test steps explicitly (write tests before implementation)

### Test Plan

- Component test strategy
- E2E test strategy (mapped from Gherkin scenarios)
- Accessibility testing approach

### Refactor Triggers

- Component contains business logic
- Duplication detected
- Test flakiness detected

### Risks & Unknowns

Missing constraints, backend dependency risks, performance concerns.

---

Review and approve this plan before beginning implementation. Do not generate implementation code.
