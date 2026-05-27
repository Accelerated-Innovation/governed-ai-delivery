---
name: spec-planning
description: Generate a feature plan (plan.md) and eval_criteria.yaml from NFRs and acceptance scenarios. Use when the user asks to plan a feature or invokes /spec-planning.
---

# Spec Planning

Plan the implementation of the named feature. When invoked, determine the feature name from the user's request; if it is not provided, ask before proceeding.

## Inputs to read

Feature specs:
- NFRs: `features/<feature_name>/nfrs.md`
- Acceptance: `features/<feature_name>/acceptance.feature`

Architecture standards:
- `docs/backend/architecture/` (all files)

Evaluation standards:
- `docs/backend/evaluation/eval_criteria.md`

Existing artifacts (read if present, update if needed):
- `features/<feature_name>/eval_criteria.yaml`

## Instructions

1. Read all inputs listed above.
2. Summarize the business goal and scope of the feature.
3. Identify required design elements per **this project's architecture**:
   - Read `.govkit/skill_context.yaml` for the architecture style and the
     folder hints under `architecture.layers` (inbound / outbound / domain).
   - Read `docs/backend/architecture/BOUNDARIES.md` for the canonical layer
     contract and `LAYER_IMPLEMENTATION.md` for the layer-by-layer guidance.
   - List the inbound entry points, domain logic modules, outbound
     dependencies, and any infrastructure adapters the feature needs —
     using the project's own folder names, not generic ones.
4. Flag any deviation from architecture contracts:
   - `ARCH_CONTRACT.md`, `BOUNDARIES.md`, `API_CONVENTIONS.md`, `SECURITY_AUTH_PATTERNS.md`
5. Determine ADR need. Mark **ADR required** if any of these occur:
   - New outbound dependency or external integration
   - Boundary change or exception
   - New pattern or approach not already documented

## Output A: Plan

Write `features/<feature_name>/plan.md` with:
- Task checklist (files/modules to create or edit)
- Test plan (unit, integration, contract)
- LLM eval hooks and where they run
- Risks, open questions, and follow-ups
- ADR status (required or not required)

## Output B: Feature Eval Criteria

Write or update `features/<feature_name>/eval_criteria.yaml` conforming to `docs/backend/evaluation/eval_criteria.md`. Include at minimum:
- FIRST enforcement settings
- 7 Virtues enforcement settings
- Any LLM-specific dimensions required by this feature
- Dataset or prompt-set reference placeholder
- Fail-on-regression behavior

Output A first, then Output B. No implementation code in this step.
