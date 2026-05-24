

# Skill Family Manifest Contract

## Purpose

This contract governs the shape of a **skill family manifest** — the top-level descriptor that groups a set of related Agent Skill packages into an executable family. The canonical filename is `csp.yaml`, but the platform must accept the shape regardless of filename.

A family manifest is an **inbound** artifact. It is authored by skill authors outside the platform repo and loaded by the platform's Skill Registry at runtime.

## Architectural Rule

A skill family is the unit of *packaged workflow*. It declares the ordered set of phases that constitute a complete delivery, the skill package each phase invokes, and any shared resources the family depends on. The platform must validate every loaded family manifest against the schema referenced below before any phase of that family is allowed to execute.

## Required Fields

Every family manifest must declare:

- `family_id` — kebab-case identifier, pattern `^[a-z][a-z0-9-]*$`. Globally unique across all loaded families on a given platform instance.
- `version` — semver string (`MAJOR.MINOR.PATCH`).
- `name` — human-readable family name.
- `description` — one-paragraph summary of what the family delivers.
- `owner` — accountable team or individual identifier (email, GitHub handle, or org-internal id).
- `phases[]` — ordered list of phase declarations (see below). Must be non-empty.

## `phases[]` Shape

Each phase declaration must contain:

- `id` — kebab-case phase identifier, unique within the family.
- `order` — integer; phases execute in ascending order. Ties are not permitted; every phase must have a distinct `order` value.
- `skill_ref` — fully-qualified reference to the skill package this phase invokes, in the form `<skill_id>@<version>` or `<skill_id>@^<version>` for semver-compatible ranges.
- `depends_on[]` — array of phase `id`s that must reach `COMPLETED` before this phase becomes `READY`. May be empty for the first phase. Must not introduce cycles.

## Optional Fields

- `shared_skills[]` — array of `<skill_id>@<version>` references for skills callable across multiple phases (e.g. orchestration, QA, handoff packager). Skills listed here are loaded once per family run and available to every phase.
- `integrations[]` — declared integration adapter identifiers the family expects to be present. The platform must fail the family load if any declared integration is unavailable.
- `lifecycle_hooks` — object with optional `pre_load`, `post_load`, `pre_phase`, `post_phase` skill references. Hooks execute outside the phase state machine and must not mutate phase state directly.

## Versioning

- `version` is the family-manifest version, not any individual skill version. Increment on additions to `phases[]`, changes to dependency order, or change of any `skill_ref`.
- Published family versions are immutable. Deprecation is a separate flag managed by the Skill Registry (see `REGISTRY_CONTRACT.md`).

## Schema

The machine-validatable schema for this contract is:

```text
extensions/agentic-skills/schemas/csp-family-manifest.schema.json
```

The platform's family loader **must** validate every ingested manifest against this schema before any phase is scheduled. Validation failures halt the load and emit a structured audit event per `AGENT_OBSERVABILITY_CONTRACT.md`.

## Relationship to Other Contracts

- Each phase's `skill_ref` resolves to a skill package whose shape is governed by `AGENT_SKILL_PACKAGE_CONTRACT.md`.
- Phase execution order and state transitions are governed by `PHASE_STATE_MACHINE_CONTRACT.md`.
- Inter-phase data transfer is governed by `HANDOFF_CONTRACT.md`.
- Skill resolution at runtime goes through `REGISTRY_CONTRACT.md`.

## Prohibited Patterns

A family manifest must not:

- Inline skill prompts, schemas, or scripts. Inlining bypasses the Skill Registry's versioning and audit guarantees.
- Declare a phase with no `skill_ref`. "Empty" phases are not permitted; use lifecycle hooks for cross-cutting concerns.
- Reference a `skill_ref` whose version is not pinned (e.g. floating `latest` is forbidden). Use `@^<version>` for semver ranges or `@<version>` for exact pinning.
- Mutate `family_id` across versions. A different `family_id` is a different family.
