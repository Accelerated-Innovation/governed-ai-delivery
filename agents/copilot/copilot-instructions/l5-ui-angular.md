---
applyTo: "**"
---
# GitHub Copilot Instructions — Level 5 GenAI Operations (Angular UI)

These instructions govern how GitHub Copilot plans, reasons, and generates code in this Angular UI repository at Level 5.

They are mandatory.

Copilot must treat this repository as a governed delivery system, not an open coding environment.

Repository artifacts are the source of truth. Chat memory is not.

---

## 1. Operating Mode

Copilot operates aligned to:

* Product specifications under `features/`
* UI architecture contracts under `docs/ui/architecture/`
* UI evaluation standards under `docs/ui/evaluation/`
* Backend LLM contracts under `docs/backend/architecture/` — this UI consumes LLM features through a governed backend gateway
* Governance rules under `governance/ui/`

Before planning or generating code:

* Read all files under `docs/ui/architecture/`
* Read `docs/ui/evaluation/eval_criteria.md`
* Read the L5 backend LLM contracts for any LLM-adjacent UI code: `LLM_GATEWAY_CONTRACT.md`, `OBSERVABILITY_LLM_CONTRACT.md`, `GUARDRAILS_CONTRACT.md`, `EVALUATION_LLM_CONTRACT.md`
* Apply MVVM contract, component conventions, state management rules, evaluation standards, and the backend LLM contracts as binding constraints
* Confirm required feature artifacts exist

If required inputs are missing, stop and ask.

---

## 2. MVVM Architecture

This project follows MVVM with a vertical slice feature structure:

```
src/
├── features/<feature>/
│   ├── components/   # View — standalone Angular components
│   ├── hooks/        # ViewModel — TanStack Angular Query inject functions
│   ├── store/        # ViewModel — Signal store for client state
│   ├── api/          # Model — API client services (including LLM-backed endpoints)
│   └── types/        # Feature-local TypeScript types
├── shared/
│   ├── components/   # Shared UI primitives only
│   └── api/          # Base ApiService, interceptors, auth headers
└── app/              # Entry point, routing, providers
```

LLM features in this UI never call provider SDKs directly. All LLM-driven behavior is consumed through backend-exposed endpoints that route through the LLM Gateway. See `LLM_GATEWAY_CONTRACT.md`.

---

## 3. Mandatory Feature Structure

Every feature must live under `features/<feature_name>/` with these artifacts:

* `acceptance.feature`
* `nfrs.md` (including LLM Latency, LLM Cost, LLM Fallback, LLM Safety for any LLM-backed feature)
* `eval_criteria.yaml` (with DeepEval/Promptfoo/RAGAS criteria for `mode: llm`)
* `plan.md`
* `architecture_preflight.md`

Implementation must not begin unless all artifacts exist and are complete.

---

## 4. Feature Lifecycle (Mandatory Order)

0. **Multi-agent features only:** run `/multi-agent-design` before architecture preflight to produce `agent_topology.md`
1. UI Architecture Preflight — `/ui-architecture-preflight`
2. GenAI Preflight — `/genai-preflight` (validates L5-specific decisions when the UI consumes an LLM-backed endpoint)
3. ADR creation (if required)
4. UI Spec Planning — `/ui-spec-planning`
5. Evaluation Suite Planning — `/eval-suite-planning` (plans DeepEval/Promptfoo/RAGAS suites)
6. Evaluation Compliance Summary in `plan.md`
7. UI Implementation Planning — `/ui-implementation-plan`
8. Incremental implementation (API → ViewModel → View)
9. Component, E2E, and LLM evaluation tests
10. CI gates (UI quality gate + UI eval gate + backend eval gate when LLM-backed)

Steps may not be skipped. Implementation order within a feature must follow the MVVM layer sequence: API layer first, ViewModel second, View last.

---

## 5. Layer Rules

Layer rules load automatically via `.github/instructions/govkit/*.instructions.md` with `applyTo:` globs.

### View — Components (`src/features/*/components/`)
* Standalone Angular components only — no `NgModule` registration
* No direct API calls — no `HttpClient` injection in component files
* No data transformation — fix the inject function, not the component
* No imports from another feature's internals
* No raw LLM responses rendered without guardrail metadata having been honoured by the API/ViewModel layers
* All data via TanStack Angular Query inject functions or Signal store selectors

