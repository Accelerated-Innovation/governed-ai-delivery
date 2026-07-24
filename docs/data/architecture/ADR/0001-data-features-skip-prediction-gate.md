# ADR-0001: Data features carry no FIRST/Virtue evaluation prediction

## Status
Accepted

## Date
2026-07-24

## Authors
- govkit maintainers

---

## 1. Context

Backend and UI features at L4 require an `evaluation_prediction` block in
`plan.md`: a self-predicted FIRST (test quality) and 7-Virtue (code quality)
score, each averaging ≥ 4.0, checked by `govkit validate`.

For data features the block never fit:

- The FIRST rubric scores unit-test design; data features are verified by
  schema tests, singular tests, and query predicates — a different surface
  with its own contract (`DATA_QUALITY_CONTRACT.md`, `eval_criteria.yaml`).
- The 7 Virtues rubric (Working / Unique / Simple / Clear / Easy /
  Developed / Tested) was written for application code. The data starter's
  copy drifted into an undocumented vocabulary
  (correctness/clarity/composability/…), which no rubric doc defines and no
  team has calibrated.
- A self-predicted ≥ 4.0 average is ceremony either way: the prediction is
  authored by the same agent that authors the plan, against a rubric the
  data team has no calibration history for.

## 2. Decision

Drop the `evaluation_prediction` requirement for `--type data` features.
`govkit validate` skips the prediction check when the marker records
`type: data`. Enforcement for data features is carried by:

- artifact completeness (the 5-artifact L4 contract still applies),
- `eval_criteria.yaml` validated against the data schema
  (`governance/data/schemas/eval_criteria.schema.json`) — deterministic
  criteria measured by queries and CI outcomes,
- the mart-contract CI gate (enforced model contracts + exposure coverage),
- the data NFR tag coverage check.

A data-native scored rubric (contract completeness, test-tier coverage,
lineage coverage) is deliberately **not** introduced now: inventing a
rubric nobody has calibrated recreates the ceremony this ADR removes. If a
team asks for a scored gate, that becomes a new ADR superseding this one.

## 3. Consequences

- `features/<name>/plan.md` for data features contains no
  `evaluation_prediction` block; the starter ships without one.
- Backend and UI features are unchanged — the prediction gate still
  applies there.
- Teams that want a prediction anyway may keep the block in their plans;
  validate simply does not require or score it for data features.
