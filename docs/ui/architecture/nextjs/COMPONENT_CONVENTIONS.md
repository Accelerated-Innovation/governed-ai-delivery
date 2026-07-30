# Next.js Component Conventions

Components render accessible UI. Business decisions and raw transport logic do
not belong in component files.

---

## 1. Component Roles

### Route composition

`page.tsx` and `layout.tsx` assemble feature components and route boundaries.

### Server presentation

Server Components render data supplied by feature application/API functions
without adding client JavaScript.

### Client interaction

Client Components own the smallest practical interactive subtree.

### Shared primitives

`src/shared/components/` contains truly reusable primitives. Promotion from a
feature requires an ADR when it changes the shared contract.

---

## 2. File and Naming Rules

- Components use PascalCase.
- Client-only files may use a `.client.tsx` suffix when that improves boundary
  visibility.
- Server-only helpers use a `.server.ts` suffix or a server-only module marker.
- Props use explicit interfaces/types; no `any`.
- Callback props begin with `on`; boolean props begin with `is`, `has`, or
  `can`.
- One primary component per file.

---

## 3. Component Boundaries

Components may:

- render pre-shaped data
- choose presentation variants
- emit user intent
- handle interaction state appropriate to the component

Components must not:

- import database or ORM packages
- call the business API outside an approved adapter/hook
- implement pricing, authorization, eligibility, or other domain rules
- reach into another feature's internals
- transform raw backend contracts extensively in JSX

---

## 4. Required Screen States

Every data-bearing surface explicitly handles:

- loading
- empty
- error
- success
- unauthorized/forbidden where applicable
- not-found where applicable
- long/overflowing content
- narrow and wide viewports

The feature `design.md` identifies which references govern each state.

---

## 5. Accessibility

- Use semantic HTML before ARIA.
- All controls have accessible names.
- Keyboard and focus behavior follows platform expectations.
- Images use meaningful alt text or an empty alt for decorative content.
- Dynamic status/error messages are announced appropriately.
- Color is not the only carrier of meaning.
- Motion respects `prefers-reduced-motion`.

See `docs/ui/architecture/ACCESSIBILITY_STANDARDS.md`.

---

## 6. Styling

Use semantic Tailwind utilities backed by the calibrated brand tokens. Avoid
unreviewed arbitrary colors, spacing, shadows, or radii when a token exists.

Do not add a component library without an accepted ADR.

---

## 7. Testing

Test behavior through accessible roles, names, and visible outcomes. Avoid
implementation-detail and broad snapshot tests. Client Components receive
component tests; async Server Component behavior is covered through appropriate
integration or Playwright journeys.
