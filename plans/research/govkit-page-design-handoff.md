# Design Handoff — GovKit Product Page

**For:** Design
**From:** Marty (Accelerated Innovation)
**Companion doc:** `govkit-product-page-spec.md` (final copy + Elementor widget per section — the build sheet for the page)
**Build context:** WordPress + Elementor 4.1.1, Poppins, acceleratedinnovation.com brand system
**Page placement:** `/our-solutions/product-accelerators/govkit/`

> **What Design owns here:** 8 branded SVG assets (callouts A–H) + visual QA of the 8-section layout against brand. Copy and widget mapping are already locked in the companion spec — this doc specifies the *visual* side: tokens, asset deliverables, responsive behavior, states, and accessibility.

---

## Overview

A single-scroll, benefit-led product page for **GovKit**, a free open-source toolkit. Eight stacked full-width sections alternating light/dark bands, closing on a full-gradient CTA. Voice and rhythm mirror the existing `/our-solution/` pages (caps eyebrows, two-beat H2s, punchy one-line subheads).

---

## Design tokens

Set these as Elementor Global Colors / Fonts so every widget inherits them. Use **token names** in the asset files, not raw hex.

| Token | Value | Usage |
|-------|-------|-------|
| `color-dark-purple` | `#19004f` | Dark section backgrounds, deep gradient stop, body on light |
| `color-purple` | `#5865e7` | Eyebrows, mid gradient stop, default icon stroke |
| `color-magenta` | `#821db0` | Accent / hover state, notice-box border |
| `color-light-blue` | `#0abeef` | Icons & links **on dark only**, bright gradient stop |
| `color-black` | `#1a1a1a` | Body text on light, code background |
| `color-white` | `#f2f2f2` | Light section background, text on dark |
| `gradient-brand` | `linear-gradient(35deg, #0abeef, #5865e7, #19004f)` | Primary buttons, closing CTA band, asset frames |
| `font-family` | Poppins | All text |
| `font-h1` | Poppins Bold | Hero H1 |
| `font-h2` | Poppins Bold | Section headings |
| `font-eyebrow` | Poppins Medium, all-caps, letter-spacing ~2px | Eyebrow labels |
| `font-body` | Poppins Regular / Light | Body copy |

---

## Section background rhythm

| # | Section | Background | Text |
|---|---------|-----------|------|
| 1 | Hero | `color-dark-purple` + `gradient-brand` accent | white |
| 2 | The problem | `color-white` | black |
| 3 | Core capabilities | `color-dark-purple` | white |
| 4 | Install & quickstart | `color-white` | black |
| 5 | Real examples | `color-dark-purple` | white |
| 6 | Who it's for | `color-white` | black |
| 7 | Open-source credibility | `color-dark-purple` | white |
| 8 | Closing CTA | full `gradient-brand` | white |

---

## Asset deliverables (the design work)

All assets: **SVG-first, transparent background, brand palette only, Poppins.** Provide each as an optimized inline SVG; provide A also as a 1200×630 PNG for OG.

| ID | Asset | Section | Spec | Sizing |
|----|-------|---------|------|--------|
| **A** | Hero badge + OG card | 1 | "GovKit" wordmark + line-art AI agent (hexagon node) enclosed in a contract/boundary frame = *agent inside guardrails*. Frame in `gradient-brand`, white wordmark, `color-magenta` accent dot. | SVG + 1200×630 PNG |
| **B** | "Drift vs. Governed" icon trio | 2 | (1) tangled/forking arrow = drift; (2) checklist/contract page = spec; (3) shield-with-check = CI gate. 2px stroke, `color-purple` default → `color-magenta` hover. | 3× ~48px |
| **C** | Six capability glyphs | 3 | Family set: rules (doc + route bracket); spec contract (page + check + "5" badge); skills (wand/spark on node); CI gate (pipeline + shield); multi-stack (3 layers / hex cluster); GenAI ops (routing fork → LLM node). Consistent corner radius + stroke weight. `color-light-blue`, active `color-magenta`. | 6× ~64px |
| **D** | 4-step flow diagram | 4 | Horizontal: **Install → Apply → Calibrate → Commit**. Rounded chips, white fill, `color-purple` numerals 1–4, connectors in `gradient-brand`. | Full-width SVG; stacks vertical on mobile |
| **E** | Lifecycle ribbon (optional) | 5 | 8 numbered dots: Create folder → Acceptance → NFRs → Preflight → Plan → Review → Implement → Merge, on a gradient track. `color-light-blue` dots, white labels. | Full-width SVG |
| **F** | Maturity-ladder diagram | 6 | 3 ascending rungs **L3 Foundations → L4 Spec-Driven → L5 GenAI Ops**, each wider/taller (additive: L4⊃L3, L5⊃L4). Rung fills step through gradient stops. One-line descriptor each. | SVG; vertical on mobile |
| **G** | Badge strip (optional) | 7 | PyPI version · Python 3.11+ · Apache-2.0 · CI status. Either embed live shields.io or recreate as brand chips (`color-purple` / `color-light-blue`). | Inline row |
| **H** | CTA band motif | 8 | Faint large line-art of the hero "agent-in-contract" hexagon, ~10% white opacity, bottom-right of the gradient band. | SVG overlay |

