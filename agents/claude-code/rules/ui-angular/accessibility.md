# Accessibility Rules

Applies to: all Angular components

## Standard

WCAG 2.1 Level AA. Non-negotiable. Zero critical or serious axe-core violations permitted.

## Hard Rules

- Every interactive element must be keyboard operable
- Every image must have descriptive `alt` attribute — empty string only for decorative images
- Every form control must have an associated `<label>` — not placeholder text alone
- Every icon button must have `aria-label`
- Color must never be the sole means of conveying information
- Focus must be visible at all times — do not suppress outline without a replacement
- Modal dialogs must trap focus and return focus on close
- Use `aria-live` for dynamic content updates where appropriate

## Angular-Specific

- Use Angular CDK `A11yModule` for focus trapping in dialogs and overlays
- Use Angular CDK `LiveAnnouncer` for programmatic screen reader announcements
- Prefer native HTML elements over ARIA role overrides

## Testing

Every component test must include a jest-axe check:

```typescript
import { axe, toHaveNoViolations } from 'jest-axe';
expect.extend(toHaveNoViolations);

it('has no accessibility violations', async () => {
  const { container } = await render(MyComponent, { ... });
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

Every Playwright E2E test must run an axe scan on each page/flow.

Any intentional WCAG exception requires an ADR.
