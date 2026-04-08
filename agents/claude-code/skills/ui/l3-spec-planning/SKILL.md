---
description: "Generate a UI feature plan (plan.md) from NFRs and acceptance scenarios — Level 3 Spec-Driven"
argument-hint: "<feature_name>"
---

# Spec Planning — UI (Level 3)

Plan the implementation of the UI feature: **$ARGUMENTS**

## Inputs to read

- `features/$ARGUMENTS/acceptance.feature`
- `features/$ARGUMENTS/nfrs.md`

## Instructions

1. Read all inputs listed above.
2. Summarize the feature from the user's perspective.
3. Identify components, data flows, and API dependencies.
4. Map Gherkin scenarios to E2E tests.
5. For each increment, list tests before implementation deliverables.

## Output: Plan

Write `features/$ARGUMENTS/plan.md` based on `governance/ui/templates/l3-plan.md` with:

- Objective, scope boundaries, and assumptions
- Design alignment (principles, testing approach, dependencies)
- Ordered increments — each with goal, deliverables, tests (listed first), and definition of done
- Risks and mitigations
- Feature-level definition of done

Tests must be listed before implementation deliverables in each increment to reinforce test-first development.

No implementation code in this step.
