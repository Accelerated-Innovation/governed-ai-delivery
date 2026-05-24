# Agent Skill Package Contract

## Purpose

This contract governs how agent capabilities are packaged, versioned, reviewed, and executed using the Agent Skills pattern.

## Architectural Rule

An Agent Skill package is the unit of agent capability. It must contain human-readable instructions, machine-readable metadata, references, schemas, prompts, deterministic scripts, assets, evaluations, and optional trigger definitions.

## Standard Structure

Agent Skill packages should follow this structure:

```text
my-skill/
├── SKILL.md
├── skill.json
├── references/
├── prompts/
├── schemas/
├── scripts/
├── assets/
├── evals/
└── triggers/
```

## `SKILL.md`

`SKILL.md` is the human-readable operating manual for the skill.

It must define:

- Purpose
- When to use the skill
- When not to use the skill
- Required inputs
- Allowed outputs
- Workflow
- Guardrails
- Approval requirements
- Failure behavior
- Examples

## `skill.json`

`skill.json` is the machine-readable contract for the skill.

It should define:

- Skill ID
- Name
- Version
- Supported modes
- Required context
- Allowed actions
- Disallowed actions
- Tool permissions
- External integrations
- Output schemas
- Approval policy
- Evaluation policy
- Trigger support

## References

The `references/` folder contains read-only knowledge used by the agent.

Examples:

- Architecture notes
- Methodology documents
- Metric glossary
- Role policy
- Source traceability
- Decision rules

References must be versioned or traceable. The skill must not depend on undocumented knowledge that cannot be audited.

## Prompts

The `prompts/` folder contains reusable prompt modules.

Prompt modules should be specific and testable. They must not contain hidden policy overrides or permissions that conflict with `skill.json` or architecture contracts.

## Schemas

The `schemas/` folder contains structured output contracts.

Agent outputs that drive application behavior must validate against schemas before they are persisted or acted upon.

Examples:

- Recommendation schema
- Action item schema
- Change proposal schema
- Tool request schema
- Approval request schema

## Scripts

The `scripts/` folder contains deterministic tools.

Use scripts for repeatable logic such as:

- Parsing packages
- Validating links
- Ranking recommendations
- Mapping actions to plans
- Comparing versions
- Generating structured proposals

Scripts must enforce input validation and must not silently perform external writes unless the tool/action boundary contract allows it.

## Evals

The `evals/` folder contains regression and quality checks.

Every production skill should include evals for:

- Output schema validity
- Policy compliance
- Role/permission correctness
- Tool-use boundaries
- Source traceability
- Representative success cases
- Representative failure cases

## Triggers

The `triggers/` folder defines background execution triggers when supported.

Triggers must declare:

- Schedule or event condition
- Required context
- Deduping rule
- Throttling rule
- Output type
- Visibility policy

## Versioning

Skill versions must be durable and auditable.

Agent runs must record:

- Skill ID
- Skill version
- Prompt/template version when available
- Model or routing profile
- Tool versions when material

## Prohibited Patterns

Skill packages must not:

- Hide production permissions in prompt text.
- Bypass application authorization.
- Contain unreviewed external write tools.
- Depend on unversioned private context.
- Emit action-driving prose when structured output is required.

