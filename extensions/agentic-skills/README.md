# Agentic Skills Extension

## Purpose

The `agentic-skills` extension adds governed architecture guidance for applications that use AI agents, Agent Skill packages, background agent runs, tool/action boundaries, human approval workflows, and agent evaluation.

It layers on top of govkit core contracts and Level 5 GenAI operations contracts.

```text
Core govkit contracts
  -> Level 5 GenAI contracts
    -> agentic-skills extension contracts
      -> product-specific contracts
```

## How extensions live in a project

Extensions are **not installed by the govkit CLI**. They live in-place under the root-level `extensions/` folder of a consuming project, as a sibling of `docs/`, `governance/`, and `features/`:

```text
<project>/
├── docs/
├── governance/
├── features/
├── extensions/
│   └── agentic-skills/
│       ├── manifest.yaml
│       ├── README.md
│       ├── docs/
│       ├── governance/
│       └── schemas/
└── .govkit
```

Govkit discovers extensions by scanning `extensions/*/manifest.yaml` during `apply` (for visibility) and `validate` (for compliance). All artifact paths declared in `manifest.yaml` are resolved relative to the extension folder itself — nothing is copied out of `extensions/<id>/`.

## Intended Use

Use this extension when a system includes one or more of the following:

- Interactive agent coaches
- Background agents
- Agent Skill packages
- Agent-generated recommendations
- Human approval before external action
- Tool adapters or external-system writes
- Agent observability and evaluation requirements

## Contract Set

Architecture contracts live under `extensions/agentic-skills/docs/backend/architecture/`:

- `AGENT_RUNTIME_CONTRACT.md`
- `AGENT_SKILL_PACKAGE_CONTRACT.md`
- `TOOL_ACTION_BOUNDARY_CONTRACT.md`
- `HUMAN_APPROVAL_CONTRACT.md`
- `RECOMMENDATION_ACTION_CONTRACT.md`
- `BACKGROUND_AGENT_TRIGGER_CONTRACT.md`
- `AGENT_OBSERVABILITY_CONTRACT.md`
- `AGENT_EVALUATION_CONTRACT.md`
- `AGENT_SECURITY_BOUNDARY_CONTRACT.md`

## Governance Templates

Reusable templates live under `extensions/agentic-skills/governance/backend/templates/`:

- `agent_topology.md`
- `skill_contract.md`
- `tool_contract.md`
- `human_approval_matrix.md`
- `recommendation_policy.md`
- `background_trigger_policy.md`

## Schemas

- `schemas/extension-manifest.schema.json` — JSON Schema for `manifest.yaml`.
- `schemas/architecture-contract-set.schema.md` — documentation for the contract-set shape.
