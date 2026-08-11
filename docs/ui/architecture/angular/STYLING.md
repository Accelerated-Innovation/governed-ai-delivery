# Angular Styling and Brand Tokens

Component-scoped styles implement the visual system recorded in
`docs/ui/design/BRAND.md`. Brand values live only in that approved contract;
this document defines the mechanism that applies them. Examples use semantic
token names, never literal brand values. Angular carries no Tailwind
mandate — utility frameworks are a per-project ADR decision.

---

## 1. Global Stylesheet

The application has exactly one global stylesheet (`src/styles.css` or the
Angular CLI equivalent). It may contain:

- semantic theme variables (CSS custom properties on `:root` mapping
  `BRAND.md` roles, including dark-theme redefinitions)
- font-face declarations
- narrowly scoped resets/base rules
- global focus, selection, and reduced-motion primitives

Feature-specific layouts and appearance do not accumulate in the global
stylesheet.

---

## 2. Semantic Tokens

Map `BRAND.md` decisions to semantic roles such as:

- background/surface/elevated
- foreground/muted
- primary/secondary/accent
- success/warning/danger/info
- border/focus
- spacing/density
- radius
- shadow
- motion duration/easing

Component styles consume roles through `var(--...)` custom properties, not
isolated raw brand swatches. Light and dark themes preserve the same
semantic meaning.

---

## 3. Component-Scoped Styles

- Every component styles itself through its own stylesheet (`styleUrl`),
  per `COMPONENT_CONVENTIONS.md`; default (emulated) view encapsulation
  stays on.
- Component styles reference semantic custom properties — no hard-coded
  colors, font stacks, spacing values, or shadows that bypass the token
  layer.
- Do not pierce encapsulation: no `::ng-deep`, no global selectors targeting
  another component's internals. Style a child through its documented
  inputs, CSS custom properties, or `::part` where the child exposes parts.
- No inline styles in templates for ordinary layout or brand styling.

Inline styles are acceptable only for genuinely runtime-calculated values
that cannot be represented safely through classes or CSS variables.

---

## 4. Responsive Design

The feature design brief declares required viewports and layout behavior.
Implement mobile/narrow behavior intentionally rather than shrinking a
desktop mockup.

Verify:

- content reflow
- touch target size
- overflow and long text
- navigation transformation
- tables/charts at narrow widths
- zoom to 200%

---

## 5. Accessibility

- Normal text contrast: at least 4.5:1.
- Large text and meaningful non-text UI contrast: at least 3:1 where the
  standard permits.
- Focus indicators are visible in every theme.
- Color never acts as the only signal.
- Motion respects reduced-motion preferences.
- Forced-colors/high-contrast behavior is tested where the audience requires
  it.

---

## 6. Assets and References

Use optimized, licensed assets with documented ownership. Reference images in
`features/<feature>/design/references/` guide implementation according to
their declared authority; they do not override accessibility, security, or
NFR contracts.

---

## 7. Component Libraries

Introducing a component library (for example Angular Material) or a utility
CSS framework requires an ADR covering:

- accessibility maturity
- styling/token integration with the `BRAND.md` semantic roles
- theming and encapsulation fit
- bundle impact
- ownership and upgrade policy
