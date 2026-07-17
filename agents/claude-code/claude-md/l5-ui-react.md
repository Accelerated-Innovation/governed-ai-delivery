# Governed AI Delivery — Claude Code Instructions (Level 5: GenAI Operations — React UI)

These instructions are mandatory. Claude operates as a governed delivery system, not an open coding environment.

Repository artifacts are the source of truth. Chat history is not.

---

## Operating Mode

Claude operates aligned to:

- Product specifications under `features/`
- UI architecture contracts under `docs/ui/architecture/`
- UI evaluation standards under `docs/ui/evaluation/`
- Backend LLM contracts under `docs/backend/architecture/` (LLM gateway, guardrails, observability, evaluation) — this UI consumes LLM features through a governed backend gateway
- Governance rules under `governance/ui/`

Before planning or generating code:

- Read all files under `docs/ui/architecture/`
- Read `docs/ui/evaluation/eval_criteria.md`
- Read the L5 backend LLM contracts that bind any LLM-adjacent UI code:
  - `docs/backend/architecture/LLM_GATEWAY_CONTRACT.md`
  - `docs/backend/architecture/OBSERVABILITY_LLM_CONTRACT.md`
  - `docs/backend/architecture/GUARDRAILS_CONTRACT.md`
  - `docs/backend/architecture/EVALUATION_LLM_CONTRACT.md`
- Apply MVVM contract, component conventions, state management rules, evaluation standards, and the backend LLM contracts as binding constraints
- Confirm required feature artifacts exist

If required inputs are missing, stop and ask.

---

## Architecture

This project uses MVVM with a vertical slice feature structure.

```
src/
├── features/
│   └── <feature-name>/
│       ├── components/   # View — pure React components, no business logic
│       ├── hooks/        # ViewModel — React Query hooks, data transformation
│       ├── store/        # ViewModel — Zustand client state
│       ├── api/          # Model — API client functions (fetch wrappers)
│       └── types/        # TypeScript types for this feature
├── shared/
│   ├── components/       # Shared UI primitives only
│   └── api/              # Base API config, interceptors, auth headers
└── app/                  # Entry point, routing, providers
```

LLM features in this UI never call provider SDKs directly. All LLM-driven behavior is consumed through backend-exposed endpoints that route through the LLM Gateway. See `LLM_GATEWAY_CONTRACT.md`.

---

## Mandatory Feature Structure

Every feature must live under `features/<feature_name>/` with these required artifacts:

- `acceptance.feature`
- `nfrs.md` (including LLM Latency, LLM Cost, LLM Fallback, LLM Safety for any LLM-backed feature)
- `eval_criteria.yaml`
- `plan.md`
- `architecture_preflight.md`

Implementation must not begin unless all five artifacts exist.

---

## Feature Lifecycle (Mandatory Order — no steps may be skipped)

0. **Multi-agent features only:** run `/multi-agent-design` before architecture preflight to produce `agent_topology.md`
1. UI Architecture Preflight → run `/ui-architecture-preflight`
2. GenAI Preflight → run `/genai-preflight` (validates L5-specific decisions — applies whenever the UI consumes an LLM-backed endpoint)
3. ADR creation (if required by preflight)
4. UI Spec Planning → run `/ui-spec-planning`
5. Evaluation Suite Planning → run `/eval-suite-planning` (plans DeepEval/Promptfoo/RAGAS suites where the UI exercises LLM behavior)
6. Evaluation Compliance Summary (must be in `plan.md`)
7. UI Implementation Planning → run `/ui-implementation-plan`
8. Incremental implementation — API → ViewModel → View
9. Component, E2E, and LLM evaluation tests
10. CI gates (UI quality gate + UI eval gate + backend eval gate when LLM-backed)

---

## Layer Rules

Layer-specific rules are consolidated in `.claude/rules/govkit/governance-src.md`. Claude Code loads it automatically when working anywhere under `src/`. Categories covered:

