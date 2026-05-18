# Component Rules — React

See: `docs/ui/architecture/react/COMPONENT_CONVENTIONS.md`

Applies to: `src/features/*/components/`, `src/shared/components/`

## Hard Rules (Summary)

- **No direct API calls** → use custom hooks wrapping React Query
- **No data transformation** → transform data in hooks via `select`
- **No business logic** → conditional rendering only, extract logic to hooks
- **No cross-feature imports** → share via `src/shared/`
- **No direct store writes** → call named actions from store

Full guidance with code examples: see **Section 8** in `docs/ui/architecture/react/COMPONENT_CONVENTIONS.md`

## Testing

See: `docs/ui/architecture/react/COMPONENT_CONVENTIONS.md` **Section 8** for testing requirements.

- Vitest + React Testing Library
- FIRST principles (Fast, Isolated, Repeatable, Self-Verifying, Timely)
- **Required:** axe-core accessibility checks in every test

## Accessibility

See: `docs/ui/architecture/ACCESSIBILITY_STANDARDS.md` for complete guidance.

- WCAG 2.1 Level AA mandatory
- Every test must include axe-core checks
- Manual screen reader testing required before merge