### ViewModel — Hooks (`src/features/*/hooks/`)
* All server state via TanStack Angular Query (`injectQuery`, `injectMutation`)
* Transform API responses here — never in components
* For LLM-backed endpoints: surface gateway-emitted error codes (rate limit, guardrail rejection, fallback exhausted) as typed states the View can render
* Query keys defined as constants in `query-keys.ts`

### ViewModel — Store (`src/features/*/store/`)
* Signal store for UI-only state — never store server data
* Never store raw LLM responses — they belong in the query cache, scoped per request
* Feature-scoped stores — no global catch-all store

### Model — API (`src/features/*/api/`)
* Plain Angular services with `HttpClient` — no components, no Query injection
* Use shared `ApiService` from `src/shared/api/`
* LLM-backed calls go to backend endpoints only; the UI never imports an LLM provider SDK
* Honour backend-emitted rate-limit and fallback signals; surface them to the ViewModel as typed errors
* All requests and responses explicitly typed — no `any`

---

## 6. Boundary Rules

Hard constraints. Never violate without an accepted ADR.

* Components must not import from `api/` directly
* Components must not import from another feature's internals
* Signal stores must not call API services directly
* `shared/` must not import from `features/`
* No business logic outside `hooks/` and `api/`
* **No direct LLM provider SDK imports anywhere in the UI** — all LLM traffic flows through backend endpoints that use the governed LLM Gateway
* **No guardrail bypass in the UI** — the UI must not strip or ignore guardrail metadata returned by the backend

---

## 7. ADR Rules

An ADR is required when:

* A new state management library is introduced
* A new shared component library is introduced
* Cross-feature state dependency is needed
* A backend contract does not exist and must be negotiated
* Any MVVM boundary rule is intentionally violated
* A new UI dependency is added
* A new LLM-backed endpoint contract is introduced or materially changed
* The UI's handling of guardrail rejection messages or fallback states changes
* The UI begins consuming a new LLM provider's surface (e.g. streaming token rendering for a model not previously supported)

All ADRs live under `docs/ui/architecture/ADR/` and follow `governance/ui/templates/architecture_preflight.md`. Implementation must not proceed until the ADR status is **Accepted**.

---

## 8. Evaluation Discipline

Every feature must include `eval_criteria.yaml` validated against `governance/ui/schemas/eval_criteria.schema.json`.

Before implementation:

* Read `docs/ui/evaluation/eval_criteria.md`
* Read `docs/backend/architecture/EVALUATION_LLM_CONTRACT.md` for any LLM-backed feature
* Confirm `plan.md` contains a completed Evaluation Compliance Summary
* Predicted FIRST average must be ≥ 4.0
* Zero predicted critical axe-core violations
* DeepEval metrics defined for `mode: llm` features
* Promptfoo addressed for user-facing LLM features (required or justified as not required)
* RAGAS addressed if the feature consumes retrieval-backed endpoints

If thresholds are not met, revise the plan before generating code.

---

## 9. Testing Requirements

Each increment must include:

* Component tests — Karma + Jasmine (or Vitest with `@analogjs/vitest-angular`) and Angular Testing Library (FIRST compliant)
* Accessibility check — axe-core in every component test
* Inject-function tests — Angular `TestBed` + MSW for API mocking (including LLM error states)
* E2E tests — Playwright for every `@e2e`-tagged Gherkin scenario with axe scan
* **DeepEval / Promptfoo / RAGAS tests** for any LLM-backed user flow — orchestrated by the backend evaluation harness; the UI test plan must reference the corresponding backend eval suite

---

## 10. Quality Gates

All generated code must pass:

* TypeScript strict mode (`tsc --noEmit`)
* ESLint including `@angular-eslint/template/accessibility-*`
* Zero critical axe-core violations
* All component and E2E tests
* All LLM evaluation gates for LLM-backed features

Violations must be fixed before proceeding.

---

## 11. Automatic Refactor Conditions

Copilot must trigger refactor before proceeding if:

* Component contains business logic or data transformation
* Inject function exposes raw API response (including raw LLM response) to components
* FIRST average predicted below 4.0
* Any critical accessibility violation detected
* Cross-layer import introduced
* LLM call observed outside the Model layer
* Guardrail metadata stripped or ignored

---

## 12. Authority

Architecture decisions belong to the Architect. Exceptions require an ADR and explicit approval. Copilot follows standards. It does not invent them.

---

## 13. Commit Discipline

- Complete one increment, then commit before starting the next
- Each commit must be independently buildable and testable
- Commit message references the increment: `feat(<feature>): increment N — <name>`
- Do not combine multiple increments into a single commit
- If an increment exceeds ~300 lines of production code, split it before committing
