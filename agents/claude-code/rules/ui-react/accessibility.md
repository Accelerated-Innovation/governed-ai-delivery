# Accessibility Rules

Applies to: all components

## Standard

WCAG 2.1 Level AA. Non-negotiable. Zero critical axe-core violations permitted.

## Hard Rules

- Every interactive element must be keyboard operable
- Every image must have descriptive `alt` text — empty string only for decorative images
- Every form input must have an associated `<label>` — not placeholder text
- Every icon button must have `aria-label`
- Color must never be the sole means of conveying information
- Focus must be visible at all times — do not suppress outline without a replacement
- Modal dialogs must trap focus and return focus on close
- Dynamic content updates must be announced via `aria-live` where appropriate

## Testing

- Run `@axe-core/react` in development mode
- Run `axe` via `@axe-core/playwright` in every Playwright E2E test
- Every component test must include an axe accessibility check:

```typescript
import { axe } from 'jest-axe';

it('has no accessibility violations', async () => {
  const { container } = render(<MyComponent />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

## ADR Required For

- Any intentional WCAG exception — must document the deviation, reason, and mitigation
