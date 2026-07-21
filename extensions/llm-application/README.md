# LLM Application Extension

## Purpose

The `llm-application` extension guides coding agents building governed applications that call language models. It owns four concerns that are optional for the GovKit core and shared by agentic and non-agentic LLM systems:

- model access through an application-owned gateway port
- model evaluation and regression gates
- model-specific observability and provenance
- input, context, tool-call, and output guardrails

The contracts are provider, model, framework, and product neutral. Concrete products are implementation choices recorded in an ADR or implementation profile; they are not architecture requirements.

## Install

```bash
govkit extension add llm-application --target .
```

The extension targets GovKit Level 5 backend API and CLI projects. It is independent of agent architecture and can govern a single model-backed endpoint, a retrieval application, a batch process, or an agentic system.

## Contract loading

Load `llm_gateway` for every model-backed feature. Load the remaining sets only when the feature touches their concerns.

| Contract set | Load when the feature touches |
|---|---|
| `llm_gateway` | Model calls, prompts, embeddings, routing, fallbacks, quotas, budgets, provider adapters |
| `model_guardrails` | Untrusted input, prompt injection, content policy, tool calls, structured output, consequential actions |
| `llm_observability` | Traces, metrics, logs, usage, cost, prompt/model provenance, production monitoring |
| `llm_evaluation` | Quality, safety, retrieval, regression, red-team, model-as-judge, release gates |

This structure preserves progressive disclosure. A coding agent should not load every contract for every feature.

## Architecture documents

The extension ships these contracts under `docs/backend/architecture/`:

- `LLM_GATEWAY_CONTRACT.md`
- `LLM_EVALUATION_CONTRACT.md`
- `LLM_OBSERVABILITY_CONTRACT.md`
- `MODEL_GUARDRAILS_CONTRACT.md`

## Relationship to Skill-Oriented Agent Architecture

The extensions are complementary:

- `llm-application` owns model access, model guardrails, model telemetry, and model evaluation.
- `skill-oriented-agent-architecture` owns agent execution, skills, authority, state, side effects, recovery, evidence, and task completion.

Install both for a skill-oriented agent that invokes language models. SOAA constraints remain authoritative for agent control boundaries; the LLM application contracts govern the model-facing parts inside those boundaries. Neither extension requires the other for systems outside the overlap.

## Implementation profiles

An implementation profile may select a gateway, evaluation framework, telemetry backend, or guardrail library. A profile must map each product to the ports and evidence defined here, pin compatible versions, document operational ownership, and preserve substitutability. Product selection never grants an SDK permission to cross an application boundary.

The extension ships one such profile — `docs/backend/architecture/GATEWAY_STACK.md` —
with **default product bindings** (LiteLLM for the gateway, OpenLLMetry → Langfuse
for telemetry, NeMo Guardrails / Guardrails AI for guardrails) that a team can adopt
and then customize. It is **advisory** (`authority: defaults`): the contracts remain
authoritative, and deviating from a default requires an ADR
(`product_selection_requires_adr: true`). It is declared under `implementation_profiles`
in the manifest, not `contract_sets`, because it names products — the neutrality the
contracts hold does not apply to it. Evaluation products are not restated in the
profile; they are governed by the core `EVAL_STACK.md`. No blocking CI conformance
gate is wired to the profile today.
