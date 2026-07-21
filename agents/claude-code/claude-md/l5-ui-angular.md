# Governed AI Delivery — Claude Code Instructions (Level 5: GenAI Operations — Angular UI)

These instructions are mandatory. Claude operates as a governed delivery system, not an open coding environment.

Repository artifacts are the source of truth. Chat history is not.

---

## Operating Mode

Claude operates aligned to:

- Product specifications under `features/`
- UI architecture contracts under `docs/ui/architecture/`
- UI evaluation standards under `docs/ui/evaluation/`
- Backend API contracts for any model-backed behavior — the UI consumes model features through a governed backend
- Governance rules under `governance/ui/`

Before planning or generating code:

- Read all files under `docs/ui/architecture/`
- Read `docs/ui/evaluation/eval_criteria.md`
- If this repository owns model execution, confirm `extensions/llm-application/manifest.yaml` exists and read its applicable contract sets
- If model execution belongs to another service, read its versioned API contract and keep all provider access and model controls behind that backend boundary
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
│       ├── components/   # View — standalone Angular components, no business logic
│       ├── hooks/        # ViewModel — TanStack Angular Query inject functions
│       ├── store/        # ViewModel — Signal store for client state
│       ├── api/          # Model — API client services (HttpClient wrappers)
│       └── types/        # TypeScript types for this feature
├── shared/
│   ├── components/       # Shared UI primitives only
│   └── api/              # Base ApiService, interceptors, auth headers
└── app/                  # Entry point, routing, providers
```

LLM features in this UI never call provider SDKs directly. All LLM-driven behavior is consumed through backend-exposed endpoints that route through the governed backend model gateway. See `LLM_GATEWAY_CONTRACT.md`.

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

0. **Multi-agent features only:** run `/govkit-multi-agent-design` before architecture preflight to produce `agent_topology.md`
1. UI Architecture Preflight → run `/govkit-ui-architecture-preflight`
2. LLM Application Preflight — run the GenAI preflight skill only when this repository owns model execution
3. ADR creation (if required by preflight)
4. UI Spec Planning → run `/govkit-ui-spec-planning`
5. Evaluation Suite Planning → run `/govkit-eval-suite-planning` (plans configured quality/adversarial/retrieval evaluators suites where the UI exercises LLM behavior)
6. Evaluation Compliance Summary (must be in `plan.md`)
7. UI Implementation Planning → run `/govkit-ui-implementation-plan`
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
- Standalone Angular components only — no `NgModule` registration
- No direct API calls. No `HttpClient` injection.
- No business logic or data transformation
- No raw LLM responses rendered without guardrail metadata having been honoured by the API/ViewModel layers
- All data via TanStack Angular Query inject functions or Signal store selectors

### ViewModel — Hooks (`src/features/<feature>/hooks/`)
- All server state via TanStack Angular Query (`injectQuery`, `injectMutation`)
- Transform API responses here — never in components
- For LLM-backed endpoints: surface gateway-emitted error codes (rate limit, guardrail rejection, fallback exhausted) as typed states the View can render

### ViewModel — Store (`src/features/<feature>/store/`)
- Signal store for client-only UI state (modals, selections, pagination)
- Never store server data — server data belongs in TanStack Angular Query cache
- Never store raw LLM responses — they belong in the query cache, scoped per request

### Model — API (`src/features/<feature>/api/`)
- Plain Angular services with `HttpClient` — no components, no Query injection
- Use shared `ApiService` from `src/shared/api/`
- LLM-backed calls go to backend endpoints only; the UI never imports an LLM provider SDK
- Honour backend-emitted rate-limit and fallback signals; surface them to the ViewModel as typed errors

---

## Boundary Rules

Hard constraints. Never violate without an accepted ADR.

- Components must not import from `api/` directly
- Components must not import from another feature's internals
- Signal stores must not call API services directly — use TanStack mutations
- `shared/` must not import from `features/`
- No business logic outside `hooks/` and `api/`
- **No direct LLM provider SDK imports anywhere in the UI** — all LLM traffic flows through backend endpoints that use the governed model gateway
- **No guardrail bypass in the UI** — the UI must not strip or ignore guardrail metadata returned by the backend

---

## Evaluation Discipline

Before implementation:

- Read `docs/ui/evaluation/eval_criteria.md`
- If installed locally, read the applicable `llm-application` evaluation contract; otherwise reference the backend service's evaluation evidence through its API contract
- Read `features/<feature_name>/eval_criteria.yaml`
- Confirm FIRST, 7 Virtue, axe, and LLM evaluation thresholds

Implementation must not proceed unless:

- An Evaluation Compliance Summary exists in `plan.md` with predicted averages meeting thresholds
- Zero predicted critical axe-core violations
- declared quality criteria are defined for `mode: llm` features
- adversarial evaluation is addressed (required or justified as not required) for user-facing LLM features
- retrieval evaluation is addressed if the feature consumes retrieval-backed endpoints

CI evaluation gates are binding.

---

## Testing Requirements

Each increment must include:

- Component tests — Karma + Jasmine (or Vitest with `@analogjs/vitest-angular`) and Angular Testing Library (FIRST compliant)
- Accessibility check — axe-core in every component test
- Inject-function tests — Angular `TestBed` + MSW for API mocking (including LLM error states)
- E2E tests — Playwright for every `@e2e`-tagged Gherkin scenario with axe scan
- **configured quality, adversarial, and retrieval evaluators tests** for any LLM-backed user flow — orchestrated by the backend evaluation harness; the UI test plan must reference the corresponding backend eval suite

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
