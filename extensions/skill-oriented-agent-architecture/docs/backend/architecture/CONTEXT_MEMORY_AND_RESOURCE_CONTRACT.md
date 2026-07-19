# Context, Memory, and Resource Contract

## Source alignment

| Field | Value |
|---|---|
| Primary decision | SOAA-014 |
| Primary invariants | SOAA-INV-068 through SOAA-INV-088 |
| Source module | SOAA Packet 4 |

## Purpose

This contract treats context as an immutable, authorized projection of durable sources. Long context is not authoritative memory. Retrieval rank is not truth, permission, or instruction precedence.

## Context source classes

Every context item must retain a source class:

- System or platform policy
- Organization or application policy
- Accepted task contract
- Workflow or architecture constraint
- Active skill instruction
- Current task interaction
- Tool observation
- Resource
- Memory
- Remote protocol content
- Derived summary

Trust metadata describes origin, integrity, validation, scope, and freshness. It never declares universal truth.

## Immutable ContextSnapshot

Every model invocation binds one immutable ContextSnapshot containing:

- Snapshot identity and digest
- Task identity and revision
- Owner identity and epoch
- Authority-context identity
- Active skill releases and activation identities
- Composition-plan version
- Policy and instruction-profile versions
- Resource and memory references
- Source classes and precedence
- Token, data, privacy, and cost budgets
- Data classifications and tenant scope
- Creation time and expiry

A change to any controlling identity makes the snapshot stale. Stale snapshots reject model invocation and operation proposals.

## Assembly pipeline

The Context Controller must:

1. Load the accepted task and control references.
2. Apply authorization and tenant filters.
3. Reserve protected budget for policy, task, authority, and output schema.
4. Retrieve only relevant discovery metadata.
5. Load active skill instructions after activation commit.
6. Retrieve supporting resources or assets on demand.
7. Apply classification, redaction, minimization, and precedence labels.
8. Validate budget and integrity.
9. Commit the immutable snapshot.

Context assembly performs no external mutation and grants no authority.

## Progressive disclosure

Skill content loads in three stages:

1. Discovery metadata
2. Activated procedural instructions
3. Supporting references and assets on demand

Full instructions remain unavailable before activation. Executable assets never run during disclosure.

## Context budgets

Budgets must cover:

- Total tokens or bytes
- Protected control allocation
- Skill instructions
- Resources and memory
- Tool observations
- Output reservation
- Sensitive-data allowance

Minimization must prefer:

- Structured records over broad dumps
- Relevant excerpts over full documents
- References over duplicated content
- Current authoritative state over conversational summaries
- Explicit omission over silent truncation

Position inside a long prompt must not determine enforcement. Critical controls require deterministic enforcement outside context.

## Compaction

Compaction creates a derived summary. It must preserve:

- Task and owner identities
- Current task revision and state
- Active skill releases
- Authority, approval, and policy references
- Plan and dependency state
- Outstanding operations and uncertainty
- Budget state
- Completion criteria and evidence obligations
- Source lineage
- Material omissions and information loss
- Compaction method, validator, and digest

Original records and evidence remain unchanged.

Rehydration reloads authoritative sources, verifies the compacted summary, and creates a new ContextSnapshot. Summary text alone never reconstructs authoritative state.

## Resource contract

Every ResourceDescriptor must state:

- Source and owner
- Trust and validation status
- Scope and authorized audience
- Data classification
- Freshness and expiry
- Integrity identity
- Transformation lineage
- Instruction classification
- Limitations

Resource content remains data. A document, website, MCP resource, A2A artifact, tool output, or retrieved prompt fragment cannot grant permission or override instructions.

## Memory types

Supported memory types include:

- Working
- Episodic
- Semantic
- Procedural reference
- Preference
- Operational

Every MemoryRecord must contain:

- Type and scope
- Source and provenance
- Trust and validation state
- Tenant and task boundaries
- Data classification
- Authorized readers and writers
- Purpose and retention
- Supersession relation
- Integrity identity
- Created, refreshed, and expiry times

## Memory read and write

The Memory Gateway owns controlled reads and writes.

Memory reads require:

- Current task purpose
- Authorized scope
- Type compatibility
- Freshness
- Tenant isolation
- Data minimization

Memory writes require:

- Typed record
- Provenance
- Validation
- Classification
- Retention
- Authorized writer
- Promotion state

Model output proposes a memory write. It never commits one directly.

Memory must not mutate:

- Task or ownership
- Skill release or activation
- Workflow or policy
- Authority or approval
- Evidence records

## Poisoning and isolation controls

The runtime must protect against:

- Cross-tenant retrieval
- Prompt injection in resources or memory
- Model-generated self-promotion
- Untrusted content marked as policy
- Stale or superseded memory
- Hidden executable content
- Summary corruption
- Excessive retention

Quarantined or unvalidated content receives no instruction role and no write access.

## Required evidence

Record:

- Snapshot identity and source inventory
- Authorization and filtering decisions
- Disclosure stage
- Classification and redaction actions
- Budget allocation and omissions
- Resource and memory provenance
- Compaction lineage and loss disclosure
- Staleness rejection
- Memory write proposal and commit decision

## Verification

Tests must prove:

- Any controlling revision invalidates the snapshot.
- Restart succeeds without provider transcript state.
- Injection cannot elevate resource or memory content.
- Retrieval rank changes do not change authority or precedence.
- Full skill instructions remain hidden before activation.
- Context limits preserve protected control fields.
- Repeated compaction leaves original sources intact.
- Corrupted summaries recover from authoritative sources.
- Cross-tenant and over-broad memory reads fail.
- Direct model memory writes create no record.
- Memory cannot mutate task, policy, authority, skill, or evidence aggregates.
