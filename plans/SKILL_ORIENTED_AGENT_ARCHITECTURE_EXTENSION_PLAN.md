# Skill-Oriented Agent Architecture Extension Plan

## Status

Implementation complete on `feature/skill-oriented-agent-architecture`.

## Outcome

Add a bundled GovKit architecture extension that translates the approved SOAA v0.2 architecture into focused guidance for Codex, Claude Code, and Copilot while they implement agentic applications.

## Binding source

- SOAA v0.2, approved 2026-07-18
- Decisions SOAA-001 through SOAA-020
- Invariants SOAA-INV-001 through SOAA-INV-206
- Midpoint amendments SOAA-MID-001 through SOAA-MID-006
- Packet 7 integration review score: 93.13 out of 100

## Scope

- [x] Inspect the current GovKit extension mechanism and bundled examples.
- [x] Resolve the approved SOAA source set.
- [x] Define profile-based contract loading.
- [x] Add the new extension manifest and README.
- [x] Add architecture guidance contracts.
- [x] Add manifest, content, installation, and validation tests.
- [x] Update root extension documentation.
- [x] Run focused and full verification.

## Verification result

- Focused extension and schema suite: 167 passed.
- Agent Skills compatibility amendment suite: 28 passed.
- Full repository suite: 1048 passed, 1 skipped.
- Diff whitespace validation: passed.
- Wheel build and bundled-extension inventory: passed.

## Extension structure

```text
extensions/skill-oriented-agent-architecture/
├── manifest.yaml
├── README.md
└── docs/backend/architecture/
    ├── SKILL_ORIENTED_AGENT_ARCHITECTURE.md
    ├── SKILL_CONTRACT.md
    ├── RUNTIME_STATE_AND_EXECUTION_CONTRACT.md
    ├── SKILL_SELECTION_AND_ACTIVATION_CONTRACT.md
    ├── AUTHORITY_AND_APPROVAL_CONTRACT.md
    ├── CONTEXT_MEMORY_AND_RESOURCE_CONTRACT.md
    ├── RESILIENCE_AND_RECOVERY_CONTRACT.md
    ├── EVALUATION_EVIDENCE_AND_COMPLETION_CONTRACT.md
    └── SKILL_LIFECYCLE_AND_INTEROPERABILITY_CONTRACT.md
```

## Design rules

- Preserve provider and framework neutrality.
- Keep adaptive proposals separate from trusted commits.
- Load contract sets progressively by feature applicability.
- Preserve one task owner, deterministic admission, exact-release activation, effective authority, fresh operation authorization, and independent completion.
- Treat skill procedure as context, not executable authority.
- Map every authoritative aggregate to one trusted writer.
- Require durable evidence across selection, activation, action, evaluation, and completion.
- Keep SOAA conformance claims outside this guidance profile until the 206-assertion suite exists.

## Existing agentic-skills extension

The existing `agentic-skills` extension governs a specific skill-family and phase-state-machine design. It is a runtime application extension, not a coding-agent-only skill pack. Its scope overlaps the new SOAA extension.

This increment leaves it unchanged to avoid an unrequested deletion. After the new extension is reviewed, retire `agentic-skills` or rename it only if its product-specific family model remains useful. Do not install both extensions in one consuming project.

## LLM application extension decision

Create a separate `llm-application` extension in a follow-on change.

Rationale:

- LLM applications exist without agents or skills.
- SOAA does not require one model provider, gateway, evaluator, telemetry system, or guardrail product.
- Skill runtimes and LLM operations evolve at different rates.
- Separate packages prevent LLM vendor choices from entering the SOAA control model.
- Vision, RAG, assistant, and agent extensions should reference one shared LLM application package.

The package should own four provider-neutral contracts:

- `LLM_GATEWAY_CONTRACT.md`
- `LLM_EVALUATION_CONTRACT.md`
- `LLM_OBSERVABILITY_CONTRACT.md`
- `MODEL_GUARDRAILS_CONTRACT.md`

Current product choices such as LiteLLM, OpenLLMetry, Langfuse, DeepEval, Promptfoo, RAGAS, NeMo Guardrails, and Guardrails AI should move into an implementation profile or guide layer rather than remain mandatory architecture.

Extracting the package is a separate change because current Level 5 manifests, rules, skills, CI gates, starter features, setup guides, stack documents, tests, and the vision extension all reference the four core files.
