---
name: ui-implementation-plan
description: Generate an ordered UI implementation checklist from a validated plan and preflight
---

# Implementation Plan — UI

You are producing an Implementation Plan for a UI feature. Determine the feature name from the user's request; if it is not provided, ask before proceeding.

Read the following before proceeding:

- `features/<feature_name>/plan.md`
- `features/<feature_name>/architecture_preflight.md`
- `docs/ui/architecture/MVVM_CONTRACT.md`
- `docs/ui/architecture/*/STATE_MANAGEMENT.md`

---

Produce an ordered implementation checklist. Sequence must follow MVVM layer order: API → ViewModel → View.

## Implementation Order

### 1. Types and Interfaces
- [ ] Define request/response types in `src/features/<feature>/types/`
- [ ] Define ViewModel types (shaped for component consumption)

### 2. API Layer
- [ ] Create API functions in `src/features/<feature>/api/`
- [ ] Wire to shared base client / ApiService
- [ ] Write unit tests for API functions (mock HTTP at boundary)

### 3. ViewModel — Query Hooks / Inject Functions
- [ ] Define query keys in `queryKeys.ts` / `query-keys.ts`
- [ ] Create query hooks with `select` transforms
- [ ] Create mutation hooks with cache invalidation
- [ ] Write unit tests using the framework's test harness + MSW

### 4. ViewModel — Client Store (if applicable)
- [ ] Define store with typed actions (Zustand for React / Signal store for Angular)
- [ ] Write unit tests for store actions without rendering

### 5. View — Components
- [ ] Build components bottom-up (leaf components first)
- [ ] Wire to hooks — no direct API calls
- [ ] Write component tests (React Testing Library / Angular Testing Library)
- [ ] Run axe accessibility check in each test

### 6. E2E — Playwright
- [ ] Map each `@e2e`-tagged Gherkin scenario to a Playwright test
- [ ] Run axe scan on each page/flow

### 7. CI Verification
- [ ] All component tests pass
- [ ] Zero critical axe violations
- [ ] All Playwright E2E scenarios pass
- [ ] Bundle size within budget (if configured)

---

Review and approve this plan before beginning implementation. Do not skip layers or reorder steps.
