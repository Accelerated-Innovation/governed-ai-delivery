---
applyTo: "src/**/api/**"
---

Follow the API layer rules defined in `docs/ui/architecture/MVVM_CONTRACT.md`.

Feature API files in `src/features/*/api/` must:

- Contain plain async functions — no Angular decorators, `inject()` calls, or component lifecycle in feature API files
- Receive the shared `ApiService` as an explicit parameter; do not use `HttpClient` directly in feature API files
- Type all request parameters and return values explicitly — no `any`
- Name functions as verb + resource: `fetchUserProfile`, `updateUserProfile`
- Let errors propagate — TanStack Query handles error state
- Not contain business logic — transform data in the ViewModel, not here

API base URL must come from `environment.apiBaseUrl` — never hardcoded.

The ViewModel captures `ApiService` during injection setup and passes it to API
functions. Never call `inject()` from an API function or deferred query callback.
See `docs/ui/architecture/angular/STATE_MANAGEMENT.md` for the caller pattern.
