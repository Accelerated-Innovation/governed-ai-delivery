---
applyTo: "**/api/**"
---

Follow the API layer rules defined in `docs/ui/architecture/MVVM_CONTRACT.md`.

All files in `**/api/**` must:

- Contain plain async functions only — no Angular decorators, no DI, no lifecycle hooks
- Use the shared `ApiService` from `src/shared/api/api.service.ts` — no direct `HttpClient` in feature API files
- Type all request parameters and return values explicitly — no `any`
- Name functions as verb + resource: `fetchUserProfile`, `updateUserProfile`
- Let errors propagate — TanStack Query handles error state
- Not contain business logic — transform data in the ViewModel, not here

API base URL must come from `environment.apiBaseUrl` — never hardcoded.
