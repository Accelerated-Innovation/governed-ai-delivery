# State Management Rules — Angular

See: `docs/ui/architecture/angular/STATE_MANAGEMENT.md`

Applies to: `src/features/*/hooks/`, `src/features/*/store/`

## Summary

- **TanStack Angular Query:** All server state, wrapped in `injectQuery`/`injectMutation`, shaped via `select`
- **Signals:** Client UI state only (modals, tabs, selections), never duplicate server data
- **Boundaries:** Query functions don't import from components; stores don't call APIs; functions don't cross features

Full patterns with code examples: `docs/ui/architecture/angular/STATE_MANAGEMENT.md`
