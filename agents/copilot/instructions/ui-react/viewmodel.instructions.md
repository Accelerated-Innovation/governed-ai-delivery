---
applyTo: "**/hooks/**,**/store/**"
---

Follow the state management rules defined in `docs/ui/architecture/react/STATE_MANAGEMENT.md`.

All hooks in `**/hooks/**` must:

- Wrap `useQuery` or `useMutation` in a named custom hook — never expose raw query results
- Transform API responses in the `select` option — never in the component
- Define query keys as typed constants in a `queryKeys.ts` file
- Invalidate relevant query keys on mutation success
- Not import from `components/`

All stores in `**/store/**` must:

- Use Zustand for UI-only state — modal open/close, active tab, pagination, selections
- Never store server data — that belongs in React Query cache
- Be scoped to a single feature — no global catch-all store
- Export named typed actions — not raw `set`
- Never call API functions directly — mutations belong in React Query

See `docs/ui/architecture/react/STATE_MANAGEMENT.md` for usage examples.
