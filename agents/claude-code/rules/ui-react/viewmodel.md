# State Management Rules — React

See: `docs/ui/architecture/react/STATE_MANAGEMENT.md`

Applies to: `src/features/*/hooks/`, `src/features/*/store/`

## Summary

- **React Query:** All server state, wrapped in custom hooks, shaped via `select`
- **Zustand:** Client UI state only (modals, tabs, selections), never duplicate server data
- **Boundaries:** Hooks don't import from components; stores don't call APIs; hooks don't cross features

Full patterns with code examples: `docs/ui/architecture/react/STATE_MANAGEMENT.md`
