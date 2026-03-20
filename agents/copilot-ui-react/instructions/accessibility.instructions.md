---
applyTo: "**/*.tsx"
---

All React components must meet WCAG 2.1 Level AA. Zero critical or serious axe-core violations are permitted.

Every `.tsx` file must:

- Make every interactive element keyboard operable
- Provide descriptive `alt` text on all images — empty string only for decorative images
- Associate every form input with a `<label>` — not placeholder text alone
- Provide `aria-label` on every icon button
- Never use color as the sole means of conveying information
- Keep focus visible at all times — do not suppress outline without a replacement
- Trap focus in modal dialogs and return focus on close
- Announce dynamic content updates via `aria-live` where appropriate

Every component test must include:

```typescript
import { axe } from 'jest-axe';

it('has no accessibility violations', async () => {
  const { container } = render(<MyComponent />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

Any intentional WCAG exception requires an ADR.
