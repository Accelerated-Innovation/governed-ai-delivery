# Evaluation, Evidence, and Completion Contract

## Source alignment

| Field | Value |
|---|---|
| Primary decisions | SOAA-016 and SOAA-017 |
| Primary invariants | SOAA-INV-103 through SOAA-INV-146 |
| Source module | SOAA Packet 5 |

## Purpose

This contract separates evaluation, evidence, gate decisions, task completion, and conformance. Agent confidence, skill success, fluent explanation, and absence of visible error are never sufficient completion evidence.

## Separate concepts

| Concept | Meaning | Authoritative owner |
|---|---|---|
| Evaluation | Measurement of a target against explicit criteria | Evaluation Controller |
| Evidence | Immutable source-linked observation record | Evidence Recorder |
| Gate decision | Deterministic application of policy to evaluated claims | Evaluation Controller |
| Completion | Task lifecycle transition after gate pass | Task Controller |
| Conformance | Requirement adherence for a named profile | Conformance assessor and report authority |

## Evaluation modes

Use the modes relevant to the governing decision:

- Design evaluation
- Skill admission
- Capability evaluation
- Regression evaluation
- Runtime gate
- Completion evaluation
- Production shadow evaluation
- Incident evaluation
- Conformance evaluation

Evaluation definitions are versioned governed artifacts. Threshold, rubric, grader, dataset, aggregation, independence, or blocking-rule changes create new versions.

## Evaluation definition

An EvaluationDefinition must identify:

- Purpose and mode
- Target and risk classes
- Dimensions and suites
- Graders, metrics, thresholds, and aggregation
- Blocking criteria
- Independence requirements
- Human-review triggers
- Evidence and environment profiles
- Budget and data classification
- Owner, approver, validity, integrity, and limitations

Blocking criteria remain separate from aggregate scores. Efficiency or stylistic quality never offsets a blocking correctness, safety, security, authority, or evidence failure.

## Evaluation cases and datasets

Cases must include applicable:

- Positive behavior
- Negative behavior
- Null selection
- Denial
- Escalation
- Failure and recovery
- Adversarial behavior

Every case must define allowed and prohibited inputs, expected and prohibited outcomes, mandatory path controls, grader bindings, risk tags, origin, data classification, solvability, ambiguity, contamination controls, integrity, and limitations.

Keep authoring, calibration, regression, held-out, adversarial, and incident partitions distinct. Hidden expected results remain unavailable to the evaluated target.

## Oracle preference

Use the strongest suitable oracle:

1. Authoritative state or externally observed effect
2. Deterministic schema, contract, policy, functional, property, or trace verifier
3. Controlled simulation or fault evaluator
4. Calibrated statistical measurement
5. Calibrated model judge for semantic or subjective criteria
6. Qualified human review for judgment, novelty, conflict, or consequence

Evaluate outcomes when several adaptive paths are valid. Evaluate paths only for mandatory controls. Hidden reasoning and stylistic similarity are prohibited correctness requirements.

## Model-judge boundary

A model judge may assess subjective quality, semantic coverage, groundedness, open-ended comparisons, and advisory instruction review.

A model judge is prohibited as the sole blocking oracle for:

- Identity, authority, approval, permission, or ownership
- Policy enforcement
- External side effects
- Evidence integrity
- Budget accounting
- Idempotency, fencing, transaction, or state-version correctness
- Security-critical code or executable assets
- Irreversible action completion
- SOAA conformance

Blocking use requires focused rubrics, structured output, calibration, bias and adversarial testing, validity limits, independence disclosure, an inconclusive result, and periodic human sampling.

## Human review and approval

Review and approval are separate:

- Domain, security, evidence, or conformance reviewers assess claims.
- An authorized approver commits a consequential authority or release decision.

Human review is required for profile-defined high-impact, irreversible, materially uncertain, novel, disputed, security-sensitive, appealable, or legally required decisions.

