# Handoff Contract

## Purpose

This contract governs how data is transferred between phases of a skill family run. The Handoff Service is the platform component responsible for accepting a phase's outputs, validating them, persisting them, and making them available as inputs to the next phase.

A handoff payload is a **dual-faced** artifact: skill authors must produce payloads that conform to the schema (inbound shape), and the platform must route and persist them according to the rules below (runtime behavior).

## Architectural Rule

No phase may transition from `COMPLETED` to releasing control to its successor without a handoff payload that has been validated against the schema **and** durably persisted. The state machine's `READY` transition for any phase depends on the predecessor's handoff record existing in persistent storage.

## Required Fields

Every handoff payload must contain:

- `from_phase` — `id` of the phase emitting the handoff.
- `to_phase` — `id` of the phase that will consume it. May be `null` only for the final phase in a family run.
- `family_id` — the family this payload belongs to.
- `run_id` — unique identifier for the family run instance.
- `artifacts[]` — concrete outputs of the emitting phase (see below).
- `state` — accumulated state visible to downstream phases.
- `trace` — audit trail of what happened during the emitting phase.

## `artifacts[]` Shape

Each artifact entry must declare:

- `type` — artifact category (e.g. `recommendation`, `decision_record`, `evidence_bundle`, `action_plan`). Free-form string; the consuming phase's skill is responsible for understanding the type.
- `schema_ref` — reference to the schema the artifact's content conforms to, in the form `<schema_id>@<version>`. Resolved through the Schema Registry per `REGISTRY_CONTRACT.md`.
- `content_ref` — pointer to the persisted content. Either a URI (`s3://...`, `https://...`) or a content-addressed hash (`sha256:...`). Inline content is not permitted in handoff payloads; persist first, reference second.

## `state` Shape

The `state` object aggregates downstream-relevant data:

- `phase_outputs` — map of `<phase_id>` → output summary for every completed phase in the run.
- `accumulated_context` — map of stable context keys (e.g. tenant, engagement, role) that persist across the whole run. Skills must not mutate `accumulated_context` after the family run has begun; the platform is the sole writer.

## `trace` Shape

The `trace` object captures the audit record of the emitting phase:

- `events[]` — ordered list of `{timestamp, event_type, detail}` entries, including at minimum the phase's `RUNNING → COMPLETED` transition.
- `decisions[]` — agent decisions made during the phase, each with `{decision_id, rationale, alternatives_considered}`.
- `approvals_taken[]` — approvals collected during the phase per `HUMAN_APPROVAL_CONTRACT.md`, each with `{approval_id, approver, granted_at, scope}`.

## Routing Rules (Runtime)

The Handoff Service must, in order:

1. **Validate** the payload against the schema (see Schema section below). On failure, halt the run with a `HANDOFF_INVALID` audit event and do not advance the state machine.
2. **Persist** the payload to durable storage *before* signaling the state machine. A handoff that has not been persisted does not exist.
3. **Emit** a `HANDOFF_PERSISTED` audit event per `AGENT_OBSERVABILITY_CONTRACT.md`, including `from_phase`, `to_phase`, `run_id`, and the persisted record's content-addressable identifier.
4. **Signal** the Phase State Machine that the predecessor is `COMPLETED` and the successor (if any) becomes `READY`.

If steps 1 or 2 fail, the platform must roll back any partial side effects of step 3 or 4 and place the run in a `FAILED` terminal state. Re-running requires explicit operator action.

## Schema

The machine-validatable schema for this contract is:

```text
extensions/agentic-skills/schemas/handoff-payload.schema.json
```

The Handoff Service **must** validate every payload against this schema; validation is the gate, not a courtesy check.

## Relationship to Other Contracts

- Phase state transitions triggered by handoff persistence are governed by `PHASE_STATE_MACHINE_CONTRACT.md`.
- `schema_ref` resolution is governed by `REGISTRY_CONTRACT.md` (Schema Registry).
- Approvals listed in `trace.approvals_taken[]` must originate from records satisfying `HUMAN_APPROVAL_CONTRACT.md`.
- Audit events emitted at every step satisfy `AGENT_OBSERVABILITY_CONTRACT.md`.

## Prohibited Patterns

A handoff payload must not:

- Embed artifact content inline. Persist first; reference second.
- Reference a `schema_ref` that does not exist in the Schema Registry at the time of handoff.
- Omit `trace.events[]`. A handoff with no audit trail is non-conformant regardless of its other fields.
- Mutate `state.accumulated_context`. Skills may read; only the platform may write.
- Use a `content_ref` that resolves to mutable storage. Handoff content is immutable once persisted; revisions require a new artifact entry with a new `content_ref`.
