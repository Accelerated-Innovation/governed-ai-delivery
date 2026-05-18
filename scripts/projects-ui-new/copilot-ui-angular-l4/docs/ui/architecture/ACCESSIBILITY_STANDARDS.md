# Accessibility Standards

This document defines accessibility requirements for all UI components.

All components must meet **WCAG 2.1 Level AA** compliance at minimum.

---

## 1. Core Principles

### Perceivable
Information must be presentable to all users regardless of sensory ability.

- **Text alternatives** for all non-text content (images, icons, diagrams)
- **Distinguishable** color and contrast (4.5:1 minimum for text)
- **Adaptable** layout that works at zoom levels and on small screens

### Operable
All interactive elements must be accessible via keyboard, screen reader, and pointer devices.

- **Keyboard accessible** — all interactions must work with Tab, Enter, Space, Arrows
- **Sufficient time** — no content that disappears automatically; if needed, allow user control
- **Seizure prevention** — no flashing content (>3 Hz)
- **Navigable** — clear focus indicators, logical tab order, skip links

### Understandable
Content and interaction must be clear and consistent.

- **Readable** — simple language, defined jargon
- **Predictable** — consistent navigation, no unexpected context changes
- **Input assistance** — labels, error messages, suggestions

### Robust
Content must work with assistive technologies and across browsers.

- **Valid HTML** — semantic markup, proper nesting
- **ARIA** when semantic HTML is insufficient
- **Testing** — validated with axe-core and screen reader testing

---

## 2. Testing Requirements

### Automated Testing (axe-core)

Every component test must run accessibility checks via **axe-core**.

**React:**
```typescript
import { render, screen } from '@testing-library/react';
import axe from 'vitest-axe';

it('has no accessibility violations', async () => {
  const { container } = render(<MyComponent />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

**Angular:**
```typescript
import { render } from '@testing-library/angular';
import axe from 'vitest-axe';

