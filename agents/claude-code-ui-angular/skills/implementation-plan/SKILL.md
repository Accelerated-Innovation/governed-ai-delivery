# Implementation Plan — Angular UI

You are producing an Implementation Plan for an Angular UI feature. Read the following before proceeding:

- `features/$ARGUMENTS/plan.md`
- `features/$ARGUMENTS/architecture_preflight.md`
- `docs/ui/architecture/MVVM_CONTRACT.md`
- `docs/ui/architecture/angular/STATE_MANAGEMENT.md`

---

Produce an ordered implementation checklist. Sequence must follow MVVM layer order: API → ViewModel → View.

## Implementation Order

### 1. Types and Interfaces
- [ ] Define request/response types in `src/features/<feature>/types/`
- [ ] Define ViewModel types shaped for template consumption

### 2. API Layer
- [ ] Create API functions in `src/features/<feature>/api/`
- [ ] Wire to shared `ApiService`
- [ ] Write unit tests — mock HttpClient at the boundary

### 3. ViewModel — TanStack Query Inject Functions
- [ ] Define query keys in `query-keys.ts`
- [ ] Create `injectQuery` functions with `select` transforms
- [ ] Create `injectMutation` functions with cache invalidation
- [ ] Write tests using `TestBed` + `HttpClientTestingModule`

### 4. ViewModel — Signal Store (if applicable)
- [ ] Define injectable service with private signals and public read-only access
- [ ] Write unit tests for store actions with `TestBed`

### 5. View — Components
- [ ] Build components bottom-up (leaf components first)
- [ ] Standalone, `OnPush`, signal inputs/outputs
- [ ] Wire to query inject functions — no direct API injection
- [ ] Write component tests with Angular Testing Library
- [ ] Include jest-axe accessibility check in every test

### 6. E2E — Playwright
- [ ] Map each `@e2e`-tagged Gherkin scenario to a Playwright test
- [ ] Run axe scan on each page/flow

### 7. CI Verification
- [ ] `tsc --noEmit` passes
- [ ] ESLint (`@angular-eslint`) passes
- [ ] All component tests pass
- [ ] Zero critical axe violations
- [ ] All Playwright E2E scenarios pass

---

Review and approve before beginning implementation. Do not skip layers or reorder steps.
