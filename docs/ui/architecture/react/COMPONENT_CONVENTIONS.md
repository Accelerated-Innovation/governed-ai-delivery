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
