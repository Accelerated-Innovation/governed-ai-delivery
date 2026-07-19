# Skill Selection and Activation Contract

## Source alignment

| Field | Value |
|---|---|
| Primary decisions | SOAA-006, SOAA-008, SOAA-009 |
| Primary invariants | SOAA-INV-021 through SOAA-INV-024 and SOAA-INV-030 through SOAA-INV-037 |
| Source module | SOAA Packet 2 |

## Purpose

This contract separates semantic relevance from hard admission and separates proposed selection from active instruction binding.

## Required four-stage pipeline

Every dynamic skill selection follows:

1. Candidate retrieval
2. Deterministic admission
3. Agent ranking
4. Atomic activation

No stage inherits the authority or result of a prior stage implicitly.

## Stage 1: candidate retrieval

Retrieval returns possibly relevant catalog entries based on task intent and visible metadata.

Retrieval:

- May use lexical, semantic, hierarchical, or rule-based search.
- Must apply catalog visibility before returning a candidate.
- Must use discovery metadata only.
- Must record catalog snapshot and retrieval method.
- Grants no eligibility, trust, authority, selection, or activation.

Full skill instructions and executable assets remain unloaded.

## Stage 2: deterministic admission

Admission applies typed hard predicates to each candidate:

- Release lifecycle state
- Integrity and provenance
- Runtime and protocol compatibility
- Declared preconditions and exclusions
- Dependency resolution
- Conflict and composition policy
- Trust and risk policy
- Data-classification constraints
- Authority feasibility

Admission produces exactly one outcome:

| Outcome | Meaning |
|---|---|
| `INELIGIBLE` | A hard non-authority requirement failed, or no permitted authority route exists |
| `ELIGIBLE` | All hard requirements pass and required access is inside current effective authority |
| `APPROVAL_ROUTABLE` | Hard requirements pass and one permitted scoped approval route exists |

Semantic intent matching is prohibited inside the deterministic admission predicate.

Admission must emit structured reason codes for every failed or approval-routable condition.

## Stage 3: agent ranking

The agent ranks only `ELIGIBLE` and `APPROVAL_ROUTABLE` entries.

The ranking request and response must include:

- Accepted task identity and revision
- Candidate snapshot identity
- Candidate status
- Fit rationale
- Uncertainty
- Material alternatives
- Approval need
- Explicit null selection

Null selection is always present. Ambiguity, insufficient fit, or unresolved same-level conflict produces null selection or escalation.

The runtime must not silently substitute a different skill after ranking.

## Binding modes

| Mode | Selection source | Required controls |
|---|---|---|
| Dynamic | Agent ranks an admitted set | Retrieval, admission, ranking, authority, activation, lifecycle, context, evidence |
| Fixed workflow | An approved workflow names an exact release or compatible range | Resolution, admission, authority, activation, lifecycle, context, evidence |

Fixed workflow binding removes ranking for one node. It never bypasses admission or activation.

## Conflict and composition

Relationships among skills must be explicit:

- Depends on
- Conflicts with
- Excludes
- Replaces
- Precedes
- Follows
- Composes with

A multi-skill run requires a versioned CompositionPlan with exact nodes, data flow, dependencies, authority and budget allocation, conflict rules, joins, cancellation propagation, failure routes, and safe amendment points.

Hidden recursive activation and hidden dependencies are prohibited.

## Stage 4: atomic activation

Before commit, the Capability Controller must revalidate:

- Task identity, revision, owner, and owner epoch
- Selection and candidate snapshot
- Skill lifecycle state and package digest
- Integrity, provenance, trust, and compatibility
- Dependency lock
- Policy and authority context
- Approval validity
- Composition or fixed-workflow binding
- Evaluation and evidence profile
- Context and instruction references

One activation transaction commits:

- Exact release identity and digest
- Bound task and agent run
- Selection record
- Dependency lock
- Effective authority envelope
- Instruction binding
- Context snapshot reference
- Evaluation and evidence profile
- Activation state
- Activation evidence

Instructions become visible only after commit. A failed transaction leaves zero active state and zero active instructions.

## Activation lifecycle

Supported states are:

```text
SELECTED
APPROVAL_PENDING
ACTIVATING
ACTIVE
SUSPENDED
TERMINATING
SUCCEEDED
FAILED
STOPPED
ESCALATED
DENIED
STALE
ACTIVATION_FAILED
```

Only the Capability Controller commits activation transitions.

Material changes to task, owner, policy, authority, approval, catalog, lifecycle, dependency, workflow binding, context, or environment require revalidation. Stale inputs produce `STALE`, not best-effort activation.

## Fallback rules

Fallback may:

- Select null
- Select another independently admitted candidate
- Request clarification
- Route scoped approval
- Escalate

Fallback must not:

- Weaken policy
- Broaden authority
- Use a revoked or incompatible release
- Skip required evaluation
- Substitute an unranked skill silently
- Drop required evidence

## Required evidence

Preserve evidence for:

- Candidate retrieval, including null outcome
- Admission outcome and reason codes for every candidate
- Ranking proposal, uncertainty, alternatives, and null option
- Approval route and decision
- Revalidation snapshots
- Activation commit or failed transaction
- Instruction exposure point
- Exact release and dependency lock

## Verification

Tests must prove:

- A highly ranked ineligible skill never reaches ranking or activation.
- Admission uses typed hard predicates only.
- Ranking always contains null selection.
- Same-level conflict results in null or escalation.
- Fault injection at each commit boundary leaves no partial activation.
- Instructions remain hidden before commit.
- Stale inputs block commit.
- Fixed binding still passes admission, authority, and activation.
- Fallback preserves or narrows every control.
