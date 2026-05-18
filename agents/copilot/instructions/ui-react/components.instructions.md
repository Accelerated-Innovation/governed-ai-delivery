---
applyTo: "src/**/components/**/*.tsx"
---

# Component Rules — React

See: `docs/ui/architecture/react/COMPONENT_CONVENTIONS.md`

All components must follow:

1. **No API calls** → use custom hooks wrapping React Query
2. **No data transformation** → transform in hooks via `select`
3. **No business logic** → conditional rendering only
4. **No cross-feature imports** → share via `src/shared/`
5. **No direct store writes** → call named actions

**Testing:** Vitest + React Testing Library, query by role/label/text, axe-core in every test

**Accessibility:** WCAG 2.1 Level AA required; see `docs/ui/architecture/ACCESSIBILITY_STANDARDS.md`
