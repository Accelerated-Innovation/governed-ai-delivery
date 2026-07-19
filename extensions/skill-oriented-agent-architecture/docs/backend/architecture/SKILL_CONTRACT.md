# Skill Contract

## Source alignment

| Field | Value |
|---|---|
| Primary decisions | SOAA-002, SOAA-004, SOAA-019 |
| Primary invariants | SOAA-INV-006 through SOAA-INV-020 and SOAA-INV-175 through SOAA-INV-182 |
| Source modules | SOAA Packets 1 and 6 |

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

## Agent Skills package profile

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

`SKILL.md` preserves standard discovery metadata and procedural instructions. `soaa/manifest.yaml` holds the governance contract.

The `SKILL.md` metadata must link:

- SOAA profile identifier
- Relative manifest path
- Manifest digest
- Exact skill release identity

The standard `allowed-tools` field is a requested ceiling. It never grants runtime access.

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
