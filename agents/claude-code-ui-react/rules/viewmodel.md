# ViewModel Rules — React Query and Zustand

Applies to: `src/features/*/hooks/`, `src/features/*/store/`

---

## React Query — Server State

- All server state lives in React Query. Never duplicate server data into Zustand.
- One custom hook per logical data concern (e.g., `useUserProfile`, `useOrderList`)
- Custom hooks wrap `useQuery` or `useMutation` — never expose raw query results to components
- Transform and shape API responses inside the hook's `select` option, not in the component
- Query keys must be defined as constants in a `queryKeys.ts` file per feature
- Mutation hooks must invalidate relevant query keys on success

```typescript
// Good
export function useUserProfile(userId: string) {
  return useQuery({
    queryKey: userQueryKeys.profile(userId),
    queryFn: () => fetchUserProfile(userId),
    select: (data) => mapToViewModel(data),
  });
}

// Bad — raw API response exposed to component
export function useUserProfile(userId: string) {
  return useQuery({ queryKey: ['user', userId], queryFn: () => fetchUserProfile(userId) });
}
```

## Zustand — Client State

- Zustand stores are for UI-only state: modal open/close, active tab, selected items, pagination page
- Never store server data in Zustand — use React Query's cache
- One store per feature — no global catch-all store
- Stores must export typed actions, not raw setters
- Stores must be fully unit testable without rendering a component

```typescript
// Good — named action
const useFilterStore = create<FilterState>((set) => ({
  activeFilter: 'all',
  setFilter: (filter: Filter) => set({ activeFilter: filter }),
}));

// Bad — raw setter exposed
const useFilterStore = create((set) => ({ filter: 'all', set }));
```

## Boundary Rules

- Hooks must not import from `components/`
- Stores must not call API functions directly — mutations belong in React Query
- Hooks from one feature must not import hooks from another feature
