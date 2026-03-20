# GitHub Copilot Instructions — React UI

These instructions govern how GitHub Copilot plans, reasons, and generates code in this React UI repository.

They are mandatory.

Copilot must treat this repository as a governed delivery system, not an open coding environment.

Repository artifacts are the source of truth. Chat memory is not.

---

## 1. Operating Mode

Copilot operates aligned to:

* Product specifications under `features/`
* Architecture contracts under `docs/ui/architecture/`
* Evaluation standards under `docs/ui/evaluation/`
* Governance rules under `governance/ui/`

Before planning or generating code:

* Read all files under `docs/ui/architecture/`
* Read `docs/ui/evaluation/eval_criteria.md`
* Apply MVVM contract, component conventions, state management rules, and evaluation standards as binding constraints
* Confirm required feature artifacts exist

If required inputs are missing, stop and ask.

---

## 2. MVVM Architecture

This project follows MVVM with a vertical slice feature structure:

```
src/
├── features/<feature>/
│   ├── components/   # View — pure React components
│   ├── hooks/        # ViewModel — React Query hooks
│   ├── store/        # ViewModel — Zustand client state
│   ├── api/          # Model — API client functions
│   └── types/        # Feature-local TypeScript types
├── shared/
│   ├── components/   # Shared UI primitives only
│   └── api/          # Base API config, auth headers
└── app/              # Entry point, routing, providers
```

See `docs/ui/architecture/MVVM_CONTRACT.md` for full rules.

---

## 3. Mandatory Feature Structure

Every feature must live under `features/<feature_name>/` with these artifacts:

* `acceptance.feature`
* `nfrs.md`
* `eval_criteria.yaml`
* `plan.md`
* `architecture_preflight.md`

Implementation must not begin unless all artifacts exist and are complete.

---

## 4. Feature Lifecycle (Mandatory Order)

All work follows this sequence:

1. Architecture Preflight
2. ADR creation (if required)
3. Spec Planning
4. Implementation Planning
5. Incremental implementation (API → ViewModel → View)
6. Component and E2E tests
7. CI gates

Steps may not be skipped. Implementation order within a feature must follow the MVVM layer sequence: API layer first, ViewModel second, View last.

---

## 5. Layer Rules

### View — Components (`src/features/*/components/`)
* No direct API calls — no `fetch`, `axios`, or `useQuery` in component files
* No data transformation — fix the hook, not the component
* No imports from another feature's internals
* All data via React Query hooks or Zustand selectors

### ViewModel — Hooks (`src/features/*/hooks/`)
* All server state via React Query
* Transform API responses in the `select` option — never in components
* Query keys defined as constants in `queryKeys.ts`
* Mutations must invalidate relevant query keys on success

### ViewModel — Store (`src/features/*/store/`)
* Zustand for UI-only state — never store server data
* Feature-scoped stores — no global catch-all store
* Export named actions, not raw setters
* Never call API functions from a store

### Model — API (`src/features/*/api/`)
* Plain async functions — no React, no hooks
* Use shared base client from `src/shared/api/`
* All requests and responses explicitly typed — no `any`

---

## 6. Boundary Rules

Hard constraints. Never violate without an accepted ADR.

* Components must not import from `api/` directly
* Components must not import from another feature's internals
* Zustand stores must not call API functions directly
* `shared/` must not import from `features/`
* No business logic outside `hooks/` and `api/`

---

## 7. ADR Rules

An ADR is required when:

* A new state management library is introduced
* A new shared component library is introduced
* Cross-feature state dependency is needed
* A backend contract does not exist and must be negotiated
* Any MVVM boundary rule is intentionally violated
* A new UI dependency is added

All ADRs live under `docs/ui/architecture/ADR/` and follow `governance/ui/templates/architecture_preflight.md`.

Implementation must not proceed until the ADR status is **Accepted**.

---

## 8. Evaluation Discipline

Every feature must include `eval_criteria.yaml` validated against `governance/ui/schemas/eval_criteria.schema.json`.

Before implementation:

* Read `docs/ui/evaluation/eval_criteria.md`
* Confirm `plan.md` contains a completed Evaluation Compliance Summary
* Predicted FIRST average must be ≥ 4.0
* Zero predicted critical axe-core violations
* All `@e2e` Gherkin scenarios must have planned Playwright tests

If thresholds are not met, revise the plan before generating code.

---

## 9. Testing Requirements

Each increment must include:

* Component tests — Vitest + React Testing Library (FIRST compliant)
* Accessibility check — `jest-axe` in every component test
* Hook tests — `renderHook` + MSW for API mocking
* E2E tests — Playwright for every `@e2e`-tagged Gherkin scenario with axe scan

---

## 10. Quality Gates

All generated code must pass:

* TypeScript strict mode (`tsc --noEmit`)
* ESLint including `eslint-plugin-jsx-a11y`
* Zero critical axe-core violations
* All component and E2E tests

Violations must be fixed before proceeding.

---

## 11. Automatic Refactor Conditions

Copilot must trigger refactor before proceeding if:

* Component contains business logic or data transformation
* Hook exposes raw API response to components
* FIRST average predicted below 4.0
* Any critical accessibility violation detected
* Cross-layer import introduced

---

## 12. Authority

Architecture decisions belong to the Architect.

Exceptions require an ADR and explicit approval.

Copilot follows standards. It does not invent them.
