---
name: govkit-spec-planning
description: Generate a feature plan (plan.md) and eval_criteria.yaml from NFRs and acceptance scenarios. Use when the user asks to plan a feature or invokes /govkit-spec-planning.
---

Plan the implementation of the named feature. When invoked, determine the feature name from the user's request; if it is not provided, ask before proceeding.

## Multi-service repos

Read `.govkit/skill_context.yaml` before planning. When it lists more than
one entry under `architecture.services`, this repo holds several services
and every path in your output has to land inside one of them:

```yaml
architecture:
  source_root: ''
  services:
    - name: billing
      root: src/billing
    - name: orders
      root: src/orders
```

1. Work out which service the feature belongs to. Take it from the request
   when it names one — by service name, or by a path under that service's
   `root`.
2. If the request names none, **ask which service to plan for** and list the
   names. Do not guess, and do not plan across all of them at once.
3. Prefix every file path in your output with that service's `root`. A task
   touching `services/pricing.py` in the `orders` service is
   `src/orders/services/pricing.py`.
4. Name the chosen service in the plan summary, so a reader knows which part
   of the repo the plan applies to.

When `architecture.services` is absent, the repo holds a single service.
Use `architecture.source_root` as the prefix instead — an empty value means
the layer folders sit at the repo root and paths need no prefix.

## Inputs to read

Feature specs:
- NFRs: `features/<feature_name>/nfrs.md`
- Acceptance: `features/<feature_name>/acceptance.feature`

Architecture standards:
- `docs/{{docs_area}}/architecture/**`

Evaluation standards:
- Global evaluation contract: `docs/{{docs_area}}/evaluation/eval_criteria.md`

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
- `docs/{{docs_area}}/evaluation/eval_criteria.md` schema and thresholds
Include, at minimum:
- FIRST enforcement settings
- 7 virtues enforcement settings
- Any LLM-specific dimensions required by this feature (groundedness, safety, tone, etc.)
- Dataset or prompt-set reference placeholder if none exists yet
- Fail-on-regression behavior

### Output A: Evaluation Compliance Summary

plan.md must include an Evaluation Compliance Summary with predicted FIRST and Virtue scores. Use the scoring rubrics for reference:

- FIRST rubric: `docs/{{docs_area}}/evaluation/FIRST_SCORING_RUBRIC.md`
- Virtue rubric: `docs/{{docs_area}}/evaluation/VIRTUE_SCORING_RUBRIC.md`

Do not proceed if predicted FIRST average or Virtue average is below 4.0.

## Output rules

- Output A first, then Output B.
- Keep Output B as valid YAML and ready to commit.
- No implementation code in this step.

This output will feed `/govkit-implementation-plan`.

### Data projects

For data projects (marker `type: data`), adjust the spec outputs:

- NFR categories are `freshness`, `quality`, `pii`, `lineage`, `cost`
  (plus `reliability`, `observability`, `compliance` where relevant).
  Tag scenarios `@nfr-<category>` — the eval gate cross-checks every
  populated category against the tags.
- `eval_criteria.yaml` uses the data schema: `mode: deterministic` (or
  `none`), and each criterion's `measurement` names a query or CI check
  with `threshold` as a predicate string. No LLM evaluator tools.
- Cite the data quality, freshness, and lineage contracts under
  `docs/data/architecture/` instead of API conventions and auth patterns.
