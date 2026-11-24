# ADR 0023: Criteria and measured scores in the feature evidence report

Status: Proposed with the L04 PR for #261. Merging that PR accepts the contract below.

## Context

ADR 0022 made `govkit evidence --feature` report a feature's scenarios. A feature with thresholds in `eval_criteria.yaml` could still report `PASS` with no criterion measured. Three things were missing.

- **No file carried a measured score.** The evaluation gate templates have placeholder steps.
- **GovKit and the graph disagreed on targets.** The Product Definition Graph compares a criterion through a `target` block. GovKit's schema had only `threshold` and `fail_on` and rejected `target`.
- **Nothing said who may run a criterion.** An agent could not tell an evaluation it should run from one that costs money or needs a person.

The plan assumed the backend, UI and data `eval_criteria` schemas shared a criterion shape. They do not. Only the backend schema has named criteria with numeric thresholds. The data schema lists an `id` with a predicate in words, and the UI schema has no criteria list. The graph reads a criterion by `name` and refuses a file whose criteria have none.

The maintainer decided on 2026-11-24: a GovKit results file, an optional target, `free` as the default class, and NFR values declared as criteria.

## Decision

1. **Criteria are results in the same report.** Each criterion is an entry of `kind: evaluation` beside the scenarios. The feature is `PASS` only when every scenario and every criterion passed.
2. **Identity is mirrored.** `criterion_identity.py` copies the engine's `criteria_from` and `_meets`. A fixture produced by running the engine pins identifiers, targets, refusals and every comparison.
3. **Scores come from one GovKit-defined file.** `govkit-eval-results*.json`, schema `evaluation-results` version 1. An entry names a criterion by identifier and gives a value or an error. An unusable file is an `ERROR`, never an empty result.
4. **An optional `target` on a backend criterion**, in the graph's shape. A target is compared ahead of `threshold`. A measurement must state the target's metric and unit, or the criterion is error.
5. **An optional `execution_class`**: `free` (default), `paid`, `human`. With no result, a free criterion is `missing` and a paid or human one is `owed`. Both are `INCONCLUSIVE`. An unknown class is an error.
6. **GovKit starts nothing.** It reads the results file and never runs an evaluation.
7. **NFR values get no new form.** A value to be compared is a criterion with a target.
8. **Other criteria forms are stated, not guessed.** Data-form criteria are not compared and prevent `PASS`. UI files add nothing.
9. **Schema version 1 of the report is extended.** It had not been released.

## Alternatives considered

- **Reading each tool's output.** No adapter for projects, but three changing formats to track and no support for any other tool.
- **A JUnit property for the score.** No new file, but it suits only evaluations that run as tests and has no natural place for a sample size.
- **Defaulting the class by mode, or requiring it.** The first makes one criterion mean different things in different files. The second invalidates every existing file.
- **Reading a mistyped class as free.** It would tell an agent to run something that costs money.
- **Ignoring data-form criteria silently.** The report would say `PASS` for criteria nobody checked.
- **Adding the fields to all three schemas.** The data and UI schemas have no criterion they could apply to.

## Consequences

- "Done" for a feature now includes its thresholds, and an agent can tell missing work from work that needs a person.
- A project must write a short step that turns its evaluation tool's output into the results file.
- A data feature with criteria cannot reach `PASS` until the data form is supported. That is a follow-up.
- The graph refuses a data-form criteria file outright, which is a question for `discovery-engine`.
- The value in a results file is whatever the project wrote. The report does not authenticate it, and L05 binds it to a commit.
- `execution_class`, the results file format, the criterion states and the `compared_with` shapes are public. Add, never rename.
