# Resilience and Recovery Contract

## Source alignment

| Field | Value |
|---|---|
| Primary decision | SOAA-015 |
| Primary invariants | SOAA-INV-089 through SOAA-INV-102 |
| Source module | SOAA Packet 4 |

## Purpose

This contract makes retry, timeout, cancellation, reconciliation, compensation, restart, budget enforcement, and recovery trusted runtime responsibilities.

## Failure taxonomy

Every failure must receive one explicit class:

| Class | Meaning | Required route |
|---|---|---|
| Deterministic rejection | Contract, policy, state, or compatibility denial | Stop or request correction |
| Transient known-safe failure | No effect occurred and bounded retry is safe | Retry under one owner |
| Unknown-effect failure | Side-effect status is uncertain | Reconcile before retry |
| Permanent execution failure | Current conditions cannot satisfy the operation | Fail, compensate, or escalate |
| Security failure | Injection, compromise, exfiltration, or authority abuse signal | Contain, revoke, suspend, investigate |
| Evidence failure | Required evidence is missing, stale, conflicting, or invalid | Block the gate and escalate |

The model may propose a classification. A trusted controller commits it.

## Retry contract

Every retry chain must define:

- One retry owner
- Finite maximum attempts
- Deadline
- Backoff and jitter
- Retryable failure set
- Idempotency rule
- Effective total across nested libraries
- Cost, token, operation, and time budget
- Stop and escalation route

Unknown-effect operations are prohibited from retry until reconciliation establishes a safe status.

Retry creates a new attempt identity while preserving the original operation identity and evidence.

## Timeout contract

A timeout must distinguish:

- Model wait timeout
- Tool execution timeout
- Remote delegation timeout
- Human input or approval expiry
- Overall task deadline

A mutating operation timeout enters unknown-effect reconciliation unless authoritative status proves no effect.

Timeout never implies cancellation at the target and never implies operation failure without evidence.

## Cancellation and quiescence

Cancellation propagates to:

- Active skill activations
- Tool and asset operations
- Workflow nodes
- Child tasks
- Delegations and handoffs
- Model invocations
- Pending evaluations

Terminal cancellation commits only after work reaches quiescence or every uncertain operation is fenced and routed to reconciliation.

Partial completion records:

- Completed work
- Incomplete work
- Side effects
- Uncertainty
- Outstanding obligations
- Compensation eligibility
- Evidence

## Operation ledger

Every external or executable operation requires a durable ledger entry before invocation.

The ledger tracks:

- Operation and attempt identities
- Idempotency key
- Input digest
- Target and interface version
- Authority decision
- Invocation time
- Known status
- Result certainty
- External correlation
- Cancellation status
- Reconciliation state
- Compensation link
- Evidence

## Reconciliation

Reconciliation obtains authoritative operation status after timeout, disconnect, crash, or ambiguous response.

It must:

1. Fence duplicate mutation.
2. Query authoritative target state where available.
3. Compare target state with expected effect.
4. Classify success, no effect, partial effect, conflicting effect, or still unknown.
5. Commit evidence.
6. Route retry, compensation, manual review, suspension, or terminal result.

No uncertainty record may age past policy without a routed outcome.

## Compensation

Compensation is a new separately authorized operation. It:

- Receives its own operation identity.
- Recalculates authority.
- Preserves the original effect and evidence.
- Defines its own failure and reconciliation path.
- Never rewrites history as though the first operation did not occur.

## Checkpoint and resume

Checkpoint only durable observable state:

- Task, owner, and revisions
- Active plans and activations
- Authority and approvals
- Context references
- Operations and uncertainty
- Delegations
- Evaluation state
- Budgets
- Evidence cursor

Resume must revalidate:

- Owner and owner epoch
- Task revision
- Policy and authority
- Approval validity
- Skill release and revocation
- Dependency lock
- Context and memory sources
- Operation status
- Remaining budget
- Evaluation definitions
- Runtime and environment compatibility

Changed conditions block unsafe resume.

## Execution budget

Every accepted task has a finite BudgetEnvelope covering:

- Deadline and elapsed time
- Model tokens and invocations
- Tool and asset operations
- Retry attempts
- Monetary cost
- Context size
- Child tasks and delegation depth
- External data volume
- Evaluation work

Child reservations must not exceed unreserved parent balance.

Hard-limit exhaustion stops covered work and routes to:

- Completion with sufficient evidence
- Partial result
- Suspension
- Failure
- Escalation for a new authorized budget

Silent continuation and silent success are prohibited.

## Operational telemetry

Trace one execution chain across:

- Principal and task
- Owner epoch
- Agent run
- Skill selection and activation
- Context snapshot
- Model request
- Tool or asset operation
- Delegation or handoff
- Evaluation and gate
- State transition
- Evidence record

Required metrics include:

- Task and activation outcomes
- Selection null, denial, and escalation rates
- Retry and unknown-effect rates
- Reconciliation age
- Cancellation time to quiescence
- Budget use and exhaustion
- Evaluation failure and inconclusive rates
- Recovery and resume outcomes

Telemetry becomes evidence only when it meets evidence integrity, completeness, scope, access, and retention rules.

## Prohibited patterns

- Infinite or hidden retry
- Independent nested retry budgets
- Retry after unknown effect without reconciliation
- Timeout treated as confirmed failure
- Cancellation reported before quiescence
- Compensation hidden as rollback
- Resume from conversational summary alone
- Budget stored only in prompt instructions
- Recovery directed by a revoked skill release
- Logs treated as authoritative state without a reconstruction contract

## Verification

Tests must prove:

- Every injected failure receives one complete class.
- Nested retries obey one total limit and one owner.
- Unknown-effect replay creates no duplicate side effect.
- Timeout on mutation enters reconciliation.
- Cancellation accounts for every child and operation.
- Uncertainty routes before policy expiry.
- Session loss resumes from durable state.
- Changed owner, authority, release, policy, or environment blocks resume.
- Compensation has separate identity, authority, and evidence.
- Concurrent child reservations never over-allocate parent budget.
- Hard exhaustion produces no silent continuation.
- Telemetry preserves correlation without leaking prohibited data.
