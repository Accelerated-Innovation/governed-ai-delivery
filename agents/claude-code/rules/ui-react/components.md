# Component Rules — View Layer

Applies to: `src/features/*/components/`, `src/shared/components/`

## Hard Rules

- No direct API calls. No `fetch`, `axios`, or `useQuery` at the top of a component file.
- No data transformation. If the shape coming from the hook isn't right for the view, fix the hook.
- No business logic. Conditional rendering based on data is fine. Deriving values from raw API responses is not.
- No imports from another feature's `components/`, `hooks/`, `store/`, or `api/`.
- No direct Zustand store writes from event handlers — call a clearly named action from the store.

## Structure

- One component per file
- Props typed with a local `interface` — not imported from `types/` unless shared
- Default export for the component, named exports for sub-components
- Co-locate styles with the component (CSS modules or styled-components)

## Testing

- Test every component with Vitest + React Testing Library
- Test behaviour, not implementation — query by role, label, or text
- No snapshot tests
- All tests must satisfy FIRST principles (see `docs/ui/evaluation/eval_criteria.md`)
- Run axe-core accessibility check in every component test
