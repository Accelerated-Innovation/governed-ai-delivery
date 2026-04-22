# Component Rules — Angular

See: `docs/ui/architecture/angular/COMPONENT_CONVENTIONS.md`

Applies to: `src/features/*/components/`, `src/shared/components/`

## Hard Rules (Summary)

- **Standalone only** → no NgModule declarations
- **OnPush detection** → always required
- **No direct API calls** → use query functions (e.g., `injectUserProfile`)
- **No data transformation** → shape data in query functions via `select`
- **No business logic** → conditional rendering only
- **No cross-feature imports** → share via `src/shared/`
- **No direct store writes** → call named actions

Full guidance with code examples: see **Section 8** in `docs/ui/architecture/angular/COMPONENT_CONVENTIONS.md`

## Testing

See: `docs/ui/architecture/angular/COMPONENT_CONVENTIONS.md` **Section 9** for testing requirements.

- Vitest + Angular Testing Utilities
- FIRST principles (Fast, Isolated, Repeatable, Self-Verifying, Timely)
- **Required:** axe-core accessibility checks in every test

## Accessibility

See: `docs/ui/architecture/ACCESSIBILITY_STANDARDS.md` for complete guidance.

- WCAG 2.1 Level AA mandatory
- Every test must include axe-core checks
- Manual screen reader testing required before merge
