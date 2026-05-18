---
applyTo: "src/**/*.component.ts,src/**/*.component.html"
---

# Component Rules — Angular

See: `docs/ui/architecture/angular/COMPONENT_CONVENTIONS.md`

All components must follow:

1. **Standalone only** → no NgModule declarations
2. **OnPush detection** → always required
3. **No API calls** → use query functions (e.g., `injectUserProfile`)
4. **No data transformation** → shape in query functions via `select`
5. **No business logic** → conditional rendering only
6. **No cross-feature imports** → share via `src/shared/`
7. **Modern syntax** → `@if/@for/@switch`, signal `input()`/`output()`

**Testing:** Vitest + Angular Testing Utilities, query by role/label/text, axe-core in every test

**Accessibility:** WCAG 2.1 Level AA required; see `docs/ui/architecture/ACCESSIBILITY_STANDARDS.md`
