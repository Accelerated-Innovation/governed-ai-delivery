# ADR 0015: Separate change posture snapshots

Status: accepted for I11b implementation, 2026-09-24.

## Context

I07 change results embed replayable workflow decisions and independent control
outcomes. I11a exports maintenance snapshots. Their identities differ: changes use
request-plan resolution and a base-specific tree, while maintenance uses
installation resolution and inventory observations. Joining on repository identity
alone would imply execution/freshness coverage neither source establishes.

## Decision

Add pure `posture_change.py` and `govkit posture change` with a separate strict
`change-posture` v1 contract. Reuse I07 replay, I04 aggregation, shared privacy
descriptors and protected artifact publication. Preserve the maintenance contract.

Retain configured declarations, selected obligations, capability requirements,
accepted transitions/exceptions, and every recorded control/finding/action with
explicit state/execution. Replace private prose/paths/identifiers with references
and private-source JSON Pointers. Preserve canonical error-as-unknown behavior;
reject missing/weakened planned controls and contradictory repository identity.
Public check labels identify names, not authenticated semantic/provider proofs.

Default to stdout. Publication requires a caller-selected protected `--target`
with `--output`: the source has no filesystem root, and it must not be inferred
from the source file's location or repository ID. Human/JSON views use the same
projected findings/actions. Successful export is independent of gate success.

## Consequences and sequencing

Reports retain unauthenticated-snapshot origin and unsupplied maintenance,
discovery and provider-enforcement coverage. No checks run during projection.
Shared descriptor schemas have parity tests; a bundled example and seven installed
change pilots cover actual passes/failures, unknown approvals and publication.

Keep I11b's snapshot contract independently reviewable. I11c follows with fleet
aggregation/denominators, complete maintenance examples and the voluntary adoption
protocol previously grouped into I11b. No #148 criterion is waived; I11 stays in
progress. #147 still needs protected-caller/path-coverage deployment evidence;
source self-hosting remains I12.
