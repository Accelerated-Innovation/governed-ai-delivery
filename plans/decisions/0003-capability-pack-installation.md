# ADR 0003: Capability pack composition and portable installation

Status: implementation decision for I03, subject to maintainer review.
Date: 2026-09-23.
Issue: [#145](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/145).
Predecessor: [ADR 0002](0002-profile-materialization.md).

## Decision

Extend existing extension manifests with a strict, optional `capability_pack` v1 contract. Adapt legacy declarations at the loading boundary; keep legacy levels as provenance only. Use the existing bundled/local distribution, supported agent layouts, and a new dedicated `govkit pack` command. Runtime `packaging` evaluates versions/specifiers; no registry infrastructure or network lookup is introduced.

| Module | Responsibility |
|---|---|
| `schema_validation.py` | Strict local YAML/JSON and bundled schema validation, shared with profiles |
| `pack_models.py` | Typed immutable content snapshots, dependencies/contributions, graph output |
| `pack_loading.py` | Explicit-source reads, bounded resource closure, legacy normalization and content digests |
| `pack_resolution.py` | Pure deterministic selection, constraint backtracking, conflicts/cycles and required-control checks |
| `pack_store.py` | Read-only operation previews, pinned resource/native-skill ownership, protected apply, replay verification and explicit check invocation |
| `cmd_pack.py` | Public registrar, flags, reporting and exit status |
| `fs.stage_bytes` | Atomic staging shared by profile and pack materialization |

Preserve accepted profile ownership. Add optional exact source/version/digest pins to both the profile and embedded resolution schema. A pin constrains selection without enabling a pack. Different providers/sources require explicit selection; one provider can choose its highest compatible version, backtracking for shared constraints.

Store declared resource closures under `.govkit/packs/<id>/<digest>`, alongside a canonical replayable lock. Replay derives destination ownership from pinned manifests and accepted profile data instead of trusting arbitrary paths in a lock. Native copies come from one neutral skill source; references are portable and frontmatter remains identical. Examples/defaults remain advisory. Pack removal may delete only unedited owned files; accepted mandatory checks still require a provider.

Expose standalone Python check entry points independent of skills. Preview/apply do not execute them. The exact-match LLM example deliberately evaluates supplied results only; evidence origin/freshness and a general check protocol are I04, and version inventory/candidates remain I09. Keep #145 open through that later acceptance.

## Limits

Pins and replay establish consistency, not authenticity. Explicit source selection authorizes later explicit execution of trusted code; invocation is not a sandbox. Files are individually atomic and caught write failures roll back, but there is no concurrent-writer transaction or crash journal. Modified pinned resources require restoration/reconciliation, not silent repair. Existing third-party pack content is preserved. Legacy document references retain their original layout semantics and are not automatically accepted as architecture on the new path.
