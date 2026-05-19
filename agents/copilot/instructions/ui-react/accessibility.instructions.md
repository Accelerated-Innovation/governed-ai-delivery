---
applyTo: "src/**/*.tsx"
---

# Accessibility Rules — React

See: `docs/ui/architecture/ACCESSIBILITY_STANDARDS.md`

All React components must meet **WCAG 2.1 Level AA** — zero critical axe-core violations permitted.

## Core Requirements

- **Semantic HTML first** — use native elements before ARIA
- **Keyboard operable** — all interactions via Tab, Enter, Space, Arrows, Escape
- **Images** — descriptive alt text (empty only for decorative)
- **Forms** — labels not placeholders; errors via `aria-describedby`
- **Focus** — always visible; never suppress outline without replacement
- **Color** — never the sole information carrier
- **Testing** — axe-core in every component test

## Required in Every Test

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