> **Consistency requirement:** B, C, E, H should read as one icon family — same 2px stroke weight, same corner radius, same join style. Treat A's hexagon-agent motif as the system's hero mark; echo it in H.

---

## Components & states

| Component | Variant | Default | Hover | Focus | Notes |
|-----------|---------|---------|-------|-------|-------|
| Primary button | CTA (Install / Star) | `gradient-brand` fill, white text | brightness +8% or subtle scale 1.02 | visible 2px `color-light-blue` outline, offset 2px | Used in Hero, §4, §7, §8 |
| Secondary button | GitHub / PyPI | transparent, 1px white or `color-light-blue` border, `color-light-blue` text (on dark) / `color-purple` (on light) | border + text → `color-magenta` | same focus ring | — |
| Text link | "Read the docs →", "CHANGELOG →" | `color-light-blue` on dark / `color-purple` on light, underline on hover | underline + `color-magenta` | underline + focus ring | See a11y note on link contrast |
| Icon Box | capability / use-case | icon `color-light-blue` (dark bg) or `color-purple` (light bg) | icon → `color-magenta`, slight lift | — | §3, §6 |
| Notice / callout | calibrate warning (§4) | left border 4px `color-magenta`, tinted bg | — | — | Draws the eye to the non-optional step |
| Code Highlight | bash/gherkin/yaml/text | `color-black` bg, `color-light-blue` accent, mono font | — | scrollable, focusable | Dark theme in all bands |

---

## Responsive behavior

| Breakpoint | Behavior |
|------------|----------|
| Desktop (>1024px) | Full layout. §3 capabilities 3×2 grid; §6 three cards in a row; diagrams D/E/F horizontal. |
| Tablet (768–1024px) | §3 → 2-col grid; §6 → 2 + 1; D/E remain horizontal but reduce label size; hero CTAs stay inline. |
| Mobile (<768px) | All grids → single column; flow diagrams D/E and ladder F stack **vertically**; hero CTA buttons full-width stacked (primary on top); code blocks horizontal-scroll, never shrink font below 14px. |

---

## Edge cases

- **Long headings / i18n:** H1 and H2 must wrap gracefully to 2–3 lines without clipping the gradient band; don't lock heights.
- **Code blocks:** never wrap shell commands — horizontal scroll within the Code Highlight widget instead, so commands stay copy-paste accurate.
- **Badge strip (G):** if live shields fail to load, fall back to static brand chips; don't leave broken-image gaps.
- **Missing OG image:** ensure Asset A PNG is set so social shares don't render a blank card.
- **Asset dark/light placement:** Light-blue icons (C) are specified for dark bands only — see accessibility.

---

## Animation / motion (keep restrained, match site)

| Element | Trigger | Animation | Duration | Easing |
|---------|---------|-----------|----------|--------|
| Section content | scroll into view | fade-up 12px | 400ms | ease-out |
| Icon Box | hover | icon color shift + lift 2px | 150ms | ease-out |
| Primary button | hover | brightness +8% | 150ms | ease-out |
| Flow/ladder (D/F) | scroll into view | sequential node reveal (optional) | 300ms stagger | ease-out |

No autoplay, no parallax that fights readability; respect `prefers-reduced-motion` (disable fade/stagger).

---

## Accessibility notes — please action these

1. **Light Blue `#0abeef` is a dark-background-only color.** On white it fails WCAG AA for text (very low contrast). Use it for icons/links **only on `color-dark-purple` bands**; on light bands use `color-purple` or `color-dark-purple` for links/icons.
2. **Purple `#5865e7` eyebrows on white are borderline (~3.9:1).** Either bump eyebrows to `color-dark-purple` on light bands, or keep `color-purple` only at large/bold sizes. Verify before publish.
3. **Gradient buttons + white text:** the bright `#0abeef` end of the gradient can drop white text below 4.5:1. Anchor button text over the mid/dark portion of the gradient, or add a subtle dark overlay behind the label. Confirm contrast on the final button.
4. **Focus order** follows DOM top-to-bottom: skip-link → nav → hero CTAs → section CTAs → footer. All buttons/links keyboard-reachable with a visible focus ring (2px `color-light-blue`, 2px offset).
5. **Icons are decorative** — mark asset SVGs `aria-hidden="true"`; meaning lives in the adjacent text. Diagrams D/E/F that carry information need an `aria-label` or adjacent text alternative (the step names are already in copy).
6. **Code blocks:** ensure they're focusable and the copy-button (if used) has an accessible label.
7. **Touch targets** ≥44×44px on mobile for all buttons and the GitHub/PyPI links.

---

## Open questions for Design

- Do A's hexagon-agent mark and the existing site logo system need to coexist, or is this a page-local motif only?
- Approve optional assets **E** (lifecycle ribbon) and **G** (badge strip), or cut for a leaner page?
- Preference on illustration density — pure line-art (recommended, matches the clean site) vs. filled/gradient-heavy?
