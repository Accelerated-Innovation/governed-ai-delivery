# Implementation Plan — React UI

You are producing an Implementation Plan for a React UI feature. Read the following before proceeding:

- `features/$ARGUMENTS/plan.md`
- `features/$ARGUMENTS/architecture_preflight.md`
- `docs/ui/architecture/MVVM_CONTRACT.md`
- `docs/ui/architecture/react/STATE_MANAGEMENT.md`

---

Produce an ordered implementation checklist. Sequence must follow MVVM layer order: API → ViewModel → View.

## Implementation Order

### 1. Types and Interfaces
- [ ] Define request/response types in `src/features/<feature>/types/`
- [ ] Define ViewModel types (shaped for component consumption)

### 2. API Layer
- [ ] Create API functions in `src/features/<feature>/api/`
- [ ] Wire to shared base client
- [ ] Write unit tests for API functions (mock fetch/axios at boundary)

### 3. ViewModel — React Query Hooks
- [ ] Define query keys in `queryKeys.ts`
- [ ] Create `useQuery` hooks with `select` transforms
- [ ] Create `useMutation` hooks with cache invalidation
- [ ] Write unit tests for hooks using `renderHook` + MSW

### 4. ViewModel — Zustand Store (if applicable)
- [ ] Define store with typed actions
- [ ] Write unit tests for store actions without rendering

### 5. View — Components
- [ ] Build components bottom-up (leaf components first)
- [ ] Wire to hooks — no direct API calls
- [ ] Write component tests with React Testing Library
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
