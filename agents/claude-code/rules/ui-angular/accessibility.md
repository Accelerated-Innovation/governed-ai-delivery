# Accessibility Rules

See: `docs/ui/architecture/ACCESSIBILITY_STANDARDS.md`

Applies to: all Angular components

## Standard

WCAG 2.1 Level AA. Non-negotiable. Zero critical axe-core violations permitted.

## Quick Reference

- **Semantic HTML first** — use native elements before ARIA
- **Keyboard operable** — Tab, Enter, Space, Arrows, Escape
- **Images** — descriptive alt text (empty only for decorative)
- **Forms** — labels not placeholders; error messages via `aria-describedby`
- **Focus** — always visible; do not suppress outline without replacement
- **Color** — never the sole information carrier
- **Testing** — axe-core in every component test

## Angular-Specific Patterns

- Use **Angular CDK `A11yModule`** for focus trapping in dialogs/overlays
- Use **Angular CDK `LiveAnnouncer`** for dynamic screen reader announcements
- Prefer **native HTML elements** over ARIA role overrides

## Testing (Angular)

Every component test must include axe-core:

```typescript
import { render } from '@testing-library/angular';
import { axe } from 'vitest-axe';

it('has no accessibility violations', async () => {
  const { container } = await render(MyComponent);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

Full guidance: `docs/ui/architecture/ACCESSIBILITY_STANDARDS.md`
