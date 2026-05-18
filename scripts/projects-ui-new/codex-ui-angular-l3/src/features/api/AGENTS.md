# API Rules — Model Layer

Applies to: `src/features/*/api/`, `src/shared/api/`

## Role

The API layer is the outbound adapter to the backend. It is the only layer that knows about HTTP endpoints and request/response shapes.

## Hard Rules

- Plain async functions — no Angular decorators, no DI, no component lifecycle
- Use the shared `ApiService` from `src/shared/api/api.service.ts` — no direct `HttpClient` injection in feature API files
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

```typescript
// src/features/user/api/user.api.ts
import { inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { ApiService } from '../../../shared/api/api.service';

export async function fetchUserProfile(userId: string): Promise<UserProfileResponse> {
  const api = inject(ApiService);
  return firstValueFrom(api.get<UserProfileResponse>(`/users/${userId}`));
}
```

## Environment Variables

- API base URL via `environment.apiBaseUrl` — configured per environment in `src/environments/`
- No secrets in frontend code
