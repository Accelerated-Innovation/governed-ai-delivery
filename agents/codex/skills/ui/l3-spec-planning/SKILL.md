---
name: ui-spec-planning
description: Generate a UI feature plan (plan.md) from NFRs and acceptance scenarios — Level 3 Spec-Driven
---

# Spec Planning — UI (Level 3)

Plan the implementation of a UI feature. Determine the feature name from the user's request; if it is not provided, ask before proceeding.

## Inputs to read

- `features/<feature_name>/acceptance.feature`
- `features/<feature_name>/nfrs.md`

## Instructions

1. Read all inputs listed above.
2. Summarize the feature from the user's perspective.
3. Identify components, data flows, and API dependencies.
4. Map Gherkin scenarios to E2E tests.
5. For each increment, list tests before implementation deliverables.

## Output: Plan

Write `features/<feature_name>/plan.md` based on `governance/ui/templates/l3-plan.md` with:

- Objective, scope boundaries, and assumptions
- Design alignment (principles, testing approach, dependencies)
- Ordered increments — each with goal, deliverables, tests (listed first), and definition of done
- Risks and mitigations
- Feature-level definition of done

Tests must be listed before implementation deliverables in each increment to reinforce test-first development.

No implementation code in this step.