- Component rules — `**/components/**`
- ViewModel rules (hooks + store) — `**/hooks/**`, `**/store/**`
- API (Model) rules — `**/api/**`
- Accessibility rules — all UI files

### View — Components (`src/features/<feature>/components/`)
- No direct API calls. No fetch. No axios.
- No business logic or data transformation
- No raw LLM responses rendered without guardrail metadata having been honoured by the API/ViewModel layers
- All data via React Query hooks or Zustand selectors

### ViewModel — Hooks (`src/features/<feature>/hooks/`)
- All server state via React Query
- Transform API responses here — never in components
- For LLM-backed endpoints: surface gateway-emitted error codes (rate limit, guardrail rejection, fallback exhausted) as typed states the View can render

### ViewModel — Store (`src/features/<feature>/store/`)
- Zustand for client-only UI state (modals, selections, pagination)
- Never store server data — server data belongs in React Query cache
- Never store raw LLM responses — they belong in the React Query cache, scoped per request

### Model — API (`src/features/<feature>/api/`)
- Plain async functions — no React, no hooks
- Use shared base client from `src/shared/api/`
- LLM-backed calls go to backend endpoints only; the UI never imports an LLM provider SDK
- Honour backend-emitted rate-limit and fallback signals; surface them to the ViewModel as typed errors

---

## Boundary Rules

Hard constraints. Never violate without an accepted ADR.

- Components must not import from `api/` directly
- Components must not import from another feature's internals
- Zustand stores must not call API functions directly — use React Query mutations
- `shared/` must not import from `features/`
- No business logic outside `hooks/` and `api/`
- **No direct LLM provider SDK imports anywhere in the UI** — all LLM traffic flows through backend endpoints that use the governed LLM Gateway
- **No guardrail bypass in the UI** — the UI must not strip or ignore guardrail metadata returned by the backend

---

## Evaluation Discipline

Before implementation:

- Read `docs/ui/evaluation/eval_criteria.md`
- Read `docs/backend/architecture/EVALUATION_LLM_CONTRACT.md` for any LLM-backed feature
- Read `features/<feature_name>/eval_criteria.yaml`
- Confirm FIRST, 7 Virtue, axe, and LLM evaluation thresholds

Implementation must not proceed unless:

- An Evaluation Compliance Summary exists in `plan.md` with predicted averages meeting thresholds
- Zero predicted critical axe-core violations
- DeepEval metrics are defined for `mode: llm` features
- Promptfoo is addressed (required or justified as not required) for user-facing LLM features
- RAGAS is addressed if the feature consumes retrieval-backed endpoints

CI evaluation gates are binding.

---

## Testing Requirements

Each increment must include:

- Component tests — Vitest + React Testing Library (FIRST compliant)
- Accessibility check — `jest-axe` in every component test
- Hook tests — `renderHook` + MSW for API mocking (including LLM error states)
- E2E tests — Playwright for every `@e2e`-tagged Gherkin scenario with axe scan
- **DeepEval / Promptfoo / RAGAS tests** for any LLM-backed user flow — orchestrated by the backend evaluation harness; the UI test plan must reference the corresponding backend eval suite

---

## ADR Rules

An ADR is required when:

- A new state management library is introduced
- A new shared component library is introduced
- Cross-feature state dependency is needed
- A backend contract does not exist and must be negotiated
- Any MVVM boundary rule is intentionally violated
- A new UI dependency is added
- A new LLM-backed endpoint contract is introduced or materially changed
- The UI's handling of guardrail rejection messages or fallback states changes
- The UI begins consuming a new LLM provider's surface (e.g. streaming token rendering for a model not previously supported)

---

## Authority

Architecture decisions belong to the Architect. Exceptions require an ADR and explicit approval. Claude follows standards — it does not invent them.

---

## Commit Discipline

- Complete one increment, then commit before starting the next
- Each commit must be independently buildable and testable
- Commit message references the increment: `feat(<feature>): increment N — <name>`
- Do not combine multiple increments into a single commit
- If an increment exceeds ~300 lines of production code, split it before committing
