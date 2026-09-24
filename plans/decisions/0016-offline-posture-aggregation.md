# ADR 0016: Aggregate explicitly selected posture snapshots offline

Status: accepted for I11c implementation.
Date: 2026-09-24.
Source: implementation plan I11 / issue #148; follows ADRs 0014–0015.

## Decision

`govkit posture aggregate` takes an explicit cohort of pseudonymous repository
references, an explicit timezone-aware reporting time and a positive integer age
window. Each repository may supply one maintenance export and one change export.
Missing exports remain in repository denominators. Identical duplicates have no
effect; conflicting snapshots of the same kind/repository are rejected so the
caller must select a snapshot. Input order never chooses the winner.

The aggregate embeds only validated privacy-filtered exports, together with
sorted cohort references, observation ages and deterministic counts. Its replay
parser revalidates the embedded schemas and canonical source parsers and recomputes
all observations/counts. Embedded schema parity tests prevent contract divergence.
No raw assessment/request input is accepted. Digests establish consistency, not
publisher authenticity or completeness of a caller-chosen cohort.

Maintenance and change coverage/capabilities have separate denominators. A
maintenance pass measures assessment dimensions; it cannot supply a missing
project-control or evaluation result. Repository reference equality does not join
their profile/tree/request identities. Full source identities stay in the embedded
snapshots. The command describes a selected snapshot cohort, not a time series or
all changes made by a team.

Counts of canonical actions can overlap. Version/pin compatibility and required
upgrade decisions come from the supplied canonical projection. Reporting adds
only counts and observation age: stale, future and undated snapshots never supply
fresh-pass numerators. Canonical stale/unknown release metadata cannot become fresh
under a larger reporting window. Counts of configured or recorded capabilities
are not evidence of execution or enforcement. No overall healthy/compliant score
or adoption/productivity metric is calculated.

The command uses stdout and performs no publication, repository inspection,
provider execution, collection or transmission. A caller may explicitly select its
output for local storage or a protected CI artifact workflow. Existing per-repository
export publication remains unchanged.

## Consequences

An explicit roster makes missing coverage visible but cannot prove that the roster
is representative. Rejecting conflicts requires deliberate selection before each
run; a central collector and automatic newest-record selection are outside scope.
Embedding inputs makes the artifact larger but allows offline replay and preserves
facts needed to interpret each count. Canonical JSON is deterministic for identical
selected exports, cohort, reporting time and age window.

Synthetic maintenance scenarios and a distinct voluntary team pilot protocol
complete the reporting deliverables. The protocol is not an executed pilot and
supplies no evidence of productivity or live provider enforcement.
