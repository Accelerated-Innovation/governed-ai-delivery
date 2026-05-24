# Registry Contract

## Purpose

This contract governs the three registries the platform runtime maintains to resolve external artifacts at runtime:

- **Skill Registry** — resolves `<skill_id>@<version>` from family manifests and phase declarations into loaded skill packages.
- **Schema Registry** — resolves `<schema_id>@<version>` referenced in handoff payloads, skill output schemas, and approval requests.
- **Prompt Registry** — resolves prompt module identifiers referenced by loaded skills.

It is a **runtime** contract — it describes platform behavior, not the shape of any ingested payload.

## Architectural Rule

Every external artifact a skill family run depends on (skills, schemas, prompts) must be resolved through one of the three registries. Direct file-system access, inline embedding, or runtime fetch from an unvalidated source is prohibited.

## Required Operations

All three registries must implement the following operations with identical semantics. Storage backends may vary; the contract is the API.

| Operation | Behavior |
|---|---|
| `register(id, version, content, metadata)` | Persists a new version of an artifact. Idempotent on `(id, version)` — re-registration with identical content is a no-op; re-registration with different content is rejected. |
| `lookup_by_id_version(id, version)` | Returns the artifact content and metadata, or raises `NotRegistered`. Resolves both exact pins (`@1.2.3`) and semver-compatible ranges (`@^1.2.0`) — the latter returns the latest registered version satisfying the range. |
| `list(prefix=None)` | Returns a paginated stream of `(id, version, metadata)` tuples. Optionally filtered by `id` prefix. |
| `latest_compatible_version(id, range)` | Returns the highest registered version matching a semver range, or raises `NotRegistered`. Used by phase loaders before invoking `lookup_by_id_version`. |

## Namespacing

- **Skill Registry** keys: `<family_id>.<skill_id>` for family-scoped skills, `<skill_id>` for shared/cross-family skills. The optional `family_ref` field in `skill.json` (see `AGENT_SKILL_PACKAGE_CONTRACT.md`) determines which namespace a skill registers under.
- **Schema Registry** keys: `<schema_id>` — flat namespace. Schemas are intentionally shareable across families to enable interop.
- **Prompt Registry** keys: `<prompt_id>` — flat namespace. Prompts are versioned independently of the skills that consume them; one prompt version can be referenced by many skill versions.

## Versioning Semantics

- All registry entries use semver (`MAJOR.MINOR.PATCH`).
- **Published versions are immutable.** Once `register(id, v, content)` returns successfully, that `(id, v)` pair must never resolve to different content.
- Deprecation is a separate metadata flag (`deprecated: true | false`). Deprecation does **not** remove the entry; `lookup_by_id_version` continues to resolve deprecated versions. Callers may filter on the flag.
- Hard deletion is an out-of-band administrative operation; the contract does not define it. Any deletion must emit an audit event per `AGENT_OBSERVABILITY_CONTRACT.md` and must invalidate caches across all platform instances.

## Cache Semantics

Registries may cache resolution results. Caches must:

- Invalidate the entry for `(id, v)` immediately upon any `register` or deletion targeting that key.
- Invalidate the entry for `(id, range)` upon any `register` of a new version that could satisfy the range.
- Bound cache lifetime by a configurable TTL even in the absence of invalidation signals. Default: 300 seconds.
- Emit a `CACHE_INVALIDATED` audit event when a non-TTL invalidation occurs.

## Authorization

- **Registration** (`register`) is restricted to the platform-owner role. The platform's IAM layer (per `AGENT_SECURITY_BOUNDARY_CONTRACT.md`) is the enforcement point.
- **Lookup** (`lookup_by_id_version`, `list`, `latest_compatible_version`) is open to platform runtime services. Skills themselves do not call registries directly; the runtime resolves their references on their behalf.
- Authorization decisions must be auditable; every `register` and every denied `lookup` emits an event.

## Audit Events

The following events must be emitted per `AGENT_OBSERVABILITY_CONTRACT.md`:

- `REGISTERED` — successful `register` (includes `id`, `version`, `metadata`, `actor`).
- `REGISTRATION_REJECTED` — content-mismatch or authorization failure on `register`.
- `RESOLVED` — successful `lookup_by_id_version` (sampled; not every read must emit, but the platform must support full audit on demand).
- `RESOLUTION_FAILED` — `NotRegistered` raised; halt condition for the calling phase per `PHASE_STATE_MACHINE_CONTRACT.md`.
- `CACHE_INVALIDATED` — non-TTL cache eviction.

## Relationship to Other Contracts

- Skill resolution failures are halt conditions per `PHASE_STATE_MACHINE_CONTRACT.md`.
- Handoff payload `schema_ref` resolution goes through the Schema Registry (see `HANDOFF_CONTRACT.md`).
- Family-manifest `phases[].skill_ref` resolution goes through the Skill Registry (see `SKILL_FAMILY_MANIFEST_CONTRACT.md`).
- Authorization enforcement: `AGENT_SECURITY_BOUNDARY_CONTRACT.md`.
- Audit emission: `AGENT_OBSERVABILITY_CONTRACT.md`.

## Prohibited Patterns

A registry implementation must not:

- Mutate the content of a published version. Versions are immutable.
- Silently drop registrations on conflict. Conflicts emit `REGISTRATION_REJECTED`.
- Return stale cached content after a `register` for the same key has been observed.
- Permit skills to call registry operations directly. Resolution is the runtime's job.
- Resolve floating identifiers (`@latest`, unpinned references). All callers must supply either an exact version or a semver range; the registry is responsible for selecting the latest compatible version, not for guessing intent.
