---
applyTo: "**/*.component.ts,**/*.component.html"
---

# Accessibility Rules — Angular

See: `docs/ui/architecture/ACCESSIBILITY_STANDARDS.md`

All Angular components must meet **WCAG 2.1 Level AA** — zero critical axe-core violations permitted.

## Core Requirements

- **Semantic HTML first** — use native elements before ARIA
- **Keyboard operable** — all interactions via Tab, Enter, Space, Arrows, Escape
- **Images** — descriptive alt text (empty only for decorative)
- **Forms** — labels not placeholders; errors via `aria-describedby`
- **Focus** — always visible; never suppress outline without replacement
- **Color** — never the sole information carrier

## Angular-Specific

- Use **Angular CDK `A11yModule`** for focus trapping in dialogs/overlays
- Use **Angular CDK `LiveAnnouncer`** for dynamic screen reader announcements

## Required in Every Test

```typescript
import { render } from '@testing-library/angular';
import { axe } from 'vitest-axe';

it('has no accessibility violations', async () => {
  const { container } = await render(MyComponent);
  expect(await axe(container)).toHaveNoViolations();
});
```

Full guidance: `docs/ui/architecture/ACCESSIBILITY_STANDARDS.md`
