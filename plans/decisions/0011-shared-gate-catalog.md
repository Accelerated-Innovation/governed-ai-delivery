# ADR 0011: Shared gate declarations and legacy CI selection

Status: accepted for I10a, 2026-09-24.

Split I10 into two deliveries without dropping any acceptance criterion. I10a
establishes a shared contract/catalog and legacy compatibility boundary; I10b
renders and safely materializes executable provider integrations and contributes
configuration/runtime facts to maintenance. Catalog compatibility can be reviewed
independently of executable workflow trust, credentials and external enforcement.

`GateSpec` describes a logical control within the shared conformance invocation.
It records additive requirements, accepted policy sources, selectors/scopes,
blocking/advisory intent, dependencies, trigger/filter intent, command contract,
permission/secret/configuration needs and expected evidence. The common entry point
is always repository-wide and has no path filters. Other gates reference that
single invocation rather than creating duplicate runs.

Explicit profiles and local pack resolution compose these declarations without
maturity-level selection. Repository obligations cannot be weakened by a pack or
workflow contribution. Conditional requirements are preserved as conditions;
catalog `blocking` is a summary, not request applicability. The runtime common
engine remains responsible for trusted profile/lock validation, reviewed intent,
actual Git scope, additive requirements, execution opt-in and evidence. It can add
checks absent from the static catalog. Neither catalog contents nor authored
workflow labels are executable allowlists or authorization to omit checks.

Unknown capability composition produces explicit decisions; catalog readiness is
not runnable/enforced CI. Records always distinguish `not-run` execution and
`unknown` enforcement. Exact composition pins and digests establish reproducible
input declarations, not publisher/provider authenticity. Unmeasured provider
permissions/secrets remain null. Record validation rejects conflicting IDs/pins,
invalid scopes, changed blocking policy, missing dependencies and cycles without
recursive graph traversal.

The identical CI dimensions in the three bundled agent manifests move to one
bounded `governance/ci/legacy-selection.json`. An explicit named reference expands
at the manifest I/O boundary before the existing pure adapter. Custom inline CI
tables retain precedence by using their existing format; mixed inline/reference
input is invalid. There is no arbitrary file/URL lookup. Existing templates and
all 258 frozen ordered selections remain unchanged, including legacy quirks.
New-mode gate selection does not interpret the legacy table's maturity levels.

The first CLI surface is read-only `govkit pipeline catalog`. The wheel must ship
the shared table, schema and example, and runtime pilots must cover all agents,
both providers, independent capability combinations and unresolved input. I10b
retains all renderer, protected generation, drift/evidence, maintenance and trust
requirements in #147 and the implementation plan.
