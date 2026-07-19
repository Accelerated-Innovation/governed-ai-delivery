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

## Install

```bash
govkit extension add skill-oriented-agent-architecture --target .
```

The extension targets GovKit Level 5 backend API and CLI projects. Its manifest supersedes the generic core `AGENT_ARCHITECTURE.md` contract for the consuming project. Record the supersession in an ADR during architecture preflight.

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

SOAA does not prescribe an LLM provider, model family, gateway product, evaluation product, observability product, or guardrail product.

The present GovKit Level 5 baseline supplies:

- `LLM_GATEWAY_CONTRACT.md`
- `EVALUATION_LLM_CONTRACT.md`
- `OBSERVABILITY_LLM_CONTRACT.md`
- `GUARDRAILS_CONTRACT.md`

Those concerns apply to LLM applications without skills and belong in a separate `llm-application` extension. Until GovKit extracts that package, this extension declares relationships to the Level 5 core contracts without duplicating them.

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
