# Next.js Feature Slices

- Keep each feature's `application/`, `api/`, `components/`, and `types/`
  cohesive.
- Components render; application code orchestrates; API adapters perform typed
  HTTP calls to backend-owned contracts.
- Do not reach into another feature's internals.
- Server Components are the default; keep client islands minimal.
- Test all user-visible states and accessibility requirements.
- Never substitute direct data access for a missing backend endpoint.