it('has no accessibility violations', async () => {
  const { container } = await render(MyComponent);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

### Manual Testing

Automated tests catch common issues but miss context-specific problems. Require manual verification:

- Test with a screen reader (NVDA, JAWS, VoiceOver)
- Test with keyboard navigation only
- Test at 200% zoom
- Test with browser color contrast checking tools
- Validate tab order and focus indicators

---

## 3. Semantic HTML

Use semantic elements to convey meaning to assistive technologies.

### Landmarks
Structure pages with landmark elements:

```html
<header>...</header>          <!-- Page header, logo, navigation -->
<nav>...</nav>               <!-- Major navigation -->
<main>...</main>             <!-- Primary content -->
<section>...</section>       <!-- Thematic grouping -->
<article>...</article>       <!-- Self-contained content -->
<aside>...</aside>           <!-- Supplementary content -->
<footer>...</footer>         <!-- Page footer -->
```

### Text Structure
Use heading hierarchy properly:

```html
<!-- Good: consistent hierarchy -->
<h1>Page Title</h1>
<h2>Section</h2>
<h3>Subsection</h3>

<!-- Bad: skipped levels -->
<h1>Page Title</h1>
<h3>This skips h2</h3>
```

### Lists
Use semantic list markup:

```html
<!-- Unordered -->
<ul>
  <li>Item 1</li>
  <li>Item 2</li>
</ul>

<!-- Ordered -->
<ol>
  <li>First step</li>
  <li>Second step</li>
</ol>

<!-- Description -->
<dl>
  <dt>Term</dt>
  <dd>Definition</dd>
</dl>
```

### Buttons and Links
Use semantically correct elements:

```html
<!-- Link: navigates -->
<a href="/path">Go to page</a>

<!-- Button: triggers action -->
<button>Submit Form</button>

<!-- Never -->
<div role="button" onclick="...">Wrong</div>
<span onclick="...">Also wrong</span>
```

---

## 4. ARIA (Accessible Rich Internet Applications)

Use ARIA only when semantic HTML is insufficient.

### Rule: HTML First

Prefer semantic HTML over ARIA:

```html
<!-- Good -->
<button>Save</button>
<nav>...</nav>
<h1>Title</h1>

<!-- Bad — using ARIA when HTML works -->
<div role="button">Save</div>
<div role="navigation">...</div>
<div role="heading" aria-level="1">Title</div>
```

### Common ARIA Attributes

When HTML doesn't provide what you need:

```html
<!-- aria-label: provides accessible name -->
<button aria-label="Close menu">×</button>

<!-- aria-labelledby: references heading -->
<div aria-labelledby="dialog-title">
  <h2 id="dialog-title">Confirm Action</h2>
</div>

<!-- aria-describedby: provides description -->
<input aria-describedby="password-hint" />
<p id="password-hint">At least 8 characters</p>

<!-- aria-live: announces dynamic updates -->
<div aria-live="polite">
  2 items added to cart
</div>

<!-- aria-disabled: when native disabled doesn't apply -->
<div role="button" aria-disabled="true">Unavailable</div>
```

### Forbidden ARIA Patterns

- Don't use `role="presentation"` or `aria-hidden="true"` to hide visual content that's important
- Don't use `aria-hidden="true"` on interactive elements
- Don't create redundant ARIA (e.g., `<button aria-label="Button">Button</button>`)
- Don't use ARIA to fix broken HTML — fix the HTML instead

---

## 5. Color and Contrast

### Contrast Ratios

Minimum **4.5:1** for normal text; **3:1** for large text (18pt+).

Use tools:
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- Browser DevTools color contrast inspector
- axe DevTools browser extension

### Never Rely on Color Alone

```html
<!-- Bad — color only conveys meaning -->
<span style="color: red">Error</span>
<span style="color: green">Success</span>

<!-- Good — use text and icons -->
<span>❌ Error</span>
<span>✓ Success</span>
```

### Dark Mode

Maintain contrast in light and dark themes:

```css
@media (prefers-color-scheme: dark) {
  body {
    background-color: #1a1a1a;
    color: #f0f0f0;
    /* Ensure 4.5:1 ratio still holds */
  }
}
```

---

## 6. Keyboard Navigation

### Tab Order

The DOM order determines tab order. Keep it logical:

```html
<!-- Good: logical flow -->
<form>
  <label>Name <input name="name" /></label>
  <label>Email <input name="email" /></label>
  <button>Submit</button>
</form>

<!-- Bad: confusing order via tabindex -->
<input tabindex="2" />
<input tabindex="1" />
<input tabindex="3" />
```

### Focus Indicators

Never remove focus outlines without providing a replacement:

```css
/* Bad */
:focus {
  outline: none;
}

/* Good */
:focus {
  outline: 2px solid #0066cc;
  outline-offset: 2px;
}
```

### Keyboard Interactions

Implement expected keyboard patterns:

```typescript
// React example
const handleKeyDown = (e: React.KeyboardEvent) => {
  if (e.key === 'Enter' || e.key === ' ') {
    onActivate(); // Accept both Enter and Space on buttons
  }
  if (e.key === 'Escape') {
    onClose(); // Standard escape behavior
  }
  if (e.key === 'ArrowDown') {
    selectNext(); // Standard menu navigation
  }
};
```

---

## 7. Forms

### Labels

Every form input must have an associated label:

```html
<!-- Good -->
<label for="email">Email</label>
<input id="email" type="email" />

<!-- Also good — implicit label -->
<label>
  Email
  <input type="email" />
</label>

<!-- Bad — no label -->
<input type="email" placeholder="Email" />
```

### Error Messages

Link errors to inputs via `aria-describedby`:

```html
<!-- Good -->
<label for="password">Password</label>
<input id="password" aria-describedby="pwd-error" />
<p id="pwd-error" role="alert">At least 8 characters required</p>

<!-- Angular example -->
<input [attr.aria-describedby]="hasError ? 'error-message' : null" />
<p id="error-message" *ngIf="hasError" role="alert">{{ error }}</p>
```

### Form Structure

Group related fields with `<fieldset>` and `<legend>`:

```html
<fieldset>
  <legend>Shipping Address</legend>
  <label>Street <input name="street" /></label>
  <label>City <input name="city" /></label>
</fieldset>
```

---

## 8. Images and Icons

### Text Alternatives

Provide meaningful alt text for all images:

```html
<!-- Good: describes content -->
<img src="sunset.jpg" alt="Sunset over the ocean" />

<!-- Bad: unhelpful -->
<img src="sunset.jpg" alt="image" />

<!-- Decorative: empty alt -->
<img src="divider.png" alt="" />
```

### Icon-Only Buttons

Use `aria-label` for icon-only buttons:

```html
<!-- Good -->
<button aria-label="Close">×</button>

<!-- Angular -->
<button [attr.aria-label]="'Close'">×</button>

<!-- React -->
<button aria-label="Close">×</button>
```

### SVG Accessibility

Provide titles and descriptions:

```html
<svg aria-labelledby="title desc">
  <title id="title">User Profile</title>
  <desc id="desc">Shows user information and settings</desc>
  <!-- SVG content -->
</svg>
```

---

## 9. Motion and Animation

### Reduced Motion

Respect `prefers-reduced-motion`:

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

### Autoplay

Never autoplay audio or video without user interaction.

```html
<!-- Bad -->
<video src="intro.mp4" autoplay></video>

<!-- Good -->
<video src="intro.mp4" controls></video>
<button onclick="video.play()">Play Video</button>
```

---

## 10. Common Inaccessible Patterns (Anti-Patterns)

| Pattern | Problem | Solution |
|---------|---------|----------|
| `<div onclick="...">` | Not keyboard accessible | Use `<button>` |
| `<img alt="image">`  | Unhelpful alt text | Describe what image shows |
| `<span style="color:red">` | Color alone conveys meaning | Add icon or text |
| `<div role="listbox">` | Not a real listbox | Use semantic `<select>` or proper list |
| Modal without focus trap | Tab leaves modal | Manage focus within modal |
| Flashing content >3 Hz | Risk of seizure | Limit flash rates |
| Autocomplete on personal data | Privacy risk | Use autocomplete="off" for sensitive fields |
| Keyboard trap | Can't escape interaction | Always allow Escape to exit |

---

## 11. Tools and Resources

### Testing Tools
- **axe-core** — automated accessibility scanning (required in all tests)
- **WAVE** — browser extension for accessibility checks
- **WebAIM Contrast Checker** — verify color contrast
- **Lighthouse** — accessibility audits in DevTools

### Screen Readers (Manual Testing)
- **NVDA** (Windows, free)
- **JAWS** (Windows/Mac, commercial)
- **VoiceOver** (Mac/iOS, built-in)
- **TalkBack** (Android, built-in)

### Guidelines
- [WCAG 2.1](https://www.w3.org/WAI/WCAG21/quickref/) — official web content accessibility guidelines
- [WAI-ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/) — ARIA implementation guide
- [MDN Accessibility](https://developer.mozilla.org/en-US/docs/Web/Accessibility) — comprehensive reference

---

## 12. Definition of Done

A component is accessible when:

- All automated tests pass axe-core checks
- Keyboard navigation works completely (Tab, Enter, Space, Arrows, Escape)
- Headings form a proper hierarchy
- All images have meaningful alt text
- All form inputs have labels
- Color contrast meets 4.5:1 minimum
- Focus indicators are visible
- No content flashes >3 Hz
- Manual screen reader testing confirms behavior
