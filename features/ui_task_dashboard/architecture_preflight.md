# Architecture Preflight: ui_task_dashboard

This document validates MVVM layer alignment, backend contract availability,
accessibility impact, and evaluation readiness before implementation begins.

Preflight is required once per feature and must be updated if scope materially changes.

---

## 1. Artifact Review

Feature folder: `features/ui_task_dashboard/`

- acceptance.feature reviewed: yes
- nfrs.md reviewed: yes — no TBD entries: yes
- eval_criteria.yaml exists: yes
- plan.md exists: yes
- All `@e2e`-tagged Gherkin scenarios have planned Playwright tests: yes
  - View all tasks on load: yes
  - Mark task complete: yes
  - Filter by status: yes
  - API error state: yes
- All `@accessibility`-tagged scenarios have planned axe checks: yes
  - Keyboard navigation: yes (Playwright keyboard flow)
  - Badge accessible label: yes (jest-axe in component test)
  - Live region announcement: yes (jest-axe + aria-live assertion)
  - No critical violations on render: yes (jest-axe + Playwright axe scan)

---

## 2. Standards Referenced

- `docs/ui/architecture/MVVM_CONTRACT.md`: vertical slice structure; layer ownership rules; boundary constraints
- `docs/ui/architecture/react/COMPONENT_CONVENTIONS.md`: functional components, custom hook consumption, no direct API calls in components
- `docs/ui/architecture/react/STATE_MANAGEMENT.md`: React Query for server state; Zustand for client UI state; optimistic update pattern
- `docs/ui/architecture/react/TECH_STACK.md`: shared API service; axios; Vitest + React Testing Library; jest-axe; Playwright
- `docs/ui/evaluation/eval_criteria.md`: FIRST principles for component tests; WCAG 2.1 AA; E2E coverage requirements

---

## 3. MVVM Layer Impact

### View — Components

- New components required:
  - `TaskDashboard` — page-level shell, assembles query/store/filter/list
  - `TaskList` — renders array of `TaskCard` items
  - `TaskCard` — displays task title, status badge, "Mark complete" button
  - `TaskFilter` — All / Open / Done filter tabs
  - `TaskStatusBadge` — open task count with accessible label
  - `TaskErrorState` — error and retry UI for API failures
  - `TaskSkeleton` — loading skeleton for initial fetch
- Shared components required: none — all components are feature-local
- Cross-feature component usage: none

### ViewModel — Query Layer

- Server state needed: yes — React Query (`useQuery`, `useMutation`)
- Query keys required:
  - `['tasks', { assignee: 'me' }]` — task list fetch
  - `['tasks']` — invalidated on successful mutation
- Data transforms required: yes — map API `TaskResponse` to `TaskViewModel` in `select` (derive `isOverdue`, format `dueDate`)
- Mutations required:
  - `markTaskComplete(taskId)` — `PATCH /api/tasks/{id}` with optimistic update; invalidates `['tasks']` on settle

### ViewModel — Store Layer

- Client UI state needed: yes — Zustand
- State shape:
  ```ts
  interface TaskDashboardStore {
    filter: 'all' | 'open' | 'done'
    setFilter: (filter: TaskDashboardStore['filter']) => void
  }
  ```
- Purpose: filter selection persists within the session; kept in client state rather than URL params per NFR

### Model — API Layer

- Backend endpoints consumed:
  - `GET /api/tasks?assignee=me` — fetch authenticated user's tasks
  - `PATCH /api/tasks/{id}` — update task status to `done`
- Endpoint availability: available (existing backend contract — no new endpoints required)
- New endpoints required: no

---

## 4. Backend Contract Analysis

| Endpoint | Method | Exists? | Blocker? |
|---|---|---|---|
| `/api/tasks` | GET | yes | no |
| `/api/tasks/{id}` | PATCH | yes | no |

No backend contract blockers. Implementation can proceed immediately.

Request/response types must be defined in `src/features/task-dashboard/types/` before API functions are written.

---

## 5. Accessibility Impact

- WCAG 2.1 AA requirements for this feature:
  - 2.1.1 Keyboard — all interactive elements (filter tabs, "Mark complete" buttons) reachable via keyboard
  - 1.3.1 Info and Relationships — open task count badge must have a programmatic label
  - 4.1.3 Status Messages — task completion must be announced without moving focus (aria-live)
  - 2.5.5 Target Size — touch targets on task cards must be ≥ 44×44px
  - 1.1.1 Non-text Content — status icons (if used) must have alt text or aria-label
- Complex interaction patterns: none — no modals, dialogs, or custom comboboxes in this feature
- React-specific accessibility concerns: `aria-live="polite"` region for mutation announcements; role and label on badge
- Accessibility risk: Low — standard list with filter tabs; no complex widgets

---

## 6. Evaluation Impact

- Mode: ui
- FIRST enforcement required: yes — minimum average 4.0
- Accessibility threshold achievable: yes — zero critical/serious violations are achievable with correct ARIA usage
- E2E coverage achievable: yes — all four `@e2e` scenarios have straightforward Playwright implementations
- Evaluation risk areas:
  - Optimistic update test: verifying UI state before mutation resolves requires careful MSW timing in hook tests
  - aria-live assertion: must use `waitFor` in React Testing Library to catch async DOM announcements

---

## 7. ADR Determination

ADR required: no

Justification: all architectural decisions for this feature are already covered by existing contracts:
- React Query + Zustand is the established state management stack (no new library introduced)
- Zustand filter state is feature-local (no cross-feature state sharing)
- Both API endpoints are existing contracts (no new backend negotiation required)
- No shared components introduced that would affect other features

---

## 8. Preflight Conclusion

- MVVM alignment: compliant
- Accessibility alignment: compliant
- Evaluation alignment: compliant

Final status: **Approved for planning**
