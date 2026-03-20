---
applyTo: "**/hooks/**,**/store/**"
---

Follow the state management rules defined in `docs/ui/architecture/angular/STATE_MANAGEMENT.md`.

All query inject functions in `**/hooks/**` must:

- Use `injectQuery` or `injectMutation` — never call API services directly in components
- Wrap in a named inject function — never expose raw query results
- Transform API responses in the `select` option — never in templates
- Define query keys as typed constants in `query-keys.ts`
- Invalidate relevant query keys on mutation success

All signal stores in `**/store/**` must:

- Use Angular Signals for UI-only state — modal open/close, active tab, pagination
- Never store server data — use TanStack Query cache
- Expose signals as read-only via `.asReadonly()`
- Export named action methods — not raw signal setters
- Never call API services directly

See `docs/ui/architecture/angular/STATE_MANAGEMENT.md` for usage examples.
