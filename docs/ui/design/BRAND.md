# Brand and Visual Direction

> govkit:editable

Complete this document before asking an agent to establish or substantially
change the visual language of the application. Replace every `TBD` that affects
the feature being built. This file defines project-wide visual intent; each
feature's `design.md` defines its local application.

## Brand Sources

List the external brand guides, design systems, or style documents used to
complete this contract, by repository-relative path or URL. Brand sources are
advisory inputs — the completed sections below are what bind.

| Source | Location | Notes |
|---|---|---|
| TBD | TBD | TBD |

## Brand Character

- Product or service name: TBD
- Primary audience: TBD
- Desired impression: TBD
- Voice and tone: TBD
- Three traits the interface should express: TBD
- Three traits the interface should avoid: TBD

## Visual Foundation

### Color

Define semantic roles rather than component-specific colors.

| Role | Light value | Dark value | Usage |
|---|---|---|---|
| Canvas | TBD | TBD | Page background |
| Surface | TBD | TBD | Cards and panels |
| Primary | TBD | TBD | Primary actions and emphasis |
| Secondary | TBD | TBD | Supporting actions |
| Text | TBD | TBD | Primary content |
| Muted text | TBD | TBD | Supporting content |
| Border | TBD | TBD | Dividers and controls |
| Success | TBD | TBD | Positive status |
| Warning | TBD | TBD | Caution status |
| Danger | TBD | TBD | Destructive or failed state |
| Focus | TBD | TBD | Keyboard focus indicator |

All color combinations must meet the accessibility standard in
`docs/ui/architecture/ACCESSIBILITY_STANDARDS.md`.

### Typography

- Display typeface: TBD
- Body typeface: TBD
- Monospace typeface: TBD
- Heading character: TBD
- Body character: TBD
- Base size and line height: TBD

### Shape, Spacing, and Depth

- Corner-radius character: TBD
- Spacing density: compact / balanced / spacious / TBD
- Shadow or elevation approach: TBD
- Border treatment: TBD
- Icon style: TBD

### Motion

- Motion character: TBD
- Standard durations and easing: TBD
- Reduced-motion behavior: TBD

## Content and Interaction

- Button and action language: TBD
- Empty-state voice: TBD
- Error-message voice: TBD
- Data-display conventions: TBD
- Destructive-action confirmation: TBD

## Responsive Direction

- Priority screen sizes or device contexts: TBD
- Small-screen navigation approach: TBD
- Content-width strategy: TBD
- Dense-data behavior: TBD

## Approved Assets

List approved logos, icons, illustrations, photography, and their usage rules.
Use repository-relative paths.

| Asset | Path | Allowed use | Restrictions |
|---|---|---|---|
| TBD | TBD | TBD | TBD |

## Reference Authority

Project architecture, accessibility rules, and accepted feature requirements
are binding. `BRAND.md` is binding for visual language after it is completed
and approved. Feature `design.md` files are binding for their feature.
Screenshots, sketches, and mockups in `design/references/` are advisory unless
their feature `design.md` explicitly promotes a named property to a
requirement.

When references conflict, use this order:

1. Accessibility and security requirements
2. Accepted feature behavior and API contracts
3. This approved brand contract
4. The feature's approved `design.md`
5. Reference images and mockups

Record deliberate exceptions in the feature plan.
