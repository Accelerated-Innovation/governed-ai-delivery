# Feature Plan: ui_task_dashboard

---

## Objective

- A task dashboard that displays tasks assigned to the authenticated user, allows filtering by status (All / Open / Done), and supports marking tasks complete with optimistic UI feedback
- Developers and knowledge workers benefit by having a single view of their assigned work without navigating away from the application
- Success: all acceptance scenarios pass; zero critical axe-core violations; LCP ≤ 1.0s; optimistic update confirmed by test; FIRST average ≥ 4.0

---

## Scope Boundaries

### In scope
- Task list view with status filter (All / Open / Done)
- Mark task complete with optimistic update and cache invalidation
- Accessible task count badge with aria-label
- aria-live region for status change announcements
- Loading skeleton, error state, and background refetch indicator
- Component tests (FIRST compliant, jest-axe)
- Playwright E2E tests for all `@e2e` scenarios with axe scan per flow

### Out of scope
- Task creation, editing, or deletion (separate feature)
- Task assignment or reassignment
- Due date management or sorting
- Push notifications or real-time WebSocket updates (polling only)
- Pagination (deferred — task count assumed manageable for initial increment)

### Assumptions
- `GET /api/tasks?assignee=me` and `PATCH /api/tasks/{id}` are available and stable
- Authentication is handled by the shared API service (auth token injected via interceptor)
- Design system provides base button, badge, and tab components, or they are built feature-local

---

## Architecture Alignment

### Relevant contracts
- `docs/ui/architecture/MVVM_CONTRACT.md`: vertical slice structure; layer ownership; boundary rules
- `docs/ui/architecture/react/COMPONENT_CONVENTIONS.md`: functional components; custom hook consumption; no API in components
- `docs/ui/architecture/react/STATE_MANAGEMENT.md`: React Query for server state; Zustand for filter client state; optimistic update pattern
- `docs/ui/evaluation/eval_criteria.md`: FIRST principles; WCAG 2.1 AA; E2E coverage

### ADRs
- New ADRs required: none
- Existing ADRs referenced: none — all patterns are established by existing contracts

---

## MVVM Breakdown

### Components (View)

| Component | Location | Props Summary |
|---|---|---|
| `TaskDashboard` | `src/features/task-dashboard/components/` | none — composes all child components |
| `TaskList` | `src/features/task-dashboard/components/` | `tasks: TaskViewModel[]`, `onMarkComplete: (id) => void` |
| `TaskCard` | `src/features/task-dashboard/components/` | `task: TaskViewModel`, `onMarkComplete: (id) => void` |
| `TaskFilter` | `src/features/task-dashboard/components/` | `value: FilterValue`, `onChange: (v) => void` |
| `TaskStatusBadge` | `src/features/task-dashboard/components/` | `count: number` |
| `TaskErrorState` | `src/features/task-dashboard/components/` | `onRetry: () => void` |
| `TaskSkeleton` | `src/features/task-dashboard/components/` | none |

### Query Layer (ViewModel — Server State)

| Hook | Query Key | API Endpoint | ViewModel Shape |
|---|---|---|---|
| `useTaskList` | `['tasks', { assignee: 'me' }]` | `GET /api/tasks?assignee=me` | `TaskViewModel[]` via `select` transform |
| `useMarkTaskComplete` | — (mutation) | `PATCH /api/tasks/{id}` | optimistic update on `['tasks']` cache |

### Store (ViewModel — Client State)

Zustand store — `useTaskDashboardStore`:

```ts
interface TaskDashboardStore {
  filter: 'all' | 'open' | 'done'
  setFilter: (filter: TaskDashboardStore['filter']) => void
}
```

Purpose: filter selection persists within the session without a page reload. Server data (task list) is never stored here — it lives in the React Query cache only.

### API Functions (Model)

| Function | Endpoint | Method | Request | Response |
|---|---|---|---|---|
| `fetchTasks` | `/api/tasks?assignee=me` | GET | — | `TaskResponse[]` |
| `patchTaskStatus` | `/api/tasks/{id}` | PATCH | `{ status: 'done' }` | `TaskResponse` |

