# Next.js Testing

Testing follows the server/client boundary and verifies user-visible behavior,
API integration, accessibility, and architecture constraints.

---

## 1. Test Layers

| Layer | Primary approach |
|---|---|
| Pure functions/mappers | Vitest unit tests |
| API adapters | unit/integration tests with transport boundary controlled |
| Client Components/hooks | Vitest + React Testing Library |
| Synchronous Server Components | focused render tests when supported and valuable |
| Async Server Components/routes | Playwright or production-like integration tests |
| User journeys | Playwright |
| Accessibility | axe plus manual checks for critical interactions |
| Approved visual states | Playwright screenshot comparison |

---

## 2. API Boundary Tests

API-adapter tests cover:

- request method/path/body/header mapping
- authentication propagation
- success mapping
- validation and authorization failures
- safe unexpected-error mapping
- timeout/cancellation where relevant

Mock at the HTTP/adapter boundary. Do not mock database behavior in the UI
project because the UI does not own a database.

---

## 3. Component Tests

- Query by accessible role, label, or visible text.
- Test behavior, not implementation details.
- Cover keyboard interactions.
- Run axe checks for rendered interactive components.
- Avoid broad snapshots.
- Keep server-only modules out of client test bundles.

---

## 4. Playwright Journeys

Every `@e2e` acceptance scenario maps to a Playwright test. Each critical flow
uses production-like routing and API behavior and covers applicable loading,
empty, error, success, unauthorized, and not-found states.

Run an axe scan on each governed flow and attach useful diagnostics on failure.

---

## 5. Visual Comparisons

Only approved screens/states become golden visual baselines. Tests declare:

- route and state
- viewport and browser project
- theme
- stabilized test data
- masked volatile regions

Generate and compare baselines in the same controlled CI environment. Snapshot
updates require review.

---

## 6. Architecture Checks

CI verifies:

- no database/ORM dependencies or imports
- no SQL/migration ownership
- no server-only module imported into client code
- type checking
- linting separately from the production build
- framework payload isolation

---

## 7. Manual Verification

For significant UI changes, record:

- keyboard-only walkthrough
- screen-reader check of the primary flow
- 200% zoom/reflow
- responsive viewports from `design.md`
- light/dark/high-contrast behavior where applicable
