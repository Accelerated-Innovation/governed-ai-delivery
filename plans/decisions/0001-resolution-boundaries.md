# ADR 0001: Explicit requirements and an inward resolution boundary

Date: 2026-09-23.
Status: implementation decision for I01; subject to maintainer review.
Scope: GovKit's installer source, not an architecture policy installed into consumer repositories.
References: [implementation plan, I01](../declarative-governance-implementation-plan.md#i01--establish-the-resolution-foundation-143), [#143](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/143).

## Context

The existing manifest resolver combines level interpretation, merge/replace rules, type/stack dispatch, and ordered resource selection. Its consumers include apply, upgrade, stack changes, and doctor. Replacing its output or changing installation semantics would endanger managed blocks, user edits, directory accumulation, and legacy markers before the declarative model is ready.

New repository configuration and per-request requirements need separate inputs. They must support explicit capability combinations without interpreting a maturity level. Observing a repository, selecting a bundled resource, and accepting a policy are different acts. A resolver cannot infer the last from the first two.

## Decision

Introduce three inward modules and preserve the existing facade:

| Module | Owns | Dependencies |
|---|---|---|
| `cli/resolution_models.py` | Typed inputs, source authority, requirements, policy references, versioned plans | Standard library only |
| `cli/resolution.py` | Consistency checks and selection from explicit inputs | Models and standard library only |
| `cli/legacy_resolution.py` | Existing level/merge/replace/dispatch semantics; conversion to and from explicit requirements | Models and standard library only |
| `cli/manifest.py` | Manifest loading, existing prompts, `resolve_variant_files()` facade | Live `paths` module, adapter, resolver |
| Existing commands and installation services | CLI validation, observation, copying, edit protection, marker persistence | Shared/domain services; not each other's command modules |

No new command, marker field, installed file layout, or profile file is introduced. The facade calls the legacy adapter, resolves the explicit input, and restores the ordered `(files, shared, governed)` ABI. New callers use `resolve_repository()` and `resolve_request()` directly. The core does not import the compatibility adapter, command handlers, paths, filesystem, network, or process modules.

### Inputs and authority

- `RepositoryInput` contains configured capability requirements, resource/check contributions, selected integrations, accepted policy, observations, proposals, and explicit provenance. Missing agent/type/CI/stack facts remain `None`; resolution supplies no framework default.
- `RequestInput` identifies the request source and additional capability/artifact/check requirements. Resolving it does not mutate or reconfigure the repository. Unavailable capabilities produce setup decisions rather than downloads or installation.
- `SourceRef` records a reference and authority: observed, proposed, accepted, bundled, or legacy. `Reason` connects every selected requirement to its applicability explanation and source. References are not fetched by the core.
- `Observation` and `ProposedDecision` remain separate from `AcceptedPolicy` and `ContractRef`. Their constructors enforce the authority distinction. A requirement justified by observed/proposed authority is unresolved; selecting a bundled artifact does not turn its contents into accepted policy.
- Accepted authority is asserted by the trusted caller. These Python types do not authenticate an approver or make an editable document trustworthy. Later loaders and CI must establish approved sources outside the core and must not trust a producer's plan as authorization.
- `ArchitectureTransition` preserves its accepted source, component scope, retain/improve/migrate choice, current and target contracts, applicability to new/changed/all code, and scoped exceptions with explicit expiry. I01 transports this declaration; it does not activate a target elsewhere, waive checks, calculate expiry against an implicit clock, or perform application refactoring.

The minimum legacy capability vocabulary is `application-governance`, `gherkin-delivery`, and `llm-evaluation`. The last denotes the legacy LLM development/evaluation bundle, including its development guidance; it is not an assertion that evaluations ran. These are internal identifiers, not new onboarding flags or a completed pack contract.

### Resolution and output

`InstallationPlan` and `WorkflowPlan` are separate, versioned outputs. Both contain explicit capability, artifact, and check selections plus structured `UnresolvedDecision` records. An installation plan retains integration, policy, observation, proposal, and provenance context. A workflow plan binds its request to the installation plan's deterministic SHA-256 identity.

The core verifies missing declared capability dependencies, explicit capability conflicts, missing reasons, unaccepted requirement sources, and inconsistent declarations sharing an identifier. It returns all independent findings instead of printing or exiting after the first. Equivalent repeated declarations combine their reasons. Conflict candidates remain inspectable, but unresolved plans are not ready and cannot be converted by the legacy bridge into an install selection.

Request resolution retains repository checks, including those required by accepted policy. A request may add capability constraints; omitting a repository dependency cannot waive it. Conflicting request declarations leave an unresolved decision and preserve the mandatory repository declaration. Policy exceptions are descriptors here, not authority to remove checks.

`ready` means that these supplied requirements have no unresolved consistency findings. It does not mean that a check executed, that a repository conforms, that a human approved anything, or that overwriting a file is authorized. There are no execution-result states to misreport in I01.

`ArtifactRequirement` is a resource selection with source path, destination, ownership category, installer attributes, and reasons. It is not a concrete filesystem operation. Directory expansion, source existence, protected-file hashes, destination collisions after expansion, deferred feature resources, stack rule overrides, and actual writes remain in the existing installer. Operation previews bound to observed ownership belong to I02/I08. Different resource IDs may intentionally contribute to the same destination directory.

### Determinism and compatibility

- JSON uses schema version 1, sorted object keys, compact separators, and no implicit time, environment, repository reads, or network lookup. Non-finite JSON numbers are rejected. Ordered arrays retain explicit precedence; deterministic does not mean sorting away legacy semantics.
- Plans snapshot caller data. Mutating an input's nested installer attributes afterward does not mutate the returned plan. The digest identifies serialized inputs/results; it is not a signature or an authenticity guarantee.
- Legacy option iteration order is intentional. Base entries retain duplicates; cross-dimension files deduplicate by `(src, dest)` with the first entry's attributes preserved; shared/governed paths deduplicate by equality. L4 merge and L5 replace defaults, explicit modes, nested type/stack dispatch, and custom metadata remain unchanged.
- Legacy provenance includes the logical manifest reference, its content digest, effective options, their order, and effective level. Level interpretation stays in the adapter; the level-free core has no level field or bundle inference.
- Original manifests remain authoritative for legacy resource selection. The adapter's bundle translation records configured capabilities; it neither accepts project architecture nor infers executed checks from CI YAML files.
- Existing CLI validation still rejects unsupported combinations. The low-level facade retains its existing permissive behavior for unknown dimensions and options. Flat custom manifests remain on the separate existing apply path. I01 does not introduce stricter validation into those public compatibility paths.
- Ownership categories describe the existing contract and do not override hash/edit protection or authorize changes to user-authored content. The copying and marker code is unchanged.

## Later contracts and migration seams

The implementation plan's other concepts remain distinct; only real I01 inputs/outputs are implemented now:

| Increment | Next consumer / responsibility |
|---|---|
| I02 | Versioned runtime profile/resolution loaders, accepted-source validation, unknown/partial context, maintenance policy, and no-write materialization previews |
| I03 | Pack descriptors/locks, dependency graph and version compatibility, portable resources, minimal installation proposals |
| I04 | Check execution protocol and findings/evidence states, independent of requirement selection |
| I05 | Evidence-backed observations with observation identity/time and bounded discovery adapters |
| I06–I07 | Intent normalization, impact-based workflows, applicability, trusted actual-change checks, transition/exception enforcement, stale-plan detection |
| I08 | Installed-state inventory, ownership-aware operations, migration/rollback and post-change verification |
| I09–I11 | Release metadata/freshness and canonical maintenance assessment, gate contracts/renderers, reports |

Serialization is an internal versioned contract in I01. No loader or public on-disk schema is claimed until I02. The core's direct requirement checks are not the later pack graph algorithm, workflow chooser, conformance engine, or installed-state inventory.

## Verification

Before changing production code, freeze 258 supported agent/type/level/CI/stack selections from `bfa4f76` in `tests/fixtures/legacy-resolution-baseline.json`. Fingerprints cover every ordered entry and installer attribute; readable synthetic cases also protect duplicate/order semantics. The original unsupported-combination tests remain in force.

New tests specify independent capabilities, separate request/repository plans, mandatory-control retention, conflicting declarations, missing dependencies/provenance, authority separation, scoped transition preservation, canonical serialization, snapshot isolation, and execution with I/O/printing forbidden. An import-boundary test protects the core's inward dependency direction. Existing manifest, install, marker, and edit-protection tests must remain green. Record executed checks and limitations in the implementation plan rather than claiming runtime evidence from this ADR.

## Alternatives considered

Keeping level interpretation in the new core would make independent combinations depend on legacy bundles. Replacing the installer or manifest format in I01 would couple behavioral change to the compatibility extraction. Generating a complete policy/pack/execution framework before its consumers exist would create untested speculative abstractions. The adapter and explicit typed inputs allow each later increment to supply its own verified boundary.
