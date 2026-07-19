# Runtime State and Execution Contract

## Source alignment

| Field | Value |
|---|---|
| Primary decisions | SOAA-005, SOAA-010 through SOAA-013 |
| Primary invariants | SOAA-INV-001 through SOAA-INV-005 and SOAA-INV-038 through SOAA-INV-067 |
| Source modules | SOAA Packets 1 and 3 |

## Purpose

This contract governs accepted tasks, runtime ownership, skill activations, composition, external operations, delegation, handoff, and authoritative state.

## Task offer and acceptance

A requested task begins as a TaskOfferRecord. It has no runtime owner.

The offer must state:

- Accountable principal
- Intent and bounded outcome
- Proposed scope
- Acceptance criteria
- Consequence and data classifications
- Requested authority
- Requested deadline and budget
- Evidence obligations

Acceptance atomically creates a TaskRecord and assigns its first runtime owner. Rejection preserves the offer and reason without creating active task state.

## One-owner rule

Every active TaskRecord has exactly one runtime owner:

- `AGENT_RUN`
- `HUMAN`

Skills, models, tools, resources, workflows, policies, evaluators, AgentDefinitions, and protocol endpoints never own tasks.

Every ownership change increments `owner_epoch`. A mutating command must match:

- Task identity
- Task aggregate version
- Current owner identity
- Current owner epoch
- Current authority context

Former-owner commands are fenced after transfer.

## Task lifecycle

Supported states are:

```text
READY
RUNNING
WAITING_INPUT
WAITING_APPROVAL
WAITING_DEPENDENCY
HANDOFF_PENDING
HUMAN_CONTROLLED
SUSPENDED
VERIFYING
COMPLETED
FAILED
CANCELED
```

Only the Task Controller commits task transitions.

Required rules:

- Accepted work enters `READY` with one owner.
- Adaptive cycles occur inside `RUNNING`.
- External waits have durable dependency, input, or approval records.
- Human takeover requires quiescence and an atomic owner commit.
- Every completion claim enters `VERIFYING`.
- Only an Evaluation Controller pass permits `COMPLETED`.
- Terminal tasks reject mutation.
- Reopened work receives a new linked task identity.

## Task revision

A material change to goal, constraints, completion criteria, stop conditions, authority, or evidence creates a new immutable task revision.

Active plans, activations, delegations, context snapshots, approvals, and evaluations must revalidate against the new revision. Historical evidence remains linked to the revision in force at decision time.

## Authoritative aggregate ownership

| Aggregate | Authoritative writer |
|---|---|
| TaskOfferRecord and TaskRecord | Task Controller |
| AgentRunRecord | Task Controller and Agent Decision Runtime through trusted ports |
| SelectionRecord and SkillActivationRecord | Capability Controller |
| CompositionPlan and workflow instance | Workflow and Composition Controller |
| AuthorityContext and ApprovalRecord | Policy and Authority Controller |
| OperationRecord | Tool Gateway or Skill Asset Runner |
| DelegationRecord and handoff transaction | Delegation and Handoff Controller |
| ContextSnapshot | Context Controller |
| MemoryRecord | Memory Gateway |
| EvaluationRun and GateDecision | Evaluation Controller |
| SkillRelease and installation state | Skill Registry and Capability Controller |
| EvidenceRecord | Evidence Recorder |

A controller must not mutate another controller's aggregate directly. Cross-aggregate coordination uses committed commands and events with idempotent consumers.

## Skill-activation lifecycle

A SkillActivation binds one exact admitted release to one task and agent run.

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

Task and activation state remain independent:

- Skill success does not complete the task.
- Skill failure does not automatically fail the task.
- Skill escalation does not transfer ownership.
- Task cancellation drives every active activation toward termination.

## Adaptive decision loop

Every decision cycle records:

1. Observation received
2. Immutable context snapshot
3. Model request identity
4. Proposed next action
5. Trusted controller decision
6. Activation, operation, delegation, wait, or evaluation outcome
7. Budget update
8. Observation cursor

Private model reasoning is never required for restart, audit, evidence, or correctness.

## Composition

A multi-skill run requires a versioned CompositionPlan defining:

- Exact skill nodes and bindings
- Dependencies and data flow
- Authority and budget allocation
- Conflict and exclusion rules
- Shared state and concurrency control
- Cancellation propagation
- Join and aggregation semantics
- Failure routes
- Safe amendment points

Adaptive parallel branches become child tasks with distinct owners. Shared-state mutation requires a lease, fencing token, transaction, partition, or validated merge rule.

Plan amendments create new versions. A running node keeps the plan version under which it started unless a declared safe-point migration commits.

## Operation boundary

Every mutating external operation receives a durable OperationRecord before invocation.

Required fields include:

- Operation identity and idempotency key
- Task, owner epoch, activation, and plan identities
- Tool or asset interface and version
- Input digest
- Authority decision
- Side-effect class
- Attempt state
- Result certainty
- Reconciliation and compensation links
- Evidence reference

Unknown effect is a distinct result. It is never treated as assumed success or assumed failure.

## Subtask delegation

Subtask acceptance:

- Creates a distinct child TaskRecord.
- Assigns the receiver as child owner.
- Preserves parent ownership.
- Preserves the accountable principal.
- Derives child authority independently inside the parent boundary.
- Creates parent-child and remote-correlation evidence.

The parent may wait, continue independent work, or cancel under declared policy.

## Whole-task handoff

Handoff uses prepare and commit phases:

1. Receiver admission
2. Acceptance intent
3. Sender quiescence
4. Atomic owner commit
5. Owner-epoch increment
6. Receiver acknowledgment
7. Former-owner fencing

Failure before commit leaves sender ownership unchanged. Ambiguous commit blocks unfenced mutation and enters reconciliation.

Network location does not determine semantics. Every delegation envelope declares `SUBTASK` or `HANDOFF`.

## State and evidence commit

Every accepted consequential transition must commit its authoritative state and evidence:

- In one transaction, or
- Through one authoritative durable envelope with deterministic recovery

A log line written before a failed state commit is not authoritative evidence of the transition.

## Restart rule

Restart reconstructs work from:

- Task and owner records
- Agent-run record
- Activation records
- Composition plan
- Authority and approval records
- Context snapshot references
- Operation and delegation records
- Evaluation and gate records
- Budget envelope
- Evidence stream

Provider conversation state or private model reasoning must not be required.

## Prohibited patterns

- Accepted tasks without one owner
- Direct model writes to authoritative aggregates
- Task state stored only inside a prompt or conversation
- Skill state and task state collapsed into one status
- External side effects without a prior OperationRecord
- Hidden recursive activation
- Parallel adaptive branches sharing one owner
- Handoff without quiescence and fencing
- Task completion without `VERIFYING`
- Historical evidence overwritten after retry or recovery

## Verification

Tests must prove:

- Zero-owner and multi-owner states are rejected.
- Stale aggregate versions and owner epochs reject writes.
- Terminal aggregates reject mutation.
- State and evidence commit atomically or recover together.
- Skill and task lifecycles remain distinct.
- Only one concurrent adaptive proposal commits.
- Every side effect has a pre-invocation operation identity.
- Mutating command replay is idempotent.
- Subtask and handoff preserve their different ownership semantics.
- Handoff fault injection preserves or fences ownership at every boundary.
- Restart reconstructs active work without a provider transcript.
