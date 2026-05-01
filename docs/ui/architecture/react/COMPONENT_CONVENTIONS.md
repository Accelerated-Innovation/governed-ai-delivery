# Component Conventions

---

## 1. Component Types

### Feature Components
Live in `src/features/<feature>/components/`. Owned by the feature. Not importable by other features.

### Shared Components
Live in `src/shared/components/`. Truly generic UI primitives (Button, Input, Modal, Badge). Must not import from `features/`. Promoted from feature to shared via ADR.

---

## 2. File Structure

```
MyComponent/
├── MyComponent.tsx         # Component implementation
├── MyComponent.test.tsx    # Component tests
└── MyComponent.module.css  # Styles (if using CSS modules)
```

One component per file. Index barrel files are permitted at the feature components level only.

---

## 3. Props

- All props typed with a local `interface Props {}`
- No prop spreading onto DOM elements unless wrapping a native element
- Required props first, optional props last
- Callback props prefixed with `on` (e.g., `onSubmit`, `onClose`)
- Boolean props prefixed with `is` or `has` (e.g., `isLoading`, `hasError`)

---

## 4. Patterns

### Loading and Error States

Handle in the component that calls the hook — not in the hook itself:

```typescript
function UserProfile({ userId }: Props) {
  const { data, isLoading, isError } = useUserProfile(userId);

  if (isLoading) return <Spinner />;
  if (isError) return <ErrorMessage />;

  return <ProfileCard profile={data} />;
}
```

### Lists

Always provide a stable `key` prop. Never use array index as key for mutable lists.

### Forms

Use React Hook Form. Never manage form state with `useState` per field.

---

## 5. Naming

- Components: PascalCase (`UserProfileCard`)
- Hooks: camelCase prefixed with `use` (`useUserProfile`)
- Stores: camelCase prefixed with `use` (`useFilterStore`)
- API functions: camelCase verb + resource (`fetchUserProfile`, `updateUserProfile`)
- CSS module classes: camelCase (`styles.profileCard`)

---

## 6. Forbidden Patterns

- `any` type — use `unknown` and narrow, or define a proper type
- `useEffect` for data fetching — use React Query
- Direct DOM manipulation — use refs only when no React alternative exists
- Inline styles for layout — use CSS modules or a design token system
- Business logic in JSX — extract to a function or hook

---

## 7. Hard Rules — Boundaries and Dependencies

These rules enforce architecture boundaries and prevent common anti-patterns.

### No Direct API Calls
- **Forbidden:** `fetch`, `axios`, or `useQuery` at the top level of a component file
- **Why:** Data fetching belongs in custom hooks, not components
- **How:** Extract data-fetching logic to `src/features/<feature>/hooks/` and wrap it in a named hook

```typescript
// Bad
export function UserProfile({ userId }: Props) {
  const [user, setUser] = useState(null);
  useEffect(() => {
    fetch(`/api/users/${userId}`)
      .then((r) => r.json())
      .then(setUser);
  }, [userId]);
  return <div>{user?.name}</div>;
}

// Good
export function UserProfile({ userId }: Props) {
  const { data: user } = useUserProfile(userId); // Custom hook
  return <div>{user?.name}</div>;
}
```

### No Data Transformation in Components
- **Forbidden:** Deriving values from raw API responses in the component
- **Why:** Components should work with pre-shaped data; transformation is a ViewModel concern
- **How:** Use the `select` option in React Query hooks to shape data before it reaches the component

```typescript
// Bad — transformation in component
const { data } = useQuery({ queryKey: [...], queryFn: fetchUser });
const fullName = `${data?.firstName} ${data?.lastName}`;

// Good — transformation in hook
const { data: fullName } = useQuery({
  queryKey: [...],
  queryFn: fetchUser,
  select: (data) => `${data.firstName} ${data.lastName}`,
});
```

### No Business Logic
- **Allowed:** Conditional rendering based on data (`isLoading`, `hasError`)
- **Forbidden:** Deriving values, calculating totals, applying business rules
- **How:** Put business logic in domain services or custom hooks; components only render

```typescript
// Bad — business logic in component
function OrderSummary({ items }: Props) {
  const subtotal = items.reduce((sum, item) => sum + item.price * item.qty, 0);
  const tax = subtotal * 0.08;
  const total = subtotal + tax;
  return <div>Total: ${total}</div>;
}

// Good — logic in a hook
function OrderSummary({ items }: Props) {
  const { subtotal, tax, total } = useOrderCalculations(items);
  return <div>Total: ${total}</div>;
}
```

### No Cross-Feature Imports
- **Forbidden:** Importing from another feature's `components/`, `hooks/`, `store/`, or `api/`
- **Why:** Prevents tight coupling and preserves feature boundaries
- **How:** Share types via `src/shared/types/`; share components via `src/shared/components/`; communicate via props or context

```typescript
// Bad
import { UserCard } from "../features/users/components/UserCard";
import { useUserList } from "../features/users/hooks/useUserList";

// Good — use shared components or define local composition
import { Card } from "@shared/components/Card";
```

### No Direct Store Writes
- **Forbidden:** Calling `store.setState` or raw Zustand `set` from event handlers
- **Why:** Makes state transitions implicit and hard to trace
- **How:** Export named actions from the store and call those

```typescript
// Bad
const useFilterStore = create((set) => ({ filter: 'all', set }));
<button onClick={() => useFilterStore.setState({ filter: 'active' })} />

// Good
const useFilterStore = create((set) => ({
  filter: 'all',
  setFilter: (filter) => set({ filter }),
}));
<button onClick={() => useFilterStore.getState().setFilter('active')} />
```

---

## 8. Testing

All components must be tested with **Vitest + React Testing Library**.

### Requirements

- **Test behavior, not implementation** — query by role, label, or accessible text
- **No snapshot tests** — snapshots become stale and don't verify behavior
- **No implementation details** — don't test props passed to child components
- **FIRST principles** — all tests must satisfy Fast, Isolated, Repeatable, Self-Verifying, Timely (see `docs/ui/evaluation/FIRST_SCORING_RUBRIC.md`)
- **Axe accessibility check** — run `axe-core` in every component test to catch WCAG violations

### Example

```typescript
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { UserProfile } from './UserProfile';

describe('UserProfile', () => {
  it('displays user name when data loads', async () => {
    // Arrange
    const user = { id: '1', name: 'Alice' };
    vi.mocked(useUserProfile).mockReturnValue({
      data: user,
      isLoading: false,
    });

    // Act
    const { container } = render(<UserProfile userId="1" />);

    // Assert
    expect(screen.getByText('Alice')).toBeInTheDocument();
    
    // Accessibility check
    const { axe } = await import('vitest-axe');
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('shows loading spinner while data fetches', () => {
    vi.mocked(useUserProfile).mockReturnValue({
      data: undefined,
      isLoading: true,
    });

    render(<UserProfile userId="1" />);
    expect(screen.getByRole('status', { name: /loading/i })).toBeInTheDocument();
  });
});
```
