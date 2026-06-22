---
name: spec-planning
description: Generate a feature plan (plan.md) and eval_criteria.yaml from NFRs and acceptance scenarios. Use when the user asks to plan a feature or invokes /spec-planning.
---

Plan the implementation of the named feature. When invoked, determine the feature name from the user's request; if it is not provided, ask before proceeding.

## Inputs to read

Feature specs:
- NFRs: `features/<feature_name>/nfrs.md`
- Acceptance: `features/<feature_name>/acceptance.feature`

Architecture standards:
- `docs/backend/architecture/**`

Evaluation standards:
- Global evaluation contract: `docs/backend/evaluation/eval_criteria.md`

Existing artifacts (read if present, update if needed):
- Feature eval config: `features/<feature_name>/eval_criteria.yaml`

## Instructions

1. Read all inputs listed above.
2. Summarize the business goal and scope of the feature.
2a. Populate the plan's `### Out of scope` from `nfrs.md` `## Out of scope`:
   - If `nfrs.md` has a non-empty `## Out of scope` section, copy its entries into the plan verbatim (author-declared — no marker).
   - If `## Out of scope` is missing or empty, infer the deferred capabilities from the spec's negative space (domain neighbors with no scenarios), then BOTH:
     - insert `<!-- INFERRED: not declared in nfrs.md ## Out of scope; confirm with feature owner -->` directly under the plan's `### Out of scope` heading, and
     - state in the planning summary that Out-of-scope was inferred and should be confirmed.
3. Identify required design elements aligned to Hexagonal Architecture:
   - Inbound ports (`ports/inbound/**`)
   - Domain logic modules (`services/**`)
   - Outbound ports (`ports/outbound/**`)
   - Adapters (`adapters/**`)
   - API route entrypoints (`api/**`)
4. Flag any deviation from architecture contracts:
   - `ARCH_CONTRACT.md`
   - `BOUNDARIES.md`
   - `API_CONVENTIONS.md`
   - `SECURITY_AUTH_PATTERNS.md`
5. Determine ADR need. Mark **ADR required** if any of these occur:
   - New outbound dependency or external integration
   - Boundary change or exception
   - New pattern or approach not already documented
6. Produce two outputs:

### Output A: Plan (Markdown)
Create `features/<feature_name>/plan.md` content with:
- Task checklist (files/modules to create or edit)
- Test plan (unit, integration, contract)
- LLM eval hooks and where they run
- Risks, open questions, and follow-ups
- ADR status (required or not required)

### Output B: Feature Eval Criteria (YAML)
Create or update `features/<feature_name>/eval_criteria.yaml` to conform to:
- `docs/backend/evaluation/eval_criteria.md` schema and thresholds
Include, at minimum:
- FIRST enforcement settings
- 7 virtues enforcement settings
- Any LLM-specific dimensions required by this feature (groundedness, safety, tone, etc.)
- Dataset or prompt-set reference placeholder if none exists yet
- Fail-on-regression behavior

### Output A: Evaluation Compliance Summary

plan.md must include an Evaluation Compliance Summary with predicted FIRST and Virtue scores. Use the scoring rubrics for reference:

- FIRST rubric: `docs/backend/evaluation/FIRST_SCORING_RUBRIC.md`
- Virtue rubric: `docs/backend/evaluation/VIRTUE_SCORING_RUBRIC.md`

Do not proceed if predicted FIRST average or Virtue average is below 4.0.

## Output rules

- Output A first, then Output B.
- Keep Output B as valid YAML and ready to commit.
- No implementation code in this step.

This output will feed `/implementation-plan`.
