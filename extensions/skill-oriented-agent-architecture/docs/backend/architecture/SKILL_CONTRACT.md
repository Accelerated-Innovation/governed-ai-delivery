# Skill Contract

## Source alignment

| Field | Value |
|---|---|
| Primary decisions | SOAA-002, SOAA-004, SOAA-019 |
| Primary invariants | SOAA-INV-006 through SOAA-INV-020 and SOAA-INV-175 through SOAA-INV-182 |
| Source modules | SOAA Packets 1 and 6 |
| External format | [Agent Skills specification](https://agentskills.io/specification), accessed 2026-07-20 |

## Purpose

This contract defines a skill as a versioned procedural capability. A skill supplies reusable method and contract metadata to a bound agent run. It does not become an agent, workflow, permission grant, or state owner.

## Canonical semantic model

```text
Skill = (I, C, P, T, R, D, G, E)
```

| Element | Required meaning |
|---|---|
| `I` | Identity, version, provenance, and integrity |
| `C` | Applicability, exclusions, and preconditions |
| `P` | Procedure, heuristics, references, and examples |
| `T` | Success, failure, stop, and escalation conditions |
| `R` | Inputs, outputs, artifacts, and errors |
| `D` | Skill, tool, resource, runtime, and environment dependencies |
| `G` | Required authority, ceilings, approvals, and prohibited access |
| `E` | Evaluation, evidence, and conformance obligations |

Every production skill must declare all eight areas. An empty area remains explicit.

## Passive package rule

Discovery, retrieval, parsing, validation, installation, and activation must not execute package code or cause an external side effect.

Executable assets remain inert until:

1. The exact release passes admission.
2. Activation commits.
3. The agent run proposes a typed invocation.
4. The runtime recalculates authority.
5. The Skill Asset Runner authorizes and isolates execution.
6. The operation and outcome enter durable records.

## Primitive boundaries

| If the component primarily... | Classify it as... |
|---|---|
| Owns an adaptive goal and next-action loop | Agent run |
| Supplies reusable contextual procedure | Skill |
| Performs one typed bounded operation | Tool |
| Supplies facts or reference content | Resource |
| Enforces mandatory order or gates | Workflow |
| Measures a target against criteria | Evaluator |

One package may contain instructions, references, schemas, and executable assets. Packaging does not erase the responsibility boundary.

## SOAA profile for Agent Skills packages

A SOAA-aligned Agent Skills package uses two layers:

```text
skill-name/
├── SKILL.md
├── soaa/
│   ├── manifest.yaml
│   ├── evidence-profile.yaml
│   ├── compatibility.yaml
│   └── provenance.json
├── scripts/
├── references/
├── assets/
├── evals/
└── LICENSE.txt
```

`SKILL.md` preserves Agent Skills discovery metadata and procedural instructions. `soaa/manifest.yaml` holds the SOAA governance contract. The Agent Skills format permits additional files and directories, so `soaa/` and `evals/` extend the package without replacing or modifying the standard format.

The standard constraints for `SKILL.md` remain binding, including the parent-directory name match and the required `name` and `description` fields. SOAA metadata uses the standard `metadata` field, whose entries are string keys mapped to string values.

```yaml
---
name: skill-name
description: Performs the governed skill-name procedure. Use for tasks that require this procedure.
license: LICENSE.txt
metadata:
  soaa-profile: "soaa-agent-skills/0.2"
  soaa-manifest: "soaa/manifest.yaml"
  soaa-manifest-digest: "sha256:<64-lowercase-hex>"
  soaa-release-id: "<immutable-release-id>"
---
```

The four SOAA metadata keys are normative:

| Key | Required value |
|---|---|
| `soaa-profile` | Exact SOAA Agent Skills profile identifier and version |
| `soaa-manifest` | Skill-root-relative path to `soaa/manifest.yaml` with no parent traversal |
| `soaa-manifest-digest` | Digest of the exact manifest bytes using the declared algorithm |
| `soaa-release-id` | Immutable release identity matching the manifest |

All four values must be non-empty strings. Nested SOAA metadata is invalid because Agent Skills metadata values are strings, not mappings. The manifest digest and release identity must match before admission.

### Generic-client behavior

A generic Agent Skills client may ignore the `soaa/` directory and unrecognized `soaa-*` metadata. It may still process the package as Agent Skills-format conformant when `SKILL.md` passes standard validation. It must not claim SOAA package-profile or runtime conformance.

A SOAA-aware client must recognize the four metadata keys, validate the referenced manifest and package integrity, and enforce SOAA admission and activation rules before using governed capabilities.

### `allowed-tools` profile rule

The Agent Skills `allowed-tools` field remains an optional, space-separated string. Within SOAA it declares a requested maximum tool set, not an authority grant. A SOAA runtime calculates:

```text
effective_tools = allowed_tools
                  intersect runtime_policy
                  intersect task_authority
                  intersect approval_scope
```

An absent `allowed-tools` field never authorizes a tool. Runtime policy, task authority, approvals, and the admitted SOAA manifest remain controlling.

### Two-stage validation

Package admission requires both validation stages:

1. Agent Skills format validation using `skills-ref validate <skill-root>` or an equivalent conforming validator. This validates `SKILL.md` frontmatter, naming, and standard field constraints.
2. SOAA profile validation. This validates the manifest schema and digest, release identity, declared files, package digest, compatibility, provenance, evidence profile, executable-asset declarations, and mirrored-field consistency.

Passing stage 1 supports an Agent Skills-format conformance claim. Passing both stages supports a SOAA package-profile conformance claim. Neither result alone establishes runtime, activation, evaluation, or task-completion conformance.

## Source-of-truth split

| Concern | Authority |
|---|---|
| Standard name, description, license, compatibility, allowed-tools | `SKILL.md` frontmatter |
| Procedure | `SKILL.md` body and integrity-bound references |
| Identity, applicability, interface, authority needs, termination, dependencies, evaluation, evidence, provenance | `soaa/manifest.yaml` |
| Exact executable behavior | Integrity-bound asset plus runner contract |
| Current grant | Policy and Authority Controller |
| Current release state | Skill Registry |

Mirrored fields must match after normalization. A conflict fails package validation.

## Required manifest areas

The SOAA manifest must define:

- Profile and schema version
- Lineage ID, release ID, declared version, digest, and owner
- Triggers, exclusions, and preconditions
- Typed inputs, outputs, artifacts, and errors
- Required, optional, and prohibited access
- Approval points
- Success, failure, stop, and escalation conditions
- Skill, tool, resource, runtime, model, protocol, and environment dependencies
- Admission and regression evaluation suites
- Completion evidence profile
- Compatibility and provenance references
- Data classification and execution-isolation needs

Unknown critical fields fail validation. Unknown noncritical fields remain preserved and reported.

## Required release identity

```text
(skill_lineage_id, declared_version, package_digest, soaa_profile_version)
```

The runtime resolves version ranges before admission, then binds one exact digest and one resolved dependency lock during activation.

## Procedure and code boundary

Skill instructions may:

- Describe a method
- Offer heuristics and examples
- Identify information to inspect
- Propose tool or resource use
- State stop and escalation conditions
- Define expected artifacts and evidence

Skill instructions must not:

- Mutate authoritative state
- Issue credentials or permissions
- Bypass approval
- Execute package assets during loading
- Hide required dependencies
- Reclassify lower-precedence content as policy
- Declare the parent task complete
- Modify the released package in place

Permission checks, state transitions, transactions, idempotency, integration boundaries, budget enforcement, completion gates, revocation, and recovery belong in application code.

## Termination boundary

Skill termination and task completion are separate.

- Skill success reports a skill-level outcome.
- Skill failure reports a skill-level failure.
- Skill stop ends the activation under a declared condition.
- Skill escalation requests a different authority or controller.
- None of these outcomes changes task ownership.
- None completes the task without the task-level completion gate.

## Required evidence

Every activation must preserve:

- Skill lineage, declared version, digest, and profile version
- Selection source and admission result
- Bound task and agent run
- Authority envelope and approval references
- Instruction and context snapshot identities
- Dependency lock
- Asset invocations
- Termination outcome
- Evaluation and evidence profile

## Verification

Tests must prove:

- Loading produces no execution side effect.
- The schema contains no owner or grant field.
- Activation leaves task ownership and existing grants unchanged.
- Exact assets execute only through the runner.
- Package traversal, undeclared assets, digest mismatch, and conflicting mirrored fields fail admission.
- Skill success alone never commits task completion.
- `allowed-tools` never expands effective authority.
