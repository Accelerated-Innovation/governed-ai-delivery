# GitHub Copilot Instructions — Angular UI

These instructions govern how GitHub Copilot plans, reasons, and generates code in this Angular UI repository.

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

If required inputs are missing, stop and ask.

---

## 2. MVVM Architecture

This project follows MVVM with a vertical slice feature structure:

```
src/
├── features/<feature>/
│   ├── components/   # View — standalone Angular components, OnPush
│   ├── hooks/        # ViewModel — TanStack Query inject functions
│   ├── store/        # ViewModel — Angular Signal stores
│   ├── api/          # Model — HttpClient wrapper async functions
│   └── types/        # Feature-local TypeScript types
├── shared/
│   ├── components/   # Shared UI primitives only
│   └── api/          # Shared ApiService, auth interceptor
└── app/              # Entry point, routing, app.config.ts
```

See `docs/ui/architecture/MVVM_CONTRACT.md` for full rules.

---

## 3. Mandatory Feature Structure

Every feature must live under `features/<feature_name>/` with:

* `acceptance.feature`, `nfrs.md`, `eval_criteria.yaml`, `plan.md`, `architecture_preflight.md`

Implementation must not begin until all artifacts exist and are complete.

---

## 4. Feature Lifecycle (Mandatory Order)

1. Architecture Preflight
2. ADR creation (if required)
3. Spec Planning
4. Implementation Planning
5. Incremental implementation — API → ViewModel → View
6. Component and E2E tests
7. CI gates

Steps may not be skipped.

---

## 5. Layer Rules

### View — Components
* Standalone components with `ChangeDetectionStrategy.OnPush` — always
* No direct `HttpClient` or API service injection
* No business logic or data transformation in class or template
* Use `@if`, `@for`, `@switch` control flow (Angular 17+)
* Signal-based inputs/outputs for new code

### ViewModel — Query Functions (`hooks/`)
* All server state via TanStack Angular Query (`injectQuery`, `injectMutation`)
* Transform API responses in `select` — never in templates
* Query keys as typed constants in `query-keys.ts`
* Mutations must invalidate affected query keys on success

### ViewModel — Signal Store (`store/`)
* Angular Signals for UI-only state only — never store server data
* Expose signals as read-only via `.asReadonly()`
* Feature-scoped — avoid `providedIn: 'root'` for feature state
* Never call API services from a store

### Model — API (`api/`)
* Plain async functions using the shared `ApiService`
* No Angular decorators in feature API files
* All types explicit — no `any`

---

## 6. Boundary Rules

* Components must not inject API services directly
* Components must not import from another feature's internals
* Signal stores must not call API services directly
* `shared/` must not import from `features/`

---

## 7. ADR Rules

An ADR is required when:
* A new state management library is introduced
* A new shared component library is introduced
* Cross-feature state is needed
* A backend contract does not exist
* Any MVVM boundary rule is intentionally violated
* Any intentional WCAG exception

All ADRs live under `docs/ui/architecture/ADR/`. Implementation must not proceed until ADR status is **Accepted**.

---

## 8. Evaluation Discipline

* Predicted FIRST average must be ≥ 4.0
* Zero predicted critical axe-core violations
* All `@e2e` Gherkin scenarios must have planned Playwright tests

If thresholds are not met, revise the plan before generating code.

---

## 9. Testing Requirements

Each increment must include:
* Component tests — Jest + Angular Testing Library (FIRST compliant)
* jest-axe accessibility check in every component test
* Query function tests — `TestBed` + `HttpClientTestingModule`
* E2E — Playwright for every `@e2e`-tagged Gherkin scenario with axe scan

---

## 10. Authority

Architecture decisions belong to the Architect. Exceptions require an ADR and explicit approval. Copilot follows standards. It does not invent them.

---

## 11. Commit Discipline

- Complete one increment, then commit before starting the next
- Each commit must be independently buildable and testable
- Commit message references the increment: `feat(<feature>): increment N — <name>`
- Do not combine multiple increments into a single commit
- If an increment exceeds ~300 lines of production code, split it before committing
