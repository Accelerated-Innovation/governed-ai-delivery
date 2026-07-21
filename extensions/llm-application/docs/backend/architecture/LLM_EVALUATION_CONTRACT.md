# LLM Evaluation Contract

## 1. Decision and scope

Every model-backed feature MUST have versioned evaluation criteria and release evidence proportionate to its behavior and risk. Evaluation measures whether a model configuration is fit for a defined use; it does not certify a model in the abstract.

This contract is tool neutral. Evaluation products are adapters that execute declared criteria and produce normalized evidence.

## 2. Evaluation definition

An evaluation definition MUST bind:

- feature and use-case identity
- model routing configuration and logical model alias
- prompt, tool, retrieval, guardrail, and policy versions
- dataset version and provenance
- slice definitions and risk categories
- metric or assertion definitions, evaluator versions, thresholds, and failure policy
- environment controls such as sampling parameters and random seeds when supported
- evidence schema version and execution timestamp

Changing any behavior-moving input creates a new evaluation subject and MUST trigger the applicable regression suite.

## 3. Evaluation families

Architecture preflight MUST select every applicable family and justify omissions:

| Family | Typical assertions |
|---|---|
| Deterministic | schema validity, citations present, policy labels, exact fields, tool arguments |
| Task quality | correctness, relevance, completeness, faithfulness, instruction adherence |
| Safety and adversarial | prompt injection, jailbreaks, harmful output, data leakage, policy bypass |
| Retrieval | context precision and recall, grounding, source coverage, answer attribution |
| Tool use | tool selection, argument validity, authorization boundary, abstention, recovery |
| Operational | latency, availability, rate-limit behavior, token use, cost, fallback behavior |
| Fairness and accessibility | declared population slices, language support, disparate failure patterns |

Deterministic assertions SHOULD be used wherever possible. Statistical or model-graded evaluation MUST be used only where deterministic or human-labelled checks cannot express the behavior adequately.

## 4. Datasets and contamination controls

- Evaluation datasets MUST be versioned, immutable for a recorded run, and linked to provenance.
- Training, tuning, development, acceptance, and production-monitoring sets MUST have declared separation rules.
- Sensitive examples MUST use approved storage, access, retention, and redaction controls.
- Synthetic examples MUST be labelled with their generator and generation configuration.
- Each material risk MUST have negative and boundary cases, not only happy-path examples.
- Aggregate scores MUST NOT hide a failing required slice.
- Dataset changes require review when they can move a release threshold.

## 5. Evaluators and oracles

Each criterion MUST name an oracle type: deterministic assertion, reference answer, human review, executable outcome, statistical detector, or model judge.

For a model judge:

- the rubric, judge prompt, judge model/configuration, and parsing logic MUST be versioned
- the judge MUST be calibrated against representative human-labelled examples
- positional, verbosity, self-preference, and shared-failure bias MUST be considered
- the judge SHOULD be independent of the evaluated model when correlated failure is material
- invalid, unavailable, or ambiguous judge output MUST be inconclusive, not passing
- consequential acceptance decisions MUST have deterministic or human escalation where required by risk

Evaluator adapters MUST normalize evidence without leaking framework-specific objects into feature governance files.

## 6. Thresholds and release gates

Thresholds MUST be declared before the gated run and MUST identify whether they apply per example, per slice, or in aggregate. A release gate MUST fail or become inconclusive when:

- a required criterion or slice misses its threshold
- required evidence is missing, stale, malformed, or produced by an unapproved evaluator version
- a regression exceeds its allowed budget
- safety-critical cases fail, even if the aggregate score passes
- sample size or confidence is insufficient for the declared claim

Threshold relaxation, criterion removal, or baseline reset requires review and an auditable rationale. Re-running until a favourable sample appears is prohibited.

## 7. Offline and production evaluation

Offline evaluation MUST run before promotion for every behavior-moving change. Production evaluation MAY add sampled feedback, outcome metrics, human review, or shadow comparisons, but it MUST respect consent, data minimization, and retention policy.

Production signals MUST be correlated with the invocation identity and immutable configuration identities from the observability contract. Production feedback MUST NOT silently become training or evaluation data without provenance and approval.

## 8. Evidence

Each run MUST produce durable evidence containing:

- evaluation definition identity and digest
- subject configuration identities
- dataset and evaluator identities
- per-case outcomes and required slice aggregates
- threshold decisions and reasons
- excluded or inconclusive cases
- environment and timing metadata
- links to redacted diagnostics sufficient to reproduce or investigate the result

Reports MUST distinguish observed facts from evaluator inference. A passing score MUST NOT claim coverage beyond the declared dataset, slices, and criteria.

## 9. Verification

Tests MUST cover:

- schema validation for evaluation definitions and evidence
- deterministic reproducibility where claimed
- threshold boundary behavior
- missing, stale, invalid, and inconclusive evidence
- required slice failure despite aggregate success
- judge parsing and calibration failure
- dataset access and redaction controls
- regression detection across prompt, model, retrieval, guardrail, and routing changes

## 10. ADR triggers

An ADR is required for:

- selecting or replacing an evaluation framework or model judge
- introducing a new oracle type for a release gate
- changing dataset separation or production feedback use
- lowering a threshold, removing a required slice, or accepting an inconclusive gate
- allowing production promotion without the normally required evaluation family

## 11. Prohibited patterns

- unversioned prompts, datasets, rubrics, judges, or thresholds
- aggregate-only acceptance for a risk with required slices
- using a model's self-assessment as the sole acceptance oracle
- treating evaluator errors or missing evidence as passes
- tuning against the final acceptance set
- logging or exporting sensitive evaluation content outside approved boundaries
- claiming general model safety or quality from a use-case-limited evaluation
