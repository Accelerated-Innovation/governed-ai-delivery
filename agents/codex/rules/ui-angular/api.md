# API Rules — Model Layer

Applies to: `src/features/*/api/`, `src/shared/api/`

## Role

The API layer is the outbound adapter to the backend. It is the only layer that knows about HTTP endpoints and request/response shapes.

## Hard Rules

- Plain async functions — no Angular decorators, `inject()` calls, or component lifecycle in feature API files
- Receive the shared `ApiService` as an explicit parameter; do not use `HttpClient` directly in feature API files
- All request parameters and return types explicitly typed — no `any`
- Name functions as verb + resource: `fetchUserProfile`, `updateUserProfile`
- Let errors propagate — TanStack Query handles error state
- No business logic — transform data in the ViewModel, not here

## Shared ApiService

`src/shared/api/api.service.ts` owns:
- Base URL from `environment.apiBaseUrl` — never hardcoded
- Auth header injection via HTTP interceptor
- Common error shape normalisation

No feature-level API file may replicate this logic.

## Pattern

The ViewModel captures `ApiService` during injection setup and passes it to these
functions. API functions never call `inject()`; query callbacks can run later,
outside Angular’s injection context. See `docs/ui/architecture/angular/STATE_MANAGEMENT.md`.

```typescript
// src/features/user/api/user.api.ts
import { firstValueFrom } from 'rxjs';
import type { ApiService } from '../../../shared/api/api.service';

export async function fetchUserProfile(api: ApiService, userId: string): Promise<UserProfileResponse> {
  return firstValueFrom(api.get<UserProfileResponse>(`/users/${userId}`));
}
```

## Environment Variables

- API base URL via `environment.apiBaseUrl` — configured per environment in `src/environments/`
- No secrets in frontend code
