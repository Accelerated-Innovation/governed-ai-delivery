---
applyTo: "**/hooks/**,**/store/**"
---

# State Management — React

See: `docs/ui/architecture/react/STATE_MANAGEMENT.md`

## Hooks

Wrap `useQuery`/`useMutation` in named hooks with `select` transforms. Never expose raw query results to components.

## Stores

Use Zustand for UI-only state (modals, tabs, selections). Never store server data — use React Query cache instead.

Full guidance with patterns: `docs/ui/architecture/react/STATE_MANAGEMENT.md`
