# ADR 0008: preserve legacy configuration through explicit migration

Status: accepted for I08 implementation.

Migration is a separate operation from legacy upgrade, profile acceptance, request
routing and architecture change. The default command produces a proposal. An
explicit reviewed profile and matching preview digest authorize only the concrete
migration operations. Existing metadata without a valid migration receipt is
protected rather than assumed to belong to this operation.

The implementation composes the existing legacy adapter, bounded discovery,
profile writer, pack resolver/installer and read-only conformance protocol.
Profile/pack operations are first executed against an isolated copy. Only new,
verified outputs are materialized in the real target. The single-file legacy
marker can be relocated with its exact bytes/mode/time; modern markers, customized
contracts, native guidance, extensions, project artifacts and CI remain unchanged.
The receipt records provenance and permits ownership-checked rollback.

Legacy control requirements become always-applicable workflow obligations. This
keeps non-pack checks separate from `policy.required_checks`, whose I03 contract
requires selected executable-pack providers. Unknown legacy/custom/CI/authority
semantics remain explicitly required and unverified, not silently dropped. Neither
local shape validation nor installed gate files establish active enforcement.
Application completion reports real post-operation checks and remaining findings.

Snapshots, source/profile and pack digests bind previews to inspected inputs;
fresh recomputation precedes writes. Per-file replacement and caught-failure
rollback are supported. Filesystem transactions, crash recovery and authenticated
approval are not. Separate normal backups and quiescent writes remain necessary.

The existing 0.21.x compatibility line and first migration delivery keep all legacy
commands. Actual removal requires I13's separately announced release/warning
boundary. Canonical maintenance integration is I09, provider enforcement I10 and
self-hosting I12. See [the guide](../../docs/LEGACY_MIGRATION.md) for the exact bounds,
workflow, operations, rollback and executable fixture coverage.