All functions use the shared `apiService` (see `docs/ui/architecture/react/TECH_STACK.md`). No bare `fetch()` calls.

---

## Backend Contract Dependencies

| Endpoint | Status | Blocker |
|---|---|---|
| `GET /api/tasks` | Available | No |
| `PATCH /api/tasks/{id}` | Available | No |

---

## Increments

### Increment 1: Types, API functions, and query hooks

Implementation follows MVVM layer order: API → ViewModel → View.

**Goal**
- Define all TypeScript types for the feature
- Implement API functions `fetchTasks` and `patchTaskStatus`
- Implement `useTaskList` and `useMarkTaskComplete` hooks

**Deliverables**
- [x] `src/features/task-dashboard/types/index.ts` — `TaskResponse`, `TaskViewModel`, `FilterValue`
- [x] `src/features/task-dashboard/api/tasks.ts` — `fetchTasks`, `patchTaskStatus`
- [x] `src/features/task-dashboard/hooks/useTaskList.ts` — React Query `useQuery`, with `select` transform
- [x] `src/features/task-dashboard/hooks/useMarkTaskComplete.ts` — `useMutation` with optimistic update and cache invalidation
- [x] `src/features/task-dashboard/hooks/query-keys.ts` — typed query key constants
- [x] Component tests for hooks (MSW + Vitest, FIRST compliant)

**Accessibility impact**
- None — no UI rendered in this increment

**Definition of Done**
- API functions typed end-to-end; no `any`
- `useTaskList` select transform maps `TaskResponse` to `TaskViewModel`
- `useMarkTaskComplete` applies optimistic update before mutation resolves and reverts on error
- Hook tests pass; FIRST average ≥ 4.0 for this increment

---

### Increment 2: Zustand store and filter state

**Goal**
- Implement `useTaskDashboardStore` for filter client state

**Deliverables**
- [x] `src/features/task-dashboard/store/useTaskDashboardStore.ts`
- [x] Unit tests for store (FIRST compliant)

**Accessibility impact**
- None — store has no rendered output

**Definition of Done**
- Store initialises with `filter: 'all'`
- `setFilter` updates state correctly
- Store tests isolated — no React rendering required

---

### Increment 3: Components and accessibility

**Goal**
- Implement all View components
- Wire query hooks and Zustand store to components
- Implement loading skeleton, error state, and aria-live region

**Deliverables**
- [x] `TaskDashboard`, `TaskList`, `TaskCard`, `TaskFilter`, `TaskStatusBadge`, `TaskErrorState`, `TaskSkeleton`
- [x] `aria-live="polite"` region in `TaskDashboard` for mutation announcements
- [x] `aria-label` on `TaskStatusBadge` (e.g., `"3 open tasks"`)
- [x] Component tests (React Testing Library + jest-axe, FIRST compliant)
- [x] Playwright E2E tests for all `@e2e` and `@accessibility` scenarios with axe scan per flow

**Accessibility impact**
- `aria-live` region must be present in the DOM on initial render (not conditionally rendered)
- `TaskStatusBadge` must use `aria-label` or visually hidden text — relying on visible text alone is not sufficient
- Focus order must follow DOM order — no CSS-only reordering that breaks keyboard flow
- Touch targets on `TaskCard` buttons must be ≥ 44×44px

**Definition of Done**
- All acceptance criteria satisfied
- Zero critical/serious axe-core violations (jest-axe in component tests; axe scan in Playwright)
- All `@e2e` Playwright tests pass
- FIRST average ≥ 4.0 across all component tests

---

## Accessibility Plan

| Scenario | WCAG Criteria | Test Approach |
|---|---|---|
| Keyboard navigation | 2.1.1 Keyboard | Playwright tab/enter/space flow through filter tabs and task cards |
| Badge announces count | 1.3.1 Info and Relationships | jest-axe in `TaskStatusBadge` test; verify `aria-label` value |
| Status change announced | 4.1.3 Status Messages | React Testing Library `waitFor` on aria-live region content after mutation |
| No critical violations on render | 4.1.2 Name, Role, Value | jest-axe in `TaskDashboard` test + Playwright axe scan on each E2E flow |
| Touch target size | 2.5.5 Target Size | Manual review; enforce ≥ 44px in CSS; flag in code review |

