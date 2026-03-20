---
description: "Produce an ordered implementation checklist for an Angular UI feature following MVVM layer sequence"
agent: "ask"
---

# Implementation Plan — Angular UI

You are producing an Implementation Plan for an Angular UI feature.

Before proceeding, read:
- `features/<feature_name>/plan.md`
- `features/<feature_name>/architecture_preflight.md`
- `docs/ui/architecture/MVVM_CONTRACT.md`
- `docs/ui/architecture/angular/STATE_MANAGEMENT.md`

Produce an ordered implementation checklist. Sequence: API → ViewModel → View.

## 1. Types and Interfaces
- [ ] Define request/response types in `src/features/<feature>/types/`
- [ ] Define ViewModel types for template consumption

## 2. API Layer
- [ ] Create async functions in `src/features/<feature>/api/`
- [ ] Wire to shared `ApiService`
- [ ] Write unit tests — mock `HttpClient`

## 3. ViewModel — TanStack Query Inject Functions
- [ ] Define query keys in `query-keys.ts`
- [ ] Create `injectQuery` functions with `select` transforms
- [ ] Create `injectMutation` functions with cache invalidation
- [ ] Write tests with `TestBed` + `HttpClientTestingModule`

## 4. ViewModel — Signal Store (if applicable)
- [ ] Define injectable service with private signals and read-only exposure
- [ ] Write unit tests for store actions

## 5. View — Components
- [ ] Build standalone, OnPush components bottom-up
- [ ] Wire to query inject functions — no direct API injection
- [ ] Write tests with Angular Testing Library + jest-axe

## 6. E2E — Playwright
- [ ] Map each `@e2e` Gherkin scenario to a Playwright test
- [ ] Run axe scan on each flow

## 7. CI Verification
- [ ] `tsc --noEmit` passes
- [ ] ESLint (`@angular-eslint`) passes
- [ ] All component tests pass
- [ ] Zero critical axe violations
- [ ] All Playwright E2E scenarios pass

Review and approve before beginning implementation.
