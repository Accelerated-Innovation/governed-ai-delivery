# Agent Evaluation Contract

## Purpose

This contract governs evaluation of agent behavior, structured outputs, tool use, recommendations, and safety boundaries.

## Architectural Rule

Agentic features must be evaluated before release and regression-tested after changes to prompts, skills, schemas, tools, or model routing.

## Evaluation Layers

Agentic evaluation should include:

- Schema validation
- Deterministic policy checks
- Tool/action boundary checks
- Role and permission checks
- Golden path examples
- Failure path examples
- LLM quality evaluation when generation is involved
- Regression tests for known issues

## Required Evaluation Dimensions

Recommended dimensions:

- Structured output validity
- Recommendation relevance
- Actionability
- Source traceability
- Policy compliance
- RBAC correctness
- No unauthorized external action
- Human approval compliance
- Groundedness
- Safety
- Latency and cost

## Eval Artifacts

Agentic features should define evaluation expectations in:

```text
eval_criteria.yaml
nfrs.md
architecture_preflight.md
```

Production skills should also include skill-level evals under:

```text
my-skill/evals/
```

## Structured Output Validation

Any output that drives application behavior must validate against a schema.

Invalid outputs must be rejected or sent to a repair flow. They must not be persisted as accepted business state.

## Tool Use Evaluation

Tests must verify:

- Allowed tools are callable only under the right conditions.
- Disallowed tools are not called.
- External writes require policy and approval.
- Tool failures produce safe failure states.

## Recommendation Evaluation

Recommendation-generating agents should be evaluated for:

- Correct interpretation of signals
- Clear rationale
- Appropriate priority
- Appropriate plan routing
- Correct visibility
- No duplicate noise
- Actionable next steps

## Human Approval Evaluation

Tests must verify:

- Approval is required for high-risk actions.
- Unauthorized roles cannot approve.
- Approval decisions are audited.
- Publishing does not occur before approval.

## Regression Requirement

When an agent failure or harmful output is discovered, add a regression case before or with the fix.

## Feature Preflight Requirements

Feature `architecture_preflight.md` must identify:

- Evaluation dimensions
- Required schemas
- Golden cases
- Failure cases
- Required regression coverage
- Release threshold

