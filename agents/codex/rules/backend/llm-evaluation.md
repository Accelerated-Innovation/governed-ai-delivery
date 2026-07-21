# LLM Evaluation Rules

These rules apply when editing model evaluation definitions, tests, datasets, and evidence.

Contract: `extensions/llm-application/docs/backend/architecture/LLM_EVALUATION_CONTRACT.md`

---

## Rules

- Every model-backed feature declares versioned criteria, datasets, slices, oracles, thresholds, and failure policy
- Select all applicable evaluation families: deterministic, task quality, safety/adversarial, retrieval, tool use, operational, and fairness/accessibility
- Prefer deterministic assertions; use human review or a calibrated model judge only where deterministic checks are insufficient
- Bind every run to immutable model-routing, prompt, retrieval, guardrail, dataset, evaluator, and configuration identities
- Version evaluation datasets and keep development and final acceptance sets separated by declared policy
- Safety-critical and required-slice failures block release even when an aggregate score passes
- Missing, stale, malformed, ambiguous, or insufficient evidence is inconclusive or failing, never passing
- A model judge has a versioned rubric and configuration, calibration evidence, parsing-failure behavior, and bias controls
- Record selected evaluation tools as adapters in `TECH_STACK.md` or an ADR; no product is required by the architecture contract

## Prohibited

- Unversioned prompts, datasets, rubrics, evaluators, judges, or thresholds
- Aggregate-only acceptance that hides a failing required slice
- A model's self-assessment as the sole acceptance oracle
- Re-running until a favourable sample appears
- Treating evaluator errors or missing evidence as passes
- Tuning against the final acceptance set