---

## Evaluation Compliance Summary (MANDATORY)

Predicted BEFORE implementation begins. All score and evidence fields are populated.

```yaml
evaluation_prediction:
  first:
    fast:           { score: 5, evidence: "All API calls mocked via MSW; no real network; hook tests use renderHook with QueryClient wrapper — no I/O" }
    isolated:       { score: 5, evidence: "Each hook test creates its own QueryClient; Zustand store reset between tests via act(); no shared state" }
    repeatable:     { score: 5, evidence: "No time-dependent logic; optimistic update tested via mock mutation state, not timers; deterministic MSW handlers" }
    self_verifying: { score: 5, evidence: "All scenarios assert on rendered output, aria attributes, and query cache state; no log-inspection" }
    timely:         { score: 4, evidence: "Tests written per increment before implementation; minor risk on aria-live timing assertions needing waitFor tuning" }
    average: 4.8
  virtues:
    working:   { score: 5, evidence: "All acceptance scenarios covered; loading, error, empty states handled; keyboard navigation and aria-live tested" }
    unique:    { score: 5, evidence: "No duplicated rendering or hook logic; filter pattern is feature-local with clear extraction path if reused" }
    simple:    { score: 4, evidence: "Optimistic update adds minor complexity in useMarkTaskComplete; kept to single hook with clear rollback path" }
    clear:     { score: 5, evidence: "Components named by function (TaskCard, TaskFilter); props interfaces are minimal and typed" }
    easy:      { score: 5, evidence: "Clean MVVM separation; components depend only on hooks; hooks depend only on API functions; no cross-feature imports" }
    developed: { score: 5, evidence: "All components and hooks have tests; all @e2e scenarios have Playwright tests; zero dead code" }
    brief:     { score: 4, evidence: "No speculative abstractions; TaskSkeleton and TaskErrorState are simple single-purpose components" }
    average: 4.71
  accessibility:
    predicted_axe_violations: 0
    wcag_level: AA
  thresholds_met: true
```

If `thresholds_met` is false or predicted FIRST average is below 4.0, revise this plan before implementation begins.

### Refactor Triggers Identified

- Optimistic update logic: if `useMarkTaskComplete` grows beyond 30 lines, extract the optimistic update helper to a shared utility in `src/shared/query/`
- Filter logic: if a second feature requires the same All/Open/Done filter pattern, extract to a shared hook — not until second use
- Component growth: if `TaskDashboard` accumulates more than two query dependencies, evaluate splitting into sub-routes

---

## Risks

- Risk: aria-live region does not announce if it is conditionally rendered after mount
  - Impact: screen reader users do not hear task completion confirmation — WCAG 4.1.3 violation
  - Mitigation: render the `aria-live` container unconditionally in `TaskDashboard` from the first render; populate its content only on mutation success

- Risk: optimistic update reverts visually if the mutation fails mid-animation
  - Impact: jarring UI flash; potential confusion about task state
  - Mitigation: implement rollback in `onError` of `useMutation`; add a component test asserting rollback behavior

- Risk: `PATCH /api/tasks/{id}` endpoint contract changes
  - Impact: mutation silently succeeds but cache is stale
  - Mitigation: assert full `TaskResponse` shape in the `useMarkTaskComplete` tests using typed MSW handlers

---

## Definition of Done (Feature-Level)

- Acceptance criteria satisfied (`acceptance.feature`) — all scenarios automated
- NFRs satisfied (`nfrs.md`) — no TBD entries; all categories covered by tagged Gherkin scenarios
- Evaluation criteria satisfied (`eval_criteria.yaml`) — schema-validated
- FIRST average ≥ 4.0 across all component and hook tests
- Zero critical axe-core violations (jest-axe + Playwright)
- All `@e2e` scenarios have passing Playwright tests with axe scan per flow
- CI gates pass (TypeScript strict, ESLint + jsx-a11y, Vitest, Playwright, eval prediction check)
- No MVVM boundary violations (components do not import API functions directly)
