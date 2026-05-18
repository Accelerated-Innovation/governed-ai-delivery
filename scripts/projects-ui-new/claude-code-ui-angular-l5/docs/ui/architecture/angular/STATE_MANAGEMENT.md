# State Management — Angular

---

## 1. TanStack Angular Query — Server State

TanStack Angular Query manages all data that originates from the backend API. It follows the same mental model as React Query.

### Setup

Provide the query client in `app.config.ts`:

```typescript
import { provideAngularQuery, QueryClient } from '@tanstack/angular-query-experimental';

export const appConfig: ApplicationConfig = {
  providers: [
    provideAngularQuery(new QueryClient()),
  ],
};
```

### Injection-Based Queries

Use `injectQuery` and `injectMutation` inside services or components:

```typescript
// src/features/user/hooks/user.queries.ts
import { inject } from '@angular/core';
import { injectQuery, injectMutation, QueryClient } from '@tanstack/angular-query-experimental';
import { userQueryKeys } from './user.query-keys';
import { fetchUserProfile, updateUserProfile } from '../api/user.api';

export function injectUserProfile(userId: Signal<string>) {
  return injectQuery(() => ({
    queryKey: userQueryKeys.profile(userId()),
    queryFn: () => fetchUserProfile(userId()),
    select: (data): UserProfileViewModel => ({
      fullName: `${data.first_name} ${data.last_name}`,
      avatarUrl: data.avatar_url,
      joinedAt: new Date(data.created_at),
    }),
  }));
}

export function injectUpdateUserProfile() {
  const queryClient = inject(QueryClient);
  return injectMutation(() => ({
    mutationFn: ({ userId, payload }: UpdateArgs) => updateUserProfile(userId, payload),
    onSuccess: (_, { userId }) => {
      queryClient.invalidateQueries({ queryKey: userQueryKeys.profile(userId) });
    },
  }));
}
```

### Query Keys

Define query keys as typed constants in `query-keys.ts` per feature:

```typescript
export const userQueryKeys = {
  all: ['users'] as const,
  profile: (id: string) => [...userQueryKeys.all, 'profile', id] as const,
};
```

### Rules

- Transform response data in `select` — never in the component or template
- Always invalidate affected query keys on mutation success
- Never duplicate server data into a Signal or service property

---

## 2. Angular Signals — Client State

Angular Signals (built-in) manage UI-only state that has no server representation.

### Feature Store Pattern

Create a injectable service per feature using signals:

```typescript
// src/features/user/store/user-filter.store.ts
import { Injectable, signal, computed } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class UserFilterStore {
  private readonly _activeFilter = signal<'all' | 'active' | 'archived'>('all');
  private readonly _page = signal(1);

  readonly activeFilter = this._activeFilter.asReadonly();
  readonly page = this._page.asReadonly();

  setFilter(filter: 'all' | 'active' | 'archived'): void {
    this._activeFilter.set(filter);
    this._page.set(1);
  }

  setPage(page: number): void {
    this._page.set(page);
  }

  reset(): void {
    this._activeFilter.set('all');
    this._page.set(1);
  }
}
```

### Rules

- Never store server data in a Signal store — use TanStack Query cache
- Expose read-only signals publicly via `.asReadonly()`
- Feature-scoped stores — do not use `providedIn: 'root'` for feature-specific state that should not persist globally
- Never call API services directly from a store — mutations belong in TanStack Query

---

## 3. Decision Guide

| Scenario | Use |
|---|---|
| Data from API | TanStack Angular Query |
| Modal open/close | Signal store |
| Table sort/filter | Signal store or query params |
| Pagination page | Query params (shareable) or Signal store |
| Form input values | Angular Reactive Forms |
| Auth token | TanStack Query + `localStorage` |
| Theme preference | Signal store + `localStorage` |
