# Accessibility Rules

See: `docs/ui/architecture/ACCESSIBILITY_STANDARDS.md`

Applies to: all components

## Standard

WCAG 2.1 Level AA. Non-negotiable. Zero critical axe-core violations permitted.

## Quick Reference

- **Semantic HTML first** — use native elements before ARIA
- **Keyboard operable** — every interactive element must work with Tab, Enter, Space, Arrows, Escape
- **Images** — descriptive alt text (empty only for decorative)
- **Forms** — labels not placeholders; error messages via `aria-describedby`
- **Focus** — always visible; do not suppress outline without replacement
- **Color** — never the sole information carrier
- **Testing** — axe-core in every component test

## Testing (React)

Every component test must include axe-core:

```typescript
import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';

it('has no accessibility violations', async () => {
  const { container } = render(<MyComponent />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

Full guidance: `docs/ui/architecture/ACCESSIBILITY_STANDARDS.md`
