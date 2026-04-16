# API Rules — Model Layer

Applies to: `src/features/*/api/`, `src/shared/api/`

## Role

The API layer is the outbound adapter to the backend. It is the only layer that knows about HTTP, endpoints, and request/response shapes.

## Hard Rules

- Plain async functions only — no React, no hooks, no state
- One file per backend resource (e.g., `user.api.ts`, `orders.api.ts`)
- All functions use the shared base client from `src/shared/api/client.ts`
- No raw `fetch` or `axios` calls outside of `src/shared/api/client.ts`
- Request and response types must be explicitly typed — no `any`
- Error handling: let errors propagate — React Query handles error state

## Shared Base Client

`src/shared/api/client.ts` owns:
- Base URL configuration (from environment variables only)
- Auth header injection
- Common error shape normalisation

No feature-level API file may replicate this logic.

## Naming

```typescript
// Functions named as: verb + resource
export async function fetchUserProfile(userId: string): Promise<UserProfileResponse> {}
export async function updateUserProfile(userId: string, payload: UpdateProfilePayload): Promise<UserProfileResponse> {}
export async function deleteUserAccount(userId: string): Promise<void> {}
```

## Environment Variables

- Base URL via `VITE_API_BASE_URL` — never hardcoded
- No secrets in frontend code
