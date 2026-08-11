# React Testing

Testing follows the MVVM layer boundaries and verifies user-visible behavior,
API integration, accessibility, and architecture constraints. Tooling is
declared in `TECH_STACK.md`; component-test rules and worked examples live in
`COMPONENT_CONVENTIONS.md`.

---

## 1. Test Layers

| Layer | Primary approach |
|---|---|
| Pure functions/mappers | Vitest unit tests |
| API functions (`api/`) | Vitest + MSW with the transport boundary controlled |
| Hooks (`hooks/`) | Vitest `renderHook` + MSW |
| Stores (`store/`) | Vitest unit tests on named actions |
| Components (`components/`) | Vitest + React Testing Library |
| User journeys | Playwright |
| Accessibility | jest-axe (component) + @axe-core/playwright (E2E), plus manual checks for critical interactions |
| Approved visual states | Playwright screenshot comparison |

---

## 2. API Boundary Tests

API-function tests cover:

- request method/path/body/header mapping
- authentication propagation through the shared base client
- success mapping
- validation and authorization failures
- safe unexpected-error mapping
- timeout/cancellation where relevant

Mock at the HTTP boundary with MSW. Do not mock the shared base client
itself — its behavior is part of what these tests protect.

---

## 3. Hook and Store Tests

- Hook tests exercise query/mutation behavior, `select` transformations, and
  error states through `renderHook` with MSW-controlled responses.
- Store tests call named actions and assert resulting state; no component
  rendering required.
- Server state stays in React Query and client state in Zustand — a test
  needing both layers at once usually indicates a boundary violation.

---

## 4. Component Tests

- Query by accessible role, label, or visible text.
- Test behavior, not implementation details.
- Cover keyboard interactions.
- Run axe checks for rendered interactive components.
- Avoid broad snapshots.

See `COMPONENT_CONVENTIONS.md` §Testing for the binding component-test rules
and a worked example.

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

- MVVM boundary rules (no API calls in components, no cross-feature imports,
  no `shared/` → `features/` imports)
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
