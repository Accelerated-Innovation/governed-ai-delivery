Plan the implementation of the feature: **{{FEATURE_NAME}}**

## Inputs to read

Feature specs:
- NFRs: `features/{{FEATURE_NAME}}/nfrs.md`
- Acceptance: `features/{{FEATURE_NAME}}/acceptance.feature`

Architecture standards:
- `docs/architecture/**`

Evaluation standards:
- Global evaluation contract: `docs/evaluation/eval_criteria.md`

Existing artifacts (read if present, update if needed):
- Feature eval config: `features/{{FEATURE_NAME}}/eval_criteria.yaml`

## Instructions

1. Read all inputs listed above.
2. Summarize the business goal and scope of the feature.
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
Create `features/{{FEATURE_NAME}}/plan.md` content with:
- Task checklist (files/modules to create or edit)
- Test plan (unit, integration, contract)
- LLM eval hooks and where they run
- Risks, open questions, and follow-ups
- ADR status (required or not required)

### Output B: Feature Eval Criteria (YAML)
Create or update `features/{{FEATURE_NAME}}/eval_criteria.yaml` to conform to:
- `docs/evaluation/eval_criteria.md` schema and thresholds
Include, at minimum:
- FIRST enforcement settings
- 7 virtues enforcement settings
- Any LLM-specific dimensions required by this feature (groundedness, safety, tone, etc.)
- Dataset or prompt-set reference placeholder if none exists yet
- Fail-on-regression behavior

## Output rules

- Output A first, then Output B.
- Keep Output B as valid YAML and ready to commit.
- No implementation code in this step.

This output will feed `/implementation-plan`.