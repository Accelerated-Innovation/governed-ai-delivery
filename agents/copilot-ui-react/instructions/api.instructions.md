---
applyTo: "**/api/**"
---

Follow the API layer rules defined in `docs/ui/architecture/MVVM_CONTRACT.md`.

All files in `**/api/**` must:

- Contain plain async functions only — no React, no hooks, no state
- Use the shared base client from `src/shared/api/client.ts` — no raw `fetch` or `axios`
- Type all request parameters and return values explicitly — no `any`
- Name functions as verb + resource: `fetchUserProfile`, `updateUserProfile`, `deleteUserAccount`
- Not contain business logic — transform data in the ViewModel hook, not here
- Let errors propagate — React Query handles error state

The API layer is the outbound adapter to the backend. It is the only layer that knows about HTTP endpoints and request/response shapes.

Base URL must come from `VITE_API_BASE_URL` — never hardcoded.
