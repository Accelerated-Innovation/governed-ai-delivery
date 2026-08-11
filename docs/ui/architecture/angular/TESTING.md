# Angular Testing

Testing follows the MVVM layer boundaries and verifies user-visible behavior,
API integration, accessibility, and architecture constraints. Tooling is
declared in `TECH_STACK.md`; component-test rules live in
`COMPONENT_CONVENTIONS.md`.

---

## 1. Test Layers

| Layer | Primary approach |
|---|---|
| Pure functions/mappers | Jest unit tests |
| API services (`api/`) | Jest + `HttpClientTestingModule` or MSW |
| Query inject functions | Jest + Angular Testing Library with the HTTP boundary controlled |
| Signal stores | Jest unit tests on named actions/computed signals |
| Components (`components/`) | Jest + Angular Testing Library |
| User journeys | Playwright |
| Accessibility | jest-axe (component) + @axe-core/playwright (E2E), plus manual checks for critical interactions |
| Approved visual states | Playwright screenshot comparison |

---

## 2. API Boundary Tests

API-service tests cover:

- request method/path/body/header mapping
- authentication propagation through the shared `ApiService`
- success mapping
- validation and authorization failures
- safe unexpected-error mapping
- timeout/cancellation where relevant

Mock at the HTTP boundary (`HttpClientTestingModule` or MSW). Do not mock the
shared `ApiService` itself — its behavior is part of what these tests protect.

---

## 3. Query and Store Tests

- Query-function tests exercise fetch/mutation behavior, transformations, and
  error states with HTTP responses controlled at the boundary.
- Signal-store tests call named actions and assert signal/computed values; no
  component rendering required.
- Server state stays in TanStack Query and client state in Signals — a test
  needing both layers at once usually indicates a boundary violation.

---

## 4. Component Tests

- Query by accessible role, label, or visible text.
- Test behavior, not implementation details.
- Cover keyboard interactions, including `OnPush` change-detection paths
  driven through user events rather than manual `detectChanges` calls.
- Run axe checks for rendered interactive components.
- Avoid broad snapshots.

See `COMPONENT_CONVENTIONS.md` §Testing for the binding component-test rules.

---

## 5. Playwright Journeys

Every `@e2e` acceptance scenario maps to a Playwright test. Each critical flow
uses production-like routing and API behavior and covers applicable loading,
empty, error, success, unauthorized, and not-found states.

Run an axe scan on each governed flow and attach useful diagnostics on failure.

---

## 6. Visual Comparisons

Only approved screens/states become golden visual baselines. Tests declare:

- route and state
- viewport and browser project
- theme
- stabilized test data
- masked volatile regions

Generate and compare baselines in the same controlled CI environment. Snapshot
updates require review.

---

## 7. Architecture Checks

CI verifies:

- MVVM boundary rules (no `HttpClient` calls in components, no cross-feature
  imports, no `shared/` → `features/` imports)
- type checking
- linting separately from the production build

---

## 8. Manual Verification

For significant UI changes, record:

- keyboard-only walkthrough
- screen-reader check of the primary flow
- 200% zoom/reflow
- responsive viewports from `design.md`
- light/dark/high-contrast behavior where applicable
