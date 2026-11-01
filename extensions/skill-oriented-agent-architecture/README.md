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

## Start here: one agent with fixed skills

Most first features have one agent run that uses two or three skills, fixed by
trusted code or chosen by the model from a small menu. That is enough for SOAA
to apply; agent count does not decide it.

1. In architecture preflight Section 15a, copy
   [`templates/preflight-soaa.md`](templates/preflight-soaa.md) and decide each
   condition in [`SOAA_APPLICABILITY.md`](docs/backend/architecture/SOAA_APPLICABILITY.md).
   Such a feature usually applies `adaptive-run`, `skill-activation` and
   `untrusted-input`, plus `model-selection` only when the model chooses among
   the skills.
2. Read `soaa_core`, then only the contract sets those conditions need.
3. Record the changed rows of the system-level role and writer maps.
4. If a material assumption is untested, set the preflight outcome to
   `experiment-required` and plan the smallest experiment from
   [`SOAA_EXPERIMENTS.md`](docs/backend/architecture/SOAA_EXPERIMENTS.md),
   usually E1.

Controls follow behavior and consequence. An omitted condition needs a reason,
a verified absent or disabled interface, an owner and a change trigger; an
unknown condition stays unresolved.

## Three layers

| Layer | Applies when the feature… | Guidance |
|---|---|---|
| LLM application | calls language models (`mode: llm`) | `llm-application` |
| SOAA | uses governed runtime skills, an adaptive agent loop or their control boundaries | This extension |
| Multi-agent topology | coordinates multiple agents | `agent_topology.md` |

`multi_agent: true` is only for topology. It does not decide whether SOAA
applies, and a feature without it can still need every SOAA control above.

## Agent Skills compatibility

The SOAA package profile preserves a standard root `SKILL.md` and places governance metadata in an additional `soaa/` directory permitted by the Agent Skills format. A generic Agent Skills client may ignore the SOAA files and process the standard skill, but it must not claim SOAA conformance. A SOAA-aware runtime validates both the Agent Skills format and the SOAA profile before admission.

See [`SKILL_CONTRACT.md`](docs/backend/architecture/SKILL_CONTRACT.md) for the normative flat metadata keys, two-stage validation rule, and `allowed-tools` authority boundary.

## Install

Legacy install, copied to `extensions/skill-oriented-agent-architecture/`:

```bash
govkit extension add skill-oriented-agent-architecture --target .
```

Declarative install: select the pack's capabilities in `.govkit/profile.yaml`,
then run

```bash
govkit pack preview --target .
govkit pack apply --target .
```

The pack is pinned under `.govkit/packs/skill-oriented-agent-architecture/<digest>/`
and verified by `.govkit/pack-lock.json`. In either case, find the installed
root with `govkit extension list --installed --target .` and read every
`extensions/skill-oriented-agent-architecture/<path>` reference under that
root. Keep one verified copy; stop if the listing reports a conflict.

The extension targets GovKit Level 5 backend API and CLI projects. Agent architecture is extension-owned; GovKit core supplies only the shared structural, security, testing, and observability-port contracts.

## Contract loading

Load `soaa_core` for every feature in scope. Load the remaining sets only when the feature touches their concerns. A touched file matching a manifest `applies_to` glob only prompts that decision; it never brings a feature into scope by itself.

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

Advisory additions, not contract sets:

- `docs/backend/architecture/SOAA_APPLICABILITY.md`: the applicability matrix,
  the omission rule and the system-level role and writer map
- `docs/backend/architecture/SOAA_EXPERIMENTS.md`: experiment patterns E1–E5,
  stopping conditions and the mapping to `experiments.yaml`
- `templates/preflight-soaa.md`: the Section 15a applicability block
- `catalog/gk-soaa-cases.yaml`: GovKit local cases GK-SOAA-01 to 16 plus
  conditional cases, each tied to applicability conditions. They are not SOAA
  assertions.

## Implementation profile

The contracts above are product neutral. The extension also ships one
**implementation profile** — `docs/backend/architecture/AGENT_RUNTIME_STACK.md` —
that maps the runtime responsibilities to concrete **default product bindings**
(e.g. LangGraph for the decision loop, a durable checkpointer for restart) a team
can adopt and then customize.

The profile is **advisory** (`authority: defaults`). `RUNTIME_STATE_AND_EXECUTION_CONTRACT.md`
remains authoritative; where they disagree, the contract wins. Deviating from a
default binding requires an ADR (`product_selection_requires_adr: true`). It is
declared under `implementation_profiles` in the manifest, not `contract_sets`,
precisely because it names products — the neutrality that the contracts hold does
not apply to it. No blocking CI conformance gate is wired to the profile today.

## Relationship to LLM application governance

SOAA does not prescribe an LLM provider, model family, gateway product, evaluation product, observability product, or guardrail product. Those concerns also apply to LLM applications without skills and are owned by the separate `llm-application` extension.

Install both extensions when an SOAA-governed system invokes language models:

```bash
govkit extension add llm-application --target .
govkit extension add skill-oriented-agent-architecture --target .
```

The `llm-application` contracts govern the model-facing parts of the system. SOAA remains authoritative for task ownership, skill selection and activation, effective authority, side-effect control, recovery, evidence, and completion. SOAA can also govern a non-LLM runtime, so it does not declare the LLM extension as an unconditional dependency.

## Source authority and limits

This package is an implementation-guidance profile. It does not by itself establish SOAA conformance. Keep three claims distinct:

- **Report validation:** the schema, identity, coverage, applicability and internal consistency of supplied records.
- **Observed execution:** a trusted runner binding the target and cases to collected evidence. Experiment records and uploaded results never supply it by themselves.
- **Formal SOAA conformance:** the released normative profile and the verified assertion catalog. Nothing in this package claims it.

SOAA v0.2 conformance requires the approved normative modules, all 206 invariant-to-assertion identities, released schemas, fixtures, adapters, oracles, and a valid evidence package. The current SOAA source set records the conformance suite and reference runtime as future implementation work.

Where this guidance conflicts with a higher SOAA authority, use this precedence:

1. Approved invariant
2. Approved decision record
3. Applied midpoint amendment
4. SOAA v0.2 root cross-module rule
5. Most specific approved module contract
6. This GovKit guidance profile

An unresolved conflict blocks implementation and enters architecture review.

Known discrepancies with the SOAA v0.2 Architecture Guide are recorded in each contract's *Source alignment* table. Each one blocks only the affected compatibility claim.
