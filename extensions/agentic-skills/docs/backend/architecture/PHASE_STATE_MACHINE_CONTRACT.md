# Phase State Machine Contract

## Purpose

This contract governs how the platform's Phase State Machine sequences, transitions, retries, and terminates phases of a skill family run. It is a **runtime** contract — it describes what the platform's code must do, not the shape of any inbound payload.

## Architectural Rule

Every phase in a family run is owned by the Phase State Machine. No phase may start, retry, halt, or complete except through a state transition emitted by the state machine. Skills must not self-advance, self-retry, or self-terminate.

## States

A phase occupies exactly one of the following states at any time:

| State | Meaning |
|---|---|
| `PENDING` | Declared in the family manifest; preconditions not yet met. |
| `READY` | All `depends_on` predecessors are `COMPLETED`; awaiting a runtime slot. |
| `RUNNING` | The skill is executing. |
| `AWAITING_APPROVAL` | Execution paused; a human approval is required per `HUMAN_APPROVAL_CONTRACT.md`. |
| `COMPLETED` | Skill executed successfully and its handoff payload was persisted per `HANDOFF_CONTRACT.md`. |
| `FAILED` | Terminal failure after retry exhaustion or unrecoverable halt condition. |
| `SKIPPED` | Marked as not applicable for this run (e.g. by a `pre_phase` lifecycle hook). Terminal. |

## Valid Transitions

| From | To | Trigger |
|---|---|---|
| `PENDING` | `READY` | All `depends_on` predecessors reached `COMPLETED` |
| `PENDING` | `SKIPPED` | A `pre_phase` lifecycle hook marked the phase non-applicable |
| `READY` | `RUNNING` | Runtime slot acquired; skill invocation begins |
| `RUNNING` | `AWAITING_APPROVAL` | Skill emitted an approval request per `HUMAN_APPROVAL_CONTRACT.md` |
| `AWAITING_APPROVAL` | `RUNNING` | Approval granted; execution resumes |
| `AWAITING_APPROVAL` | `FAILED` | Approval rejected; halt condition (see below) |
| `RUNNING` | `COMPLETED` | Skill returned successfully **and** handoff payload was validated **and** persisted |
| `RUNNING` | `FAILED` | Halt condition met (see below) **and** retry policy exhausted |
| `RUNNING` | `READY` | Recoverable error; retry policy permits another attempt |

All other transitions are prohibited. The state machine must reject an attempted illegal transition with a `STATE_TRANSITION_REJECTED` audit event and leave the phase in its prior state.

## Retry Policy

Retry policy is declared at one of two levels:

- **Family-level default** — declared in the family manifest under an optional `retry_policy` block: `{ max_attempts, backoff_seconds, retryable_failures[] }`.
- **Skill-level override** — a skill's `skill.json` may declare its own `retry_policy` that overrides the family default for that phase only.

If neither is declared, the platform default is `max_attempts: 1` (no retry).

The `retryable_failures[]` list enumerates error categories considered transient (e.g. `network_timeout`, `tool_unavailable`). All other errors are terminal on first occurrence regardless of `max_attempts`.

## Halt Conditions

The following force an immediate `FAILED` transition with no retry, even if the retry budget is unused:

- **Missing required artifact** — a `depends_on` predecessor's handoff payload omits an `artifact.type` this phase requires.
- **Handoff schema validation failure** — payload validation against `handoff-payload.schema.json` fails per `HANDOFF_CONTRACT.md`.
- **Approval rejected** — `AWAITING_APPROVAL` resolved with a rejection per `HUMAN_APPROVAL_CONTRACT.md`.
- **Skill registry resolution failure** — `phases[].skill_ref` cannot be resolved to a registered skill at the version requested per `REGISTRY_CONTRACT.md`.
- **Security boundary violation** — the skill attempted an action outside `disallowed_actions` or its declared `tool_permissions` per `AGENT_SECURITY_BOUNDARY_CONTRACT.md`.

## Audit Events

Every state transition **must** emit an audit event per `AGENT_OBSERVABILITY_CONTRACT.md`. At minimum each event carries:

- `run_id`, `family_id`, `phase_id`
- `from_state`, `to_state`
- `timestamp` (ISO-8601, UTC)
- `transition_cause` (one of: `dependencies_satisfied`, `slot_acquired`, `approval_requested`, `approval_granted`, `approval_rejected`, `skill_completed`, `retryable_failure`, `terminal_failure`, `halt_condition_met`, `skipped_by_hook`)
- `attempt_number` (1-based; resets per phase, not per run)

Audit events must be emitted **before** the state change is durably committed; replay must be deterministic from the audit stream alone.

## Terminal States and Run Completion

A run reaches a terminal state when every phase is `COMPLETED`, `SKIPPED`, or `FAILED`. The run as a whole is:

- `RUN_COMPLETED` if every phase is `COMPLETED` or `SKIPPED`.
- `RUN_FAILED` if any phase is `FAILED`.

Re-running a `RUN_FAILED` run is not permitted automatically; explicit operator action (with a new `run_id`) is required.

## Relationship to Other Contracts

- Phase advancement gating: `HANDOFF_CONTRACT.md` (persistence-before-transition rule).
- Skill resolution: `REGISTRY_CONTRACT.md`.
- Approval pauses: `HUMAN_APPROVAL_CONTRACT.md`.
- Audit emission: `AGENT_OBSERVABILITY_CONTRACT.md`.
- Halt conditions on boundary violations: `AGENT_SECURITY_BOUNDARY_CONTRACT.md`.

## Prohibited Patterns

The state machine implementation must not:

- Permit a skill to mutate phase state directly.
- Advance a phase to `COMPLETED` without a persisted handoff record.
- Retry on non-retryable failure categories regardless of `max_attempts`.
- Suppress or batch audit events. Every transition is one event, emitted synchronously.
- Allow a `FAILED` or `SKIPPED` phase to be reanimated within the same `run_id`.