Reviewer identity, competency, independence, conflicts, evidence, counterevidence, rubric, outcome, rationale, limits, and time must enter a HumanReviewRecord.

## Evaluator independence

Declare independence across:

- Producer identity
- Model family
- Context
- Data and oracle
- Execution environment
- Organization
- Authority
- Conflict of interest

A producer self-check is advisory. The task owner never commits its own final gate.

## Non-deterministic evaluation

For stochastic behavior, declare:

- Trial count and sampling
- Seed and model configuration
- Reliability measure
- Confidence or credible interval method
- Minimum acceptable lower bound
- Tail and critical-failure treatment
- Multiple-comparison treatment
- Stopping rule

Use a reliability measure aligned with production behavior. A one-attempt production path must not claim reliability through a many-attempt best-of result.

## Completion evidence profiles

| Profile | Minimum evidence | Intended use |
|---|---|---|
| `EP0_OBSERVED` | Trace, outcome statement, sources, budget result, limitations | Advisory analysis |
| `EP1_VERIFIED` | EP0 plus an objective verifier for each required criterion and policy evidence | Routine reversible execution |
| `EP2_INDEPENDENT` | EP1 plus independent evaluation, negative checks, side-effect certainty, evidence review | Consequential execution |
| `EP3_HUMAN_GATED` | EP2 plus qualified human review and separate approval where required | Irreversible, high-impact, disputed, or policy-designated execution |

Task acceptance binds a profile before execution. Increased risk may preserve or strengthen the profile, never weaken it silently.

## Completion gate

Every completion follows:

```text
Observation
  -> EvidenceRecord
  -> EvidenceClaim
  -> GateDecision
  -> Task transition
```

Completion requires:

- Disposition for every acceptance criterion
- Required outcome verification
- Required mandatory-path verification
- Side-effect reconciliation
- Evidence sufficiency
- Blocking counterevidence resolution
- Evaluation Controller gate pass
- Task Controller transition from `VERIFYING` to `COMPLETED`

Failed or inconclusive gates route to revision, re-evaluation, review, suspension, cancellation, or failure under policy.

## Evidence rules

Evidence must be:

- Immutable and append-only
- Content-addressed
- Source, method, environment, time, and target linked
- Scoped to exact versions and operating conditions
- Data-minimized and access-controlled
- Retained under governing policy
- Linked to counterevidence
- Independent of private model reasoning

Evidence from a different skill, model, tool, policy, runtime, configuration, or environment requires explicit compatibility evidence.

Missing, stale, integrity-failed, conflicting, mis-scoped, or insufficient evidence blocks the claim.

## Gate semantics

Gate logic is deterministic even when one input comes from a model or human.

Supported outcomes are:

- `PASS`
- `FAIL`
- `INCONCLUSIVE`
- `ERROR`

One blocking failure makes the gate fail. `ERROR`, missing execution, stale evidence, or unmet independence never becomes pass through aggregation.

Weighted scoring applies only to non-blocking criteria with explicit weights and thresholds.

## Conformance boundary

SOAA conformance measures adherence to every applicable required invariant in a named profile. It does not certify general safety, business fitness, quality superiority, or absence of defects.

A claim must name:

- Exact target and version
- Profile and version
- Suite and adapter versions
- Environment and dependency versions
- Assessment mode
- Evidence package
- Validity period
- Limitations

Required assertion results have no waiver inside a claimed profile.

This GovKit extension is guidance. It does not supply the complete 206-assertion executable suite and must not be presented as a conformance certificate.

## Required verification

Tests must cover:

- Definition and target identity
- Dataset separation and contamination
- Positive, negative, null, denial, escalation, and failure cases
- Blocking criteria and aggregation
- Model-judge calibration and attack resistance
- Reviewer and approver authority separation
- Evaluator independence
- Stochastic reliability and uncertainty
- Exact evidence scope, integrity, freshness, and counterevidence
- False completion narratives
- Side-effect certainty
- Gate outcomes and task transitions

Every production failure must enter a reviewed regression case with data minimization and provenance.
