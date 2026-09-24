# ADR 0009: Maintenance facts before consolidated advice

Status: accepted for I09a, 2026-09-24.

The running CLI, a legacy version marker, desired profile, lock and actual resource
bytes can disagree. Comparing one version string cannot establish repository health.
Release availability also needs independent approved-source, compatibility and
freshness facts before an update can be proposed.

`release_metadata.py` validates the versioned source document, compares known releases
against accepted constraints and the current environment, and exposes an explicit
anonymous metadata-only HTTPS refresh. The CLI alone writes a named cache outside
the target. Static metadata files can travel through existing distribution channels;
no code fetch, package installation, credentials or repository export is introduced.

`maintenance_inventory.py` observes bounded metadata/resources and reuses existing
Git identity and profile/lock replay. It keeps partial facts when a local integration
is absent. Invalid supplied release documents are rejected; failed provider lookups
are explicit records. Declared lock ownership remains unverified until replay succeeds.
Digest matching never establishes control execution or remote enforcement.

Candidate previews recompute inventory identity and compose existing protected pack
previews from explicit local candidate content plus the other locked packs. Current
component dependencies are checked; an implicit coordinated upgrade is not invented.
Pack/runtime/policy conflicts still block the actual preview. A CLI update is a
separate developer-environment operation. No serialized maintenance action is executed.

I09 is split into reviewable deliveries: I09a supplies #145 version/resource facts,
release candidates and previews; I09b composes those with #178 discovery and available
CI/conformance evidence for #146's four-dimensional assessment, then integrates #149
migration proposals and post-operation verification. I09 and #146 remain incomplete
until that composition is demonstrated. I10 retains provider-specific CI contracts.

Source records and digests are local consistency evidence, not authenticated publisher
claims or approvals. Missing/stale metadata does not prove freshness. Bounded snapshots,
legacy resources without locks, ignored files and concurrent writers retain explicit
coverage limitations. See docs/MAINTENANCE_INVENTORY.md for the command contract.
