# Component Rules — View Layer

Applies to: `src/features/*/components/`, `src/shared/components/`

## Hard Rules

- Standalone components only — no NgModule declarations
- `ChangeDetectionStrategy.OnPush` — always, no exceptions
- No direct `HttpClient` injection or API service injection in components
- No business logic or data transformation in component class or template
- No imports from another feature's internals
- Use `@if`, `@for`, `@switch` (Angular 17+ control flow) — not `*ngIf`, `*ngFor`
- Always provide `track` by a unique identifier in `@for` — never by `$index` for mutable lists

## Structure

- One component per file
- Template in a separate `.html` file
- Styles in a separate `.css` file
- Signal-based inputs (`input()`, `input.required<T>()`) for new code
- Signal-based outputs (`output<T>()`) for new code

## Testing

- Test every component with Jest + Angular Testing Library
- Query by accessible role, label, or text — not by CSS class or component internals
- No snapshot tests
- All tests must satisfy FIRST principles
- Run jest-axe accessibility check in every component test:

```typescript
it('has no accessibility violations', async () => {
  const { container } = await render(MyComponent, { ... });
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```
