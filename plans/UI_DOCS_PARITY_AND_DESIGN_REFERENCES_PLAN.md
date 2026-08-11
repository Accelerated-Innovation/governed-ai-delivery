# UI Docs Parity and Design References Plan

> **Status:** Approved source of truth
> **Approved:** 2026-08-11
> **Implementation status:** Complete (2026-08-11, branch
> `feat/ui-docs-parity-design-references`)
> **Scope:** Make each per-stack UI architecture doc set (`react`, `angular`,
> `nextjs`) individually fully functional, and extend the feature design
> reference contract to cover interactive prototypes (including
> Claude-generated design files), without changing the advisory status of
> `design.md`.

---

## Implementation Record

All five increments implemented test-first, one commit each:

1. `feat(payload): ship STYLING.md for react and angular UI stacks` — also
   fixed react TECH_STACK's stale governance paths discovered en route.
2. `feat(payload): ship TESTING.md for react and angular UI stacks` — also
   fixed angular COMPONENT_CONVENTIONS naming Vitest/`vi.mocked`/vitest-axe
   against TECH_STACK's declared Jest stack (same read-order contradiction
   class as react's CSS modules), and pointed calibrate's `step.testing` at
   the per-stack TESTING.md for all UI types.
3. `docs(payload): record the intentional nextjs docs asymmetry`.
4. `feat(payload): cover interactive prototypes in the design reference
   contract` — the two starters keep their intentionally different design.md
   shapes, so the consistency tests are semantic (both carry the prototype
   wording and the D4 rule), not byte identity.
5. `feat(doctor): warn when design references and design.md drift (D020)`.

Anti-drift tests live in `tests/test_ui_stack_docs.py` plus additions to
`tests/test_calibrate.py`, `tests/test_agent_skills.py`, and
`tests/test_doctor.py`. Verification: fast loop 2280 passed; e2e tier 134
passed (16 environment skips: JDK-dependent ArchUnit tests); `pytest -k
parity` green; skill bodies byte-identical across agents.

