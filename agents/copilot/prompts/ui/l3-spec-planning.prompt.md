---
description: "Generate a UI feature plan (plan.md) from NFRs and acceptance scenarios — Level 3 Spec-Driven"
agent: "ask"
---

# Spec Planning — UI (Level 3)

Plan the implementation of the UI feature: **{{FEATURE_NAME}}**

## Inputs to read

- `features/{{FEATURE_NAME}}/acceptance.feature`
- `features/{{FEATURE_NAME}}/nfrs.md`

## Instructions

1. Read all inputs listed above.
2. Summarize the feature from the user's perspective.
3. Identify components, data flows, and API dependencies.
4. Map Gherkin scenarios to E2E tests.
5. For each increment, list tests before implementation deliverables.

## Output: Plan

Write `features/{{FEATURE_NAME}}/plan.md` based on `governance/ui/templates/l3-plan.md` with:
- Objective, scope boundaries, and assumptions
- Design alignment (principles, testing approach, dependencies)
- Ordered increments — each with goal, deliverables, tests (listed first), and definition of done
- Risks and mitigations
- Feature-level definition of done

## Output rules

- Tests must be listed before implementation deliverables in each increment.
- No implementation code in this step.
