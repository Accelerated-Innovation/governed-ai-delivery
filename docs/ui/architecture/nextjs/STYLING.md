# Next.js Styling and Brand Tokens

Tailwind CSS 4 implements the visual system recorded in
`docs/ui/design/BRAND.md`.

---

## 1. Global CSS

The application global stylesheet may contain:

- `@import "tailwindcss"`
- semantic theme variables
- font-face declarations
- narrowly scoped resets/base rules
- global focus, selection, and reduced-motion primitives

Feature-specific layouts and appearance do not accumulate in the global
stylesheet.

---

## 2. Semantic Tokens

Map brand decisions to semantic roles such as:

- background/surface/elevated
- foreground/muted
- primary/secondary/accent
- success/warning/danger/info
- border/focus
- spacing/density
- radius
- shadow
- motion duration/easing

Components consume roles, not isolated raw brand swatches. Light and dark
themes preserve the same semantic meaning.

---

## 3. Tailwind Usage

- Prefer standard or semantic utilities.
- Use class composition helpers for conditional variants.
- Keep variant definitions close to reusable components.
- Avoid string-building that prevents Tailwind from detecting classes.
- Avoid arbitrary values when a semantic token exists.
- Do not use inline styles for ordinary layout or brand styling.

Inline styles are acceptable only for genuinely runtime-calculated values that
cannot be represented safely through classes or CSS variables.

---

## 4. Responsive Design

The feature design brief declares required viewports and layout behavior.
Implement mobile/narrow behavior intentionally rather than shrinking a desktop
mockup.

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
`features/<feature>/design/references/` guide implementation according to their
declared authority; they do not override accessibility, security, or NFR
contracts.

---

## 7. Component Libraries

Tailwind CSS does not imply a component library. Introducing one requires an
ADR covering:

- accessibility maturity
- styling/token integration
- server/client compatibility
- bundle impact
- ownership and upgrade policy
