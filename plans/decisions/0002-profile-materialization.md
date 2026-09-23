# ADR 0002: Declarative profile validation and metadata materialization

Status: implementation decision for I02, subject to maintainer review.
Date: 2026-09-23.
Issue: [#144](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/144).
Predecessor: [ADR 0001](0001-resolution-boundaries.md).

## Decision

Expose `govkit profile preview` and `govkit profile apply` as an explicit configuration path. Apply saves desired configuration and a replayable resolution record only. Pack installation belongs to I03 and legacy migration to I08; profile metadata must not falsely represent either as completed. Existing flag-only `apply` and `upgrade` remain unchanged and do not discover/adopt profiles implicitly.

Use `.govkit/profile.yaml` for project-owned desired configuration and `.govkit/resolution.json` for generated, versioned resolution metadata. The legacy marker remains separate and unchanged. A consumer need not have a legacy marker or choose a framework to preview/materialize a profile. The target directory must already exist.

| Module | Responsibility |
|---|---|
| `profiles.py` | Strict YAML/JSON loading, bundled runtime schema validation, typed profile/workflow/maintenance inputs, profile-to-core adapter, canonical record serialization and replay |
| `profile_store.py` | Bounded read-only metadata previews, content-bound apply, ownership checks, atomic replacements and caught-failure rollback |
| `cmd_profile.py` | Dedicated registrar, arguments, readable/JSON reporting and exit status |
| I01 models/resolver | Existing pure explicit-requirement consistency checking; no profile loading, filesystem work or command dependencies |

Promote `jsonschema` from a test-only dependency to a runtime dependency (`>=4,<5`). Use the same Draft 2020-12 schemas for runtime rejection and example validation instead of maintaining a second handwritten structural validator. Schemas are bundled under the existing `governance/` wheel mapping and found via live `paths.GOVERNANCE_DIR`. All references are local `$defs`; validation does not retrieve remote schemas. The resolution schema embeds the profile definition to remain standalone; a parity test prevents drift between the shared definitions.

The public contract rejects unknown versions/fields, aliases, duplicate keys/IDs, non-JSON YAML values, and invalid accepted authority. A profile may contain unknown or custom repository characteristics. Capabilities can explicitly name required context; missing unrelated context remains non-blocking. Mandatory capability/check policy cannot be silently erased by selection, and required checks remain in the underlying repository input consumed by request resolution.

Accepted source references record project assertions and are not fetched or copied. They are not an authentication mechanism. Desired configuration excludes observations and proposals; separately supplied typed context is retained in generated resolution output without acquiring policy authority. A target document remains scoped and separate from current constraints. Identical scope declarations with incompatible transitions are unresolved; full selector-overlap/exception enforcement remains a conformance responsibility.

Workflow rules declare permission, named conditions and additional requirements. I02 does not infer request impact, select a workflow, invoke checks, evaluate expressions, or use exceptions to remove controls. Permitted workflows may name capabilities requiring a later setup decision. Maintenance declarations record approved sources/channels, constraints/pins, age limits and explicit refresh permission. Neither refresh permission nor an age limit performs a lookup. Every I02 record reports release metadata as not queried; actual freshness, version comparison and urgency remain later assessment responsibilities.

Resolution records include the validated desired profile, its canonical digest, CLI version, full I01 plan, explicit unknowns, and lookup status. The loader replays the embedded profile/context to reject internally inconsistent or tampered selections. This is consistency checking, not trust: callers must bind the record to independently accepted current policy. No wall clock, absolute profile path, random identity or environment lookup enters the resolved plan. CLI version is explicit producing-tool provenance.

## Materialization and ownership

Preview reads only the provided input and the two fixed metadata destinations. Its operations are `create`, `preserve`, `update`, or `protected`, with current/proposed digests. It does not install capabilities or read an entire repository. Conflicting explicit integration flags and all level flags fail rather than silently changing accepted policy.

An existing equivalent profile is preserved byte for byte. A different profile is protected; the author must reconcile/edit it directly, then preview again. A canonical generated record may be refreshed after runtime validation and replay. Unrelated, malformed, or hand-edited metadata is protected, with no force override. Legacy markers, installed assets, user documents and locks are outside the write set. Invalid/unresolved configuration blocks materialization before creating `.govkit/`.

Apply accepts an in-memory preview and recomputes it from current inputs. Serialized operations never become arbitrary write instructions. Changed source/destination bytes and metadata symlinks are rejected. Writes are staged before replacements; replacements are atomic per file and caught failures restore completed operations. A no-op apply preserves mtimes. This is not a transaction against concurrent writers or a process/power-loss recovery journal. Later broader installation plans need their own ownership/concurrency contract rather than treating this two-file writer as a generic installer.

## Verification

Tests preceded production modules and failed collection because the modules did not exist. Follow-up tests reproduced acceptance of credential-bearing metadata URLs and contradictory same-scope transitions before fixes. Tests exercise real parsing/resolution/storage and the actual CLI dispatcher, including unknown fields/versions, unsupported authority, invalid metadata policy, tampered records, no-write preview, stale source/destinations, protected files, symlinks, idempotency, marker preservation and injected write failure rollback.

All illustrative profiles and paired resolution records must runtime-validate and replay. Run legacy/core/installer compatibility checks, the fast suite, and a real wheel with only runtime dependencies in a clean venv. Actual results and limits belong in the implementation plan's I02 execution record.
