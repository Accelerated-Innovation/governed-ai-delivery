---
name: l3-spec-planning
description: Generate a feature plan (plan.md) from NFRs and acceptance scenarios — Level 3 Spec-Driven
argument-hint: "<feature_name>"
user-invocable: true
---

Plan the implementation of the feature: **$ARGUMENTS**

## Inputs to read

Feature specs:
- NFRs: `features/$ARGUMENTS/nfrs.md`
- Acceptance: `features/$ARGUMENTS/acceptance.feature`

Design principles:
- `docs/backend/architecture/DESIGN_PRINCIPLES.md`

Testing conventions:
- `docs/backend/architecture/TESTING.md`

## Instructions

1. Read all inputs listed above.
2. Summarize the business goal and scope of the feature.
3. Identify required design elements:
   - Key modules or classes to create or modify
   - Dependencies (internal and external)
   - Data stores or services involved
4. Map Gherkin scenarios to integration tests.
5. For each increment, list tests before implementation deliverables.

## Output: Plan

Create `features/$ARGUMENTS/plan.md` based on `governance/backend/templates/l3-plan.md` with:
- Objective, scope boundaries, and assumptions
- Design alignment (principles, testing approach, dependencies, security)
- Ordered increments — each with goal, deliverables, tests (listed first), and definition of done
- Risks and mitigations
- Feature-level definition of done

## Output rules

- Tests must be listed before implementation deliverables in each increment.
- No implementation code in this step.
- This output will feed `/implementation-plan`.
