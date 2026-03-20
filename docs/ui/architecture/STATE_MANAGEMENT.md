# State Management

This document defines how React Query and Zustand are used together in this project.

---

## 1. React Query — Server State

React Query manages all data that originates from the backend API.

### Query Keys

Define query keys as typed constants in `src/features/<feature>/hooks/queryKeys.ts`:

```typescript
export const userQueryKeys = {
  all: ['users'] as const,
  profile: (id: string) => [...userQueryKeys.all, 'profile', id] as const,
  list: (filters: UserFilters) => [...userQueryKeys.all, 'list', filters] as const,
};
```

### Custom Hooks

Wrap every `useQuery` and `useMutation` in a named custom hook:

```typescript
export function useUserProfile(userId: string) {
  return useQuery({
    queryKey: userQueryKeys.profile(userId),
    queryFn: () => fetchUserProfile(userId),
    select: (data): UserProfileViewModel => ({
      fullName: `${data.firstName} ${data.lastName}`,
      avatarUrl: data.avatar_url,
      joinedAt: new Date(data.created_at),
    }),
  });
}

export function useUpdateUserProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, payload }: UpdateArgs) => updateUserProfile(userId, payload),
    onSuccess: (_, { userId }) => {
      queryClient.invalidateQueries({ queryKey: userQueryKeys.profile(userId) });
    },
  });
}
```

### Rules

- Transform response data in `select` — never in the component
- Always invalidate affected query keys on mutation success
- Use `staleTime` intentionally — default is 0 (always refetch)
- Never store `useQuery` results in `useState`

---

## 2. Zustand — Client State

Zustand manages UI-only state that has no server representation.

### Store Structure

One store per feature. Define state and actions together:

```typescript
interface FilterState {
  activeFilter: 'all' | 'active' | 'archived';
  page: number;
  setFilter: (filter: FilterState['activeFilter']) => void;
  setPage: (page: number) => void;
  reset: () => void;
}

const initialState = { activeFilter: 'all' as const, page: 1 };

export const useFilterStore = create<FilterState>((set) => ({
  ...initialState,
  setFilter: (filter) => set({ activeFilter: filter, page: 1 }),
  setPage: (page) => set({ page }),
  reset: () => set(initialState),
}));
```

### Rules

- Never store server data — use React Query cache
- Never call API functions from a store — use React Query mutations
- Export named actions, not raw `set`
- Reset store state on feature unmount if state should not persist across navigation

---

## 3. Decision Guide

| Scenario | Use |
|---|---|
| Data from API | React Query |
| Modal open/close | Zustand |
| Table sort/filter selection | Zustand or URL params |
| Pagination page | URL params (shareable) or Zustand |
| Form input values | React Hook Form or `useState` |
| Auth token | React Query + `localStorage` (via shared auth adapter) |
| Theme preference | Zustand + `localStorage` |
