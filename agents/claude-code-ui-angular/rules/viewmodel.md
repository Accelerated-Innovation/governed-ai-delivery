# ViewModel Rules — TanStack Angular Query and Signals

Applies to: `src/features/*/hooks/`, `src/features/*/store/`

---

## TanStack Angular Query — Server State

- All server state via TanStack Angular Query — never duplicate into Signals
- Use `injectQuery` and `injectMutation` — wrap in named inject functions per concern
- Transform API responses in `select` — never in templates or components
- Query keys defined as typed constants in `query-keys.ts` per feature
- Mutations must invalidate affected query keys on success

```typescript
// Good — named inject function with select transform
export function injectUserProfile(userId: Signal<string>) {
  return injectQuery(() => ({
    queryKey: userQueryKeys.profile(userId()),
    queryFn: () => fetchUserProfile(userId()),
    select: (data): UserProfileViewModel => ({
      fullName: `${data.first_name} ${data.last_name}`,
    }),
  }));
}

// Bad — raw API response exposed
export function injectUserProfile(userId: Signal<string>) {
  return injectQuery(() => ({
    queryKey: ['user', userId()],
    queryFn: () => fetchUserProfile(userId()),
  }));
}
```

## Angular Signals — Client State

- Signals are for UI-only state: modals, active tab, selections, pagination
- Never store server data in signals — use TanStack Query cache
- Expose signals as read-only via `.asReadonly()`
- Feature-scoped injectable services — avoid `providedIn: 'root'` for feature state
- Never call API services from a signal store

```typescript
// Good — read-only exposure, named actions
@Injectable()
export class FilterStore {
  private readonly _filter = signal<Filter>('all');
  readonly filter = this._filter.asReadonly();
  setFilter(f: Filter): void { this._filter.set(f); }
}

// Bad — mutable signal exposed publicly
export class FilterStore {
  readonly filter = signal<Filter>('all');
}
```

## Boundary Rules

- Query inject functions must not import from `components/`
- Signal stores must not call API services directly
- Query functions from one feature must not be used in another feature
