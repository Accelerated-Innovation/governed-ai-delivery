# Skill Lifecycle and Interoperability Contract

## Source alignment

| Field | Value |
|---|---|
| Primary decisions | SOAA-018 through SOAA-020 |
| Primary invariants | SOAA-INV-147 through SOAA-INV-206 |
| Source module | SOAA Packet 6 |
| External format | [Agent Skills specification](https://agentskills.io/specification), accessed 2026-07-20 |

## Purpose

This contract governs immutable skill releases, promotion, deprecation, retirement, revocation, compatibility, supply-chain integrity, Agent Skills packaging, MCP and A2A mappings, and portability.

## Separate identities

Keep these identities distinct:

- Skill definition or lineage
- Immutable skill release
- Environment-specific installation
- Task-specific activation

No mutable `latest` directory or version label identifies exact executable behavior.

## Release lifecycle

Supported release states are:

```text
CANDIDATE
ADMITTED
REJECTED
DEPRECATED
RETIRED
REVOKED
```

Legal transitions:

- `CANDIDATE -> ADMITTED` after admission and release gates pass
- `CANDIDATE -> REJECTED` after failure or withdrawal
- `ADMITTED -> DEPRECATED` with an approved migration plan
- `ADMITTED -> REVOKED` after a revocation directive
- `DEPRECATED -> RETIRED` after the support deadline
- `DEPRECATED -> REVOKED` after a revocation directive
- `RETIRED -> REVOKED` after a later compromise finding

Only admitted releases enter new selection or activation.

## Release identity and immutability

```text
(skill_lineage_id, declared_version, package_digest, soaa_profile_version)
```

- Declared versions use Semantic Versioning syntax.
- Exact bytes define the package digest.
- Published release bytes are immutable.
- Changed executable assets always create a new digest and impacted-area regression run.
- A version class is a governed claim supported by change-impact evidence.
- Activation binds the exact digest after range resolution.

## Compatibility and dependency lock

Compatibility must address:

- SOAA and Agent Skills profile
- Runtime capabilities
- Model profile
- Tool and resource interfaces
- Skill dependencies
- MCP, A2A, and extension versions
- Platform and language runtime
- Policy schemas
- Data contracts
- Supported degradation modes

Resolve floating ranges before admission and activation. Bind one deterministic dependency lock containing exact skill releases, tool interfaces, resource contracts, protocol versions, runtime version, model profile, policy digest, and evaluation reference.

Missing required compatibility rejects binding or enters one predeclared safe degraded mode.

Silent fallback is prohibited when it drops a control, changes authority or ownership, weakens completion evidence, changes side-effect class, loses required data, or uses an untested profile.

## Change impact, migration, and rollback

Every release change must record:

- Predecessor and proposed release identities
- Changed files and semantics
- Version class
- Affected dependencies, authority, data, evaluations, and protocols
- Migration and rollback support
- Reviewer, approval, and evidence

A live activation migrates only at a declared safe point with:

- Exact source and target releases
- State-transform contract
- Fresh authority and compatibility checks
- New context and instruction snapshot
- Target admission status
- Migration evaluation
- Atomic binding change and evidence
- Recovery route

Rollback binds another exact admitted release. It never rewrites history or reuses a prior digest with different bytes.

## Revocation

Revocation blocks:

- New selection
- New activation
- Resume
- Retry
- Recovery directed by the revoked release
- Asset execution
- Covered operation authorization

Active work follows one committed policy:

- Cancel now
- Suspend and quarantine
- Stop before next operation
- Compensation only

In-flight mutation is canceled where safe or fenced and reconciled. Outputs after the compromise boundary remain quarantined until cleared.

Cached descriptors must include lifecycle epoch, fetch time, expiry, and integrity. Operation beyond the allowed revocation-staleness limit fails closed.

## Learning and drift

Execution evidence, incidents, feedback, or model proposals enter a governed draft process. Released packages are never mutated in place.

Revalidation triggers include changes to:

- Model or configuration
- Runtime or orchestration
- System or developer instructions
- Policy
- Tool schema, behavior, endpoint, or permission
- Resource contract or trust
- Dependent skill
- Protocol or adapter
- Operating system or language runtime
- Threat intelligence or legal constraint
- Observed task distribution or outcome quality

Revalidation results in pass, constrained operation, deprecation, disablement, revocation, or suspension for insufficient evidence.

## SOAA profile for Agent Skills packages

The SOAA package profile uses:

- `SKILL.md` for standard discovery and procedure
- `soaa/manifest.yaml` for governance semantics
- Flat string metadata keys `soaa-profile`, `soaa-manifest`, `soaa-manifest-digest`, and `soaa-release-id`

The Agent Skills format permits additional files and directories. A generic client may ignore `soaa/` and remain Agent Skills-format compatible, but it must not claim SOAA conformance. A SOAA-aware client must first validate the standard `SKILL.md`, then validate the SOAA manifest, digest, release identity, declared package contents, compatibility, provenance, and evidence profile.

`allowed-tools` is a requested ceiling, not a grant. Effective tool access is the intersection of that ceiling, runtime policy, task authority, and approval scope. Absence of the field never authorizes a tool.

Package integrity covers instructions, manifest, profile files, scripts, assets, references, evaluations, schemas, migrations, license, and provenance. Parent traversal, symbolic-link escape, undeclared executable assets, and digest mismatch fail admission.

## MCP mapping

SOAA v0.2 maps MCP specification revision `2025-11-25`.

| MCP primitive | SOAA interpretation |
|---|---|
| Resource | Resource candidate through Resource Gateway |
| Resource template | Parameterized resource descriptor |
| Prompt | Prompt-template resource under precedence rules |
| Tool | Descriptor and operation through Tool Gateway |
| Roots | Context-boundary advertisement, never a grant |
| Sampling | Model request through Model Gateway |
| Elicitation | Structured human-input request, never approval by itself |
| Protocol task | Remote operation handle, never local TaskRecord by default |
| Logging and progress | Untrusted observation events until validated |

MCP names, descriptions, annotations, prompts, and server instructions are external claims. Wire compatibility never grants SOAA authority.

## A2A mapping

SOAA v0.2 maps A2A protocol version `1.0`.

| A2A primitive | SOAA interpretation |
|---|---|
| Agent Card | Remote agent descriptor |
| AgentSkill | Advertised remote capability, not internal SkillDefinition |
| Message | Task offer or task-interaction input |
| Task | Remote protocol lifecycle object, not local TaskRecord by default |
| Artifact | Untrusted data until validated |
| Authentication-required state | Authentication need, not approval |

Remote completion remains a proposal until local verification.

SOAA remote delegation declares `SUBTASK` or `HANDOFF`. Whole-task handoff requires prepare, quiescence, atomic owner commit, fencing, reconciliation, and evidence across failure boundaries.

## Protocol version policy

Every protocol adapter pins:

- Protocol version
- Negotiated extensions
- Semantic mapping profile
- Adapter version
- Compatibility evidence
- Downgrade policy

A protocol upgrade or downgrade triggers change-impact and behavior-preservation evaluation. Missing semantics reject the connection or route one predeclared degraded mode.

## Portability claims

Keep separate:

- Package portability
- Runtime semantic portability
- Protocol interoperability

A runtime portability claim requires at least two independently implemented runtime profiles and evidence preserving:

- Outcomes
- Authority
- Side effects
- Ownership
- Interfaces
- Failure behavior
- Completion
- Evidence

Syntax conversion or package loading alone does not prove behavioral equivalence.

## Supply-chain controls

Review:

- Names and discovery metadata
- Natural-language procedure
- Executable assets
- References and templates
- Tool and resource declarations
- Evaluation definitions and graders
- Dependencies and build process
- Provenance, signatures, package inventory, and license

Digest validity, signer trust, provenance acceptance, and release admission remain separate decisions.

## Prohibited patterns

- Mutable released packages
- Activation by version label without digest
- Silent compatible-range fallback
- New operations after revocation
- Offline use past lifecycle staleness limits
- MCP or A2A descriptors treated as grants
- Remote completion accepted as local completion
- A2A AgentSkill treated as internal procedural skill without mapping
- Authentication or elicitation treated as approval
- Protocol downgrade without semantic checks
- Portability claimed from file-format compatibility alone

## Verification

Tests must prove:

- Lifecycle transitions reject every illegal edge.
- Exact release bytes remain immutable.
- Candidate, rejected, retired, and revoked releases fail new activation as applicable.
- Revocation reaches selection, activation, resume, retry, recovery, assets, and operations.
- Cached stale lifecycle state fails closed.
- Dependency resolution is deterministic and locked.
- Migration commits atomically or preserves the source binding.
- Rollback never binds a revoked or incompatible release.
- Package traversal, undeclared assets, and digest mismatch fail.
- MCP and A2A injection cannot change policy, authority, ownership, or completion.
- Remote subtask and handoff preserve different ownership semantics.
- Upgrade and downgrade tests detect semantic loss.
- Cross-runtime differential tests support any portability claim.
