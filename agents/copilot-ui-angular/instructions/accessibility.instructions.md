---
applyTo: "**/*.component.ts,**/*.component.html"
---

All Angular components must meet WCAG 2.1 Level AA. Zero critical or serious axe-core violations are permitted.

Every component must:

- Make every interactive element keyboard operable
- Provide descriptive `alt` on all images — empty string only for decorative images
- Associate every form control with a `<label>` — not placeholder text alone
- Provide `aria-label` on every icon button
- Never use color as the sole means of conveying information
- Keep focus visible — do not suppress outline without a replacement
- Use Angular CDK `A11yModule` for focus trapping in dialogs and overlays
- Use Angular CDK `LiveAnnouncer` for programmatic screen reader announcements

Every component test must include:

```typescript
import { axe, toHaveNoViolations } from 'jest-axe';
expect.extend(toHaveNoViolations);

it('has no accessibility violations', async () => {
  const { container } = await render(MyComponent, { ... });
  expect(await axe(container)).toHaveNoViolations();
});
```

Any intentional WCAG exception requires an ADR.
