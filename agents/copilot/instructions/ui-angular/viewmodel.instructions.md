---
applyTo: "src/**/hooks/**,src/**/store/**"
---

# State Management — Angular

See: `docs/ui/architecture/angular/STATE_MANAGEMENT.md`

## Query Functions

Wrap `injectQuery`/`injectMutation` in named inject functions with `select` transforms. Never expose raw query results to components.

## Signal Stores

Use Angular Signals for UI-only state (modals, tabs, selections). Expose as read-only. Never store server data — use TanStack Query cache instead.

Full guidance with patterns: `docs/ui/architecture/angular/STATE_MANAGEMENT.md`
