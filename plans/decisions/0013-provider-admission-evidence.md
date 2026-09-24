# ADR 0013: Provider admission and canonical maintenance evidence

Status: accepted for implementation; live provider collection remains caller-owned.

## Context

Generated configuration alone cannot establish that CI executed or enforced a
control. PR execution also needs explicit event, checkout and accepted-intent
authority. I09 already supplies the canonical maintenance engine; I10b supplies
protected reusable entry points and pinned common-engine execution.

## Decision

Add optional accepted admission policy to version-1 settings/bindings while
preserving replay of existing settings. Normalize supported native GitHub/Azure PR
records into a small typed admission value. Before project execution, require
matching clean Git-visible source/policy snapshots, full base/policy SHAs and
accepted request bytes. Keep provider values in environment inputs, never shell
interpolation. Reuse the same conformance engine and additive required checks.

Use an explicit versioned provider-observation export contract, not ambient
credentials or network calls. Report configuration, runtime and enforcement
separately as canonical checks; reuse them through `assess_repository`. Preserve
null, freshness, identities and source limitations. Track fixed generated paths
in maintenance inventory even when Git ignores them. Collection does not
authenticate exported JSON or install external branch/reviewer controls. Imported
runtime/enforcement evidence is marked `unverified-artifact`; positive claims stay
unknown, while explicit negative observations remain actionable even when a
separate runtime report mismatches. A local consistency check cannot promote an
unauthenticated export to independently executed evidence.

Publish only a caller-selected new file outside inspected/trusted checkouts,
using no-follow directory handles and create-only atomic linking. Native artifact
upload is separate optional caller configuration. Optional release refresh uses
the existing accepted data-only source boundary. Candidate integration proposals
reuse protected operation comparison and grant no write authority.

## Consequences

Local fixtures can establish deterministic provider parity and fail-closed
behavior; they cannot demonstrate live organization policy enforcement. Native
API export collection, credentials and protected caller activation remain explicit
deployment responsibilities. Older templates remain runnable without admission
but cannot produce admitted enforcement through this collector. Scheduled/push
events, Windows publication and hostile concurrent filesystem writers remain
outside this increment's demonstrated support. See
[the provider guide](../../docs/PROVIDER_EVIDENCE.md) for exact inputs and limits.
