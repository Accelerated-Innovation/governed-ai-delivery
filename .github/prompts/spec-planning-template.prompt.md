Plan the implementation of the feature: **{{FEATURE_NAME}}**

Use these specifications:

* NFRs: `features/{{FEATURE_NAME}}/nfrs.md`
* Acceptance: `features/{{FEATURE_NAME}}/acceptance.feature`
* LLM Evaluation: `features/{{FEATURE_NAME}}/eval_criteria.yaml`
* Architecture Standards: `docs/architecture/**`

## Instructions

1. Read all spec files.
2. Summarize the business goal and scope of the feature.
3. Identify required:

   * Inbound ports (service interface)
   * Domain logic modules (`services/`)
   * Outbound ports (infrastructure dependencies)
   * Adapters for storage, external APIs, etc.
   * API route entrypoints
4. Flag any deviation from architecture contracts (e.g., layering, boundaries).
5. Recommend whether an ADR is required for:

   * New outbound dependencies
   * Cross-boundary violations
   * Architectural changes or novel patterns
6. Produce a Markdown plan with:

   * Task checklist (files/modules to create or edit)
   * Testing plan (unit, integration, evals)
   * Risk or follow-up items

Output should be actionable and align with `ARCH_CONTRACT.md`, `API_CONVENTIONS.md`, and security/auth requirements.

The output will be used as input to `/implementation-plan`.
