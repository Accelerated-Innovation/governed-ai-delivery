# Skill-Oriented Agent Architecture Extension

## Purpose

The `skill-oriented-agent-architecture` extension guides coding agents building applications in which an accountable agent run selects and applies governed procedural skills.

It implements a GovKit guidance profile derived from the approved Skill-Oriented Agent Architecture v0.2 specification dated 2026-07-18.

The central boundary is:

> A skill supplies procedure. Trusted runtime components retain authority, state, side-effect control, evaluation, and completion.

## Intended use

Install this extension for an API or CLI application with one or more of these characteristics:

- Adaptive agent execution
- Dynamic or fixed skill binding
- Tool or executable-asset invocation
- Human approval before consequential action
- Multi-skill composition
- Agent delegation or task handoff
- Governed context or memory
- Agent and skill evaluation
- Skill release lifecycle management
- MCP or A2A interoperability

This extension governs the application being built. It is distinct from the Agent Skills packages used by Codex, Claude Code, or Copilot to guide software delivery.

## Agent Skills compatibility

The SOAA package profile preserves a standard root `SKILL.md` and places governance metadata in an additional `soaa/` directory permitted by the Agent Skills format. A generic Agent Skills client may ignore the SOAA files and process the standard skill, but it must not claim SOAA conformance. A SOAA-aware runtime validates both the Agent Skills format and the SOAA profile before admission.

See [`SKILL_CONTRACT.md`](docs/backend/architecture/SKILL_CONTRACT.md) for the normative flat metadata keys, two-stage validation rule, and `allowed-tools` authority boundary.

## Install

```bash
govkit extension add skill-oriented-agent-architecture --target .
```

The extension targets GovKit Level 5 backend API and CLI projects. Agent architecture is extension-owned; GovKit core supplies only the shared structural, security, testing, and observability-port contracts.

## Contract loading

Load `soaa_core` for every feature in scope. Load the remaining sets only when the feature touches their concerns.

| Contract set | Load when the feature touches |
|---|---|
| `soaa_core` | Agents, skills, task ownership, runtime state, orchestration |
| `soaa_selection_authority` | Catalogs, selection, activation, policy, permissions, approvals |
| `soaa_context_resilience` | Context, memory, resources, retries, recovery, budgets, telemetry |
| `soaa_assurance` | Evaluation, evidence, verification, completion, conformance |
| `soaa_ecosystem` | Releases, package integrity, versioning, MCP, A2A, portability |

This structure preserves progressive disclosure. A coding agent should not load every contract for every feature.

## Architecture documents

The extension ships these guidance contracts under `docs/backend/architecture/`:

- `SKILL_ORIENTED_AGENT_ARCHITECTURE.md`
- `SKILL_CONTRACT.md`
- `RUNTIME_STATE_AND_EXECUTION_CONTRACT.md`
- `SKILL_SELECTION_AND_ACTIVATION_CONTRACT.md`
- `AUTHORITY_AND_APPROVAL_CONTRACT.md`
- `CONTEXT_MEMORY_AND_RESOURCE_CONTRACT.md`
- `RESILIENCE_AND_RECOVERY_CONTRACT.md`
- `EVALUATION_EVIDENCE_AND_COMPLETION_CONTRACT.md`
- `SKILL_LIFECYCLE_AND_INTEROPERABILITY_CONTRACT.md`

Each document identifies its approved SOAA decision scope and invariant range.

## Relationship to LLM application governance

SOAA does not prescribe an LLM provider, model family, gateway product, evaluation product, observability product, or guardrail product. Those concerns also apply to LLM applications without skills and are owned by the separate `llm-application` extension.

Install both extensions when an SOAA-governed system invokes language models:

```bash
govkit extension add llm-application --target .
govkit extension add skill-oriented-agent-architecture --target .
```

The `llm-application` contracts govern the model-facing parts of the system. SOAA remains authoritative for task ownership, skill selection and activation, effective authority, side-effect control, recovery, evidence, and completion. SOAA can also govern a non-LLM runtime, so it does not declare the LLM extension as an unconditional dependency.

## Source authority and limits

This package is an implementation-guidance profile. It does not by itself establish SOAA conformance.

SOAA v0.2 conformance requires the approved normative modules, all 206 invariant-to-assertion identities, released schemas, fixtures, adapters, oracles, and a valid evidence package. The current SOAA source set records the conformance suite and reference runtime as future implementation work.

Where this guidance conflicts with a higher SOAA authority, use this precedence:

1. Approved invariant
2. Approved decision record
3. Applied midpoint amendment
4. SOAA v0.2 root cross-module rule
5. Most specific approved module contract
6. This GovKit guidance profile

An unresolved conflict blocks implementation and enters architecture review.