Deviation from §4 as written: the instruction-file doc lists are asserted
as "reachable" (explicit path or a directory-wide "read all files under
docs/ui/architecture/" instruction) because the copilot L4 and all L5
instruction files use the directory-wide form and need no per-file edits.

Observation recorded for a future pass (out of scope here):
`features/ui_task_dashboard/` — a shared worked example for ui-react and
ui-angular at L4 — ships no `design.md` while both starters and the skills
treat it as the sixth UI artifact.

---

## 1. Purpose

Two observations triggered this plan:

1. `docs/ui/architecture/nextjs/` ships 8 documents while `react/` and
   `angular/` ship 3 each. Some of that asymmetry is intentional
   (server-first concerns), some of it is a real gap (styling and testing).
2. The UI skills read `features/<feature>/design.md` and inventory
   `features/<feature>/design/references/`, but the reference contract is
   image-centric (screenshots, sketches, wireframes, mockups). There is no
   convention for interactive prototypes — e.g. an HTML prototype generated
   by Claude, or an exported design-tool file.

This document is the implementation source of truth once approved. If
implementation reveals a material decision that conflicts with this plan,
update and re-approve this document before proceeding.

---

## 2. Current State (verified)

### 2.1 Doc inventory

Shared, installed for every UI type (`governed` list in all three agent
manifests): `MVVM_CONTRACT.md` (including §6 Next.js Layer Mapping),
`ACCESSIBILITY_STANDARDS.md`, `NFRS_CONVENTIONS.md`, `ADR/TEMPLATE.md`,
`docs/ui/design/BRAND.md`, plus `docs/ui/evaluation/` at L4+.

| Document | react | angular | nextjs |
|---|---|---|---|
| TECH_STACK.md | yes | yes | yes |
| COMPONENT_CONVENTIONS.md | yes | yes | yes |
| STATE_MANAGEMENT.md | yes | yes | yes |
| STYLING.md | — | — | yes |
| TESTING.md | — | — | yes |
| APPLICATION_STRUCTURE.md | — | — | yes |
| API_BOUNDARY.md | — | — | yes |
| SERVER_CLIENT_BOUNDARIES.md | — | — | yes |

Manifests install per-stack docs by directory
(`docs/ui/architecture/react/` etc.), so new files in these folders ship
automatically with no manifest change. The per-type rules files
(`claude-md/ui-react.md`, `copilot-instructions/ui-react.md`,
`agents-md/ui-react.md`, and the l4/l5/src variants) list the per-stack docs
**by name** and must be updated in lockstep across all three agents.

### 2.2 Intentional vs. gap

Intentionally nextjs-only (do **not** replicate):

- `API_BOUNDARY.md`, `SERVER_CLIENT_BOUNDARIES.md` — server-first App Router
  concerns with no react/vite or angular equivalent.
- `APPLICATION_STRUCTURE.md` — App Router layout. For react/angular the
  equivalent contract already exists as `MVVM_CONTRACT.md` §3 Feature Slice
  Structure.

Real gaps:

- **Styling.** Angular has no styling guidance anywhere (its TECH_STACK has
  no styling section). React is self-contradictory:
  `react/TECH_STACK.md` §2 mandates Tailwind-only ("No custom global
  stylesheets"), while `react/COMPONENT_CONVENTIONS.md` §2 shows
  `MyComponent.module.css`, §5 names CSS-module class conventions, and §6
  says "use CSS modules or a design token system." Neither stack maps
  `docs/ui/design/BRAND.md` tokens to implementation the way
  `nextjs/STYLING.md` does.
- **Testing.** React/angular testing guidance is scattered across
  TECH_STACK §Testing (tool table) and COMPONENT_CONVENTIONS §Testing
  (component-test rules). Next.js has a dedicated `TESTING.md` covering test
  layers, API-boundary tests, journeys, and visual comparisons. Backend
  stacks also ship a dedicated `TESTING.md` (one of the 6 overlay docs), so
  a per-stack TESTING.md is the established pattern.

### 2.3 Design references and skills (verified behavior)

- `govkit init` for a UI starter scaffolds `design.md` **and**
  `design/references/README.md` (starter copy is recursive).
- All three UI skills read `features/<feature>/design.md`;
  `ui/architecture-preflight` explicitly inventories
  `features/<feature>/design/references/`; `ui/spec-planning` §5.5 requires
  listing "every screenshot/mockup reference."
- References are **advisory** unless `design.md` promotes a named property
  to a requirement. `govkit validate` does not gate `design.md` —
  `tests/test_validate.py::test_ui_nextjs_design_artifact_is_advisory_to_completeness`
  locks this in. This plan does not change that contract.
- The references README names only static artifacts: "screenshots, sketches,
  wireframes, or mockups."

---

## 3. Decisions

| # | Decision | Choice | Rationale |
|---|---|---|---|
| D1 | Parity approach | Targeted gap-fill, not 8-file structural parity | 3 of the 5 nextjs-only docs are server-first concerns; copying them would manufacture artificial parity and contradict the standalone-type design in `UI_NEXTJS_STANDALONE_PLAN.md` |
| D2 | React styling source of truth | Tailwind (per TECH_STACK) — **approved** | TECH_STACK declares the stack; the CSS-module mentions in COMPONENT_CONVENTIONS predate it and are the stale side of the contradiction. Aligns react with nextjs brand-token practice |
| D3 | Prototype storage | Keep a single `design/references/` folder; prototypes are another reference kind | Avoids changing the skills' inventory contract and the starter layout; the `design.md` table's Authority column already carries the semantics |
| D4 | Prototype authority | Advisory by default, same as images; promotion only via `design.md`; prototype **code is never imported, copied, or extended in `src/`** | Prototypes (including Claude-generated HTML) are throwaway design communication. Without an explicit rule, an agent will treat runnable HTML as implementation reference |
| D5 | `design.md` gating | Unchanged (advisory to validate) | Test-locked contract; enforcement pressure comes from skills and the doctor advisory check (Increment 5) |
| D6 | Angular styling posture | Component-scoped styles + BRAND tokens via CSS custom properties; no Tailwind mandate — **approved** | Matches Angular idiom; Tailwind is a react/nextjs stack choice, not a UI-wide one |
| D7 | External brand guides | An external brand guide is a **source input to `BRAND.md`**, never to STYLING.md. STYLING.md carries mechanism only (how tokens are wired per stack), never brand values | `BRAND.md` is the `govkit:editable` project-wide brand contract with a defined authority order; duplicating values into STYLING.md would create a second, ungoverned source of truth |

---

## 4. Increments

Each increment is independently shippable and follows test-first: add or
update the failing payload-consistency/parity tests, then make them pass.
Ruff runs scoped to changed files only.

### Increment 1 — STYLING.md for react and angular; resolve the react contradiction

- Add `docs/ui/architecture/react/STYLING.md`: Tailwind + `clsx`/`tailwind-merge`
  usage, BRAND.md token mapping (CSS custom properties → Tailwind theme),
  dark-mode/reduced-motion posture, what is forbidden (inline layout styles,
  ad-hoc hex values outside the token layer).
- Add `docs/ui/architecture/angular/STYLING.md`: component-scoped styles,
  BRAND.md token mapping via CSS custom properties, same forbidden list
  adapted to Angular.
- Fix `react/COMPONENT_CONVENTIONS.md` §2/§5/§6 to match D2 (remove
  CSS-module file-structure entry and naming rule; point at STYLING.md).
- Both STYLING.md docs state D7 explicitly: `docs/ui/design/BRAND.md` is the
  single source of brand values; STYLING.md examples use semantic token
  names, never literal brand values.
- Add a short "Brand sources" line to the `BRAND.md` template intro: when an
  external brand guide exists, record its location (repo-relative path or
  URL) so agents and reviewers can trace where the completed values came
  from. The external document itself stays advisory — the completed
  `BRAND.md` is what binds, per its existing Reference Authority order.
- Update every rules file that lists the per-stack docs by name, in lockstep
  across `agents/claude-code`, `agents/codex`, `agents/copilot`
  (`ui-react.md`, `ui-angular.md`, their `l4-`/`l5-`/`src-` variants, and
  copilot `instructions/` where applicable).
- Tests: extend the payload tests that pin per-stack doc inventories and
  rules-file doc lists; `pytest -k parity`.

### Increment 2 — TESTING.md for react and angular

- Add `docs/ui/architecture/react/TESTING.md` and
  `docs/ui/architecture/angular/TESTING.md`, structured like
  `nextjs/TESTING.md` (test layers table, API-boundary tests at the HTTP
  adapter, component-test rules, Playwright journeys mapped from `@e2e`
  scenarios, axe integration, visual comparisons) with content sourced from
  the existing TECH_STACK §Testing and COMPONENT_CONVENTIONS §Testing
  sections. Tooling stays exactly what each TECH_STACK already declares.
- Slim COMPONENT_CONVENTIONS §Testing to component-specific rules plus a
  pointer to TESTING.md (no duplicated normative text).
- Update the same rules-file doc lists as Increment 1, all three agents.
- Tests: same suites as Increment 1.

### Increment 3 — record the intentional asymmetry

- Add a repo-side `docs/ui/architecture/README.md` (not installed — the
  manifests' `governed` lists name entries explicitly) stating: which docs
  are shared, which are per-stack, why `API_BOUNDARY.md`,
  `SERVER_CLIENT_BOUNDARIES.md`, and `APPLICATION_STRUCTURE.md` are
  nextjs-only, and that react/angular application structure lives in
  `MVVM_CONTRACT.md` §3. Add a matching note to `CLAUDE.md`'s payload
  section so a future "parity" pass doesn't re-open this.
- Tests: a payload test asserting the README is **not** in any manifest
  `governed`/`files` entry (guards against accidental install).

### Increment 4 — prototypes and Claude-generated design files in the reference contract

- Update the `design.md` template's "Reference Images and Mockups" section
  in **both** `features/starter_ui/` and `features/starter_ui_nextjs/`:
  rename to "Reference Images, Mockups, and Prototypes"; note that the table
  covers interactive prototypes; add the D4 rule verbatim: references are
  advisory, and prototype code is never imported, copied, or extended in
  `src/` — behavior transfers only by promotion in `design.md` and then into
  `acceptance.feature`/`plan.md`.
- Update `design/references/README.md` in both starters: accepted kinds now
  include interactive HTML prototypes (e.g. generated by Claude or another
  AI tool) and design-tool exports; require descriptive filenames and a
  `design.md` table row per retained file; restate advisory-by-default and
  the no-code-reuse rule.
- Update the three UI skills — `spec-planning` (§5.5 "every
  screenshot/mockup/prototype reference"), `architecture-preflight`
  (inventory step names prototypes; advisory wording covers them),
  `implementation-plan` (checklist wording) — **byte-identical frontmatter,
  lockstep bodies across all three agents** (9 SKILL.md files).
- Tests: extend `tests/test_agent_skills.py` (currently asserts `design.md`
  appears in skill text) to assert the prototype wording; add a fixture test
  that the two starters' `design.md` sections and references READMEs stay
  consistent with each other; `pytest -k parity`.

### Increment 5 — doctor advisory check (approved in scope)

- New doctor check (WARN, never FAIL, preserving D5): for each UI feature,
  flag files present under `features/<feature>/design/references/` that are
  not listed in `design.md`'s reference table, and table rows whose file
  does not exist. A real filesystem-vs-content comparison, not a text
  assertion.
- TDD in `tests/test_doctor.py`; respects the existing finding/severity
  model and `govkit doctor` output format.

---

## 5. Explicit non-goals

- No change to `validate`'s 5-artifact completeness contract or design.md's
  advisory status.
- No `APPLICATION_STRUCTURE.md`, `API_BOUNDARY.md`, or
  `SERVER_CLIENT_BOUNDARIES.md` for react/angular.
- No new folder layout under `features/<feature>/design/`.
- No integration with any specific design tool's file format; the contract
  is tool-agnostic (a "Claude Design" HTML export is just a reference file).

---

## 6. Acceptance criteria

1. `react/` and `angular/` each ship `STYLING.md` and `TESTING.md`; the
   react styling contradiction is gone (single source of truth per D2).
2. All rules files listing per-stack docs name the new files, identically
   across the three agents; `pytest -k parity` passes.
3. Both UI starters' `design.md` and `design/references/README.md` name
   prototypes, carry the no-code-reuse rule, and stay mutually consistent.
4. All three UI skills mention prototype references; SKILL.md frontmatter
   remains byte-identical across agents.
5. Full suite (`pytest`) green; `./full_test` green; wheel-smoke unaffected
   (no new top-level asset dirs, so no `force-include` change needed).

---

## 7. Approval record

All three open questions were answered 2026-08-11:

1. **D2** — approved: Tailwind is the react styling source of truth; the
   CSS-module mentions in COMPONENT_CONVENTIONS are removed.
2. **Increment 5** — approved in scope: the doctor advisory check ships as
   part of this plan.
3. **D6** — approved: Angular uses component-scoped styles with BRAND
   tokens; no Tailwind mandate for Angular.

A follow-up question about external brand guides was resolved as **D7**:
brand guides feed `BRAND.md`, not STYLING.md, and Increment 1 adds the
"Brand sources" traceability line to the `BRAND.md` template.
