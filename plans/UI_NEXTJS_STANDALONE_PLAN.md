# Standalone `ui-nextjs` Project Type Plan

> **Status:** Approved source of truth
> **Approved:** 2026-07-26
> **Implementation status:** Complete
> **Scope:** Add a standalone Next.js + Tailwind CSS UI project type without
> merging, overlaying, or overlapping the existing UI project types.

---

## Implementation Record

All ten increments and the acceptance criteria in Section 11 are implemented.
Final verification:

- Full repository suite: `1275 passed, 1 skipped`.
- Standalone apply matrix: 18/18 combinations passed across Claude Code,
  Codex, Copilot, L3/L4/L5, GitHub, and Azure.
- Wheel contents include the new architecture, brand, starter, CI, agent, and
  boundary-check payloads.
- A clean wheel install passed `ui-nextjs` apply, marker isolation, payload
  isolation, `govkit doctor`, `govkit validate`, `govkit init`, and
  `govkit calibrate --non-interactive`.
- Representative boundary tests reject direct database/ORM/SQL access while
  permitting typed backend-API access through Server Components, Route
  Handlers, and Server Actions.

On this Windows host, `C:\Windows\system32\bash.exe` is an inaccessible WSL
launcher. The five Bash-wrapper tests were therefore executed with the
installed Git Bash binary; they pass and are included in the full-suite count
above.

---

## 1. Purpose

GovKit currently supports two standalone UI project types:

- `ui-react` for React + Vite applications
- `ui-angular` for Angular applications

This plan adds a third standalone type:

- `ui-nextjs` for Next.js App Router + Tailwind CSS applications

One `govkit apply` configures one project shape at one target. A Next.js UI is
installed separately from React/Vite, Angular, API, CLI, and data projects. A
full-stack monorepo continues to use one GovKit install per application
subdirectory.

This document is the implementation source of truth. If implementation reveals
a material decision that conflicts with this plan, update and re-approve this
document before proceeding with the conflicting change.

---

## 2. Product Boundary

GovKit installs governance and planning artifacts into an existing project. It
does not generate a runnable Next.js application in this increment.

The `ui-nextjs` payload governs:

- Next.js application structure
- Server and Client Component boundaries
- API access and business-logic boundaries
- Tailwind CSS styling and brand-token usage
- component and state-management conventions
- accessibility
- testing and visual verification
- feature planning and architecture preflight
- CI quality gates
- agent guidance for Claude Code, Codex, and Copilot

The payload does not own:

- backend business logic
- database schemas, migrations, queries, or connectivity
- deployment-platform configuration beyond example CI build/test commands
- generation of application source code
- selection of a component library

---

## 3. Decisions

### D1 - `ui-nextjs` is a standalone project type

The public CLI value is:

```text
--type ui-nextjs
```

It is a sibling of `ui-react` and `ui-angular`, not a stack overlay beneath
`ui-react`.

### D2 - UI types do not use stack overlays

UI framework selection is represented by `options.type`. UI installs do not
populate `marker.stack` and do not use `--stack`.

The following must be enforced:

- `govkit apply --type ui-nextjs --stack <id>` fails with a clear explanation.
- The same rule applies to `ui-react` and `ui-angular`.
- `govkit apply --detect --type <ui-type>` reports stack as not applicable.
- `govkit stack apply <id>` rejects a target whose marker type is any UI type.
- The stack-overlay schema and documentation do not imply that UI types are
  valid overlay targets.

### D3 - Existing UI types remain independent

`ui-react`, `ui-angular`, and `ui-nextjs` must not install one another's
framework-specific architecture docs, rules, or CI files.

Framework-neutral UI contracts may be shared:

- accessibility standards
- UI evaluation contracts and rubrics
- NFR conventions
- ADR template
- brand and visual-reference conventions

### D4 - Next.js uses a server-first App Router architecture

The baseline is:

- current supported Next.js major at implementation time, initially Next.js 16
- React 19
- TypeScript strict mode
- App Router
- Server Components by default
- Client Components only where interaction, client state, lifecycle behavior,
  or browser APIs require them
- Tailwind CSS 4
- ESLint
- Vitest + React Testing Library for supported unit/component tests
- Playwright for end-to-end, accessibility, async Server Component, and
  approved visual-regression coverage

Versions are documented as supported ranges, not unbounded `latest` promises.
The stack document records the reviewed baseline version and review date.

### D5 - Use an API-first layered frontend architecture

Next.js does not require classic MVC or MVVM. `ui-nextjs` therefore uses a
component-oriented, API-first layered architecture.

The conceptual layers are:

| Layer | Typical location | Responsibility |
|---|---|---|
| Delivery/composition | `src/app/` | Routes, layouts, metadata, loading/error boundaries, page composition |
| Presentation | `src/features/<feature>/components/` | Accessible rendering and user interaction |
| UI application | `src/features/<feature>/application/` | UI orchestration, view-data mapping, client hooks, mutation coordination |
| API integration | `src/features/<feature>/api/` | Typed calls to the external business API |
| Shared UI infrastructure | `src/shared/` | HTTP client, auth propagation, shared primitives, accessibility utilities |

The final contract may refine folder names during implementation, but it must
preserve these responsibilities and dependency direction.

### D6 - The UI never accesses a database directly

The required dependency path is:

```text
Browser / Next.js UI
        -> typed API client
        -> backend business API
        -> backend domain/business logic
        -> database
```

The `ui-nextjs` repository must not:

- import a database driver or ORM
- contain database connection strings
- connect to a database from a Server Component
- execute SQL from any UI source file
- own database migrations or schema-management code
- implement authoritative business decisions in the UI
- bypass the backend API to read or mutate business data

Examples of disallowed dependencies include Prisma, Drizzle, Sequelize, Knex,
TypeORM, `pg`, `mysql2`, and `mssql`. The enforcement design must allow the
list to evolve without weakening the default prohibition.

This is a hard project-shape boundary, not an ADR escape hatch. A project that
needs database ownership requires a separately governed backend target.

### D7 - Business logic lives behind an API

The UI may own presentation logic:

- formatting values for display
- mapping API responses into view data
- managing loading, empty, error, and optimistic UI states
- local form feedback
- interaction and navigation state
- coordinating calls to published backend operations

The UI may not own authoritative domain rules such as:

- pricing
- eligibility
- authorization decisions
- inventory or account balances
- workflow approval rules
- durable validation that determines whether a business operation is valid

Client-side validation may improve usability, but the backend API remains
authoritative.

### D8 - Thin Next.js BFF behavior is allowed

Route Handlers and Server Actions may act as a thin backend-for-frontend for:

- session and cookie handling
- secure token forwarding
- calling one or more published backend API operations
- response shaping for the UI
- protocol adaptation
- UI-specific aggregation that does not introduce domain decisions

They must not:

- connect to a database
- become a second business API
- contain authoritative business rules
- expose secrets to Client Components
- call an internal Route Handler from a Server Component when the same backend
  API adapter can be called directly without an extra HTTP hop

### D9 - Tailwind CSS is prescribed; a component library is not

Tailwind CSS 4 is the styling system. The baseline may include lightweight
class-composition utilities, but it does not automatically prescribe
shadcn/ui, Tailwind Plus, Material UI, Chakra, or another component library.

Adding a shared component library remains a project-level ADR decision.

### D10 - Brand guidance is first-class

Every standalone UI install receives an editable project-level brand document:

```text
docs/ui/design/BRAND.md
```

It records:

- semantic colors and contrast expectations
- typography
- logo usage
- imagery and iconography
- spacing, radius, shadow, and density principles
- motion and reduced-motion behavior
- responsive principles
- content voice
- source-of-truth links and asset ownership
- mapping from brand decisions to framework styling tokens

Tailwind-specific token implementation belongs in the Next.js `STYLING.md`
contract; the brand document remains framework-neutral.

### D11 - Feature visual references are structured but initially advisory

New UI features receive:

```text
features/<feature>/design.md
features/<feature>/design/references/
```

`design.md` is scaffolded and reviewed during architecture preflight. It is not
added to the hard L4 five-artifact completeness gate in this increment.

Mockups and screen images are optional. When present, the design brief indexes
each reference by:

- file or stable design link
- screen/route
- viewport
- UI state
- light/dark theme where applicable
- authority: approved, exploratory, or inspiration
- owner and review date

### D12 - Design-reference precedence is explicit

Implementation follows this order of authority:

1. acceptance criteria and NFRs
2. accessibility and security contracts
3. approved architecture decisions
4. project brand document
5. approved feature mockups
6. exploratory mockups
7. inspiration images

Conflicts among authoritative sources block implementation until clarified.
Agents must not silently choose one.

### D13 - Visual regression is opt-in and controlled

Approved screens may become Playwright visual baselines after implementation.
Reference mockups are design inputs, not automatically pixel-exact golden
files.

Visual baselines must:

- be generated in the same controlled environment used by CI
- identify route, state, viewport, browser, and theme
- mask or stabilize volatile content
- be reviewed when intentionally updated

### D14 - Agent parity is mandatory

Claude Code, Codex, and Copilot must receive behaviorally equivalent
`ui-nextjs` guidance. Skill frontmatter parity and payload inventory parity
remain test-enforced.

### D15 - `ui-nextjs` supports the existing UI maturity levels

| Type | L3 | L4 | L5 |
|---|---|---|---|
| `ui-nextjs` | yes | yes | yes |

- L3 installs architecture, agent guidance, shared UI contracts, brand
  guidance, and the appropriate L3 CI gate.
- L4 adds the spec-driven feature workflow and UI evaluation gates.
- L5 adds the existing GenAI-operations material applicable to UI projects,
  matching the current UI maturity model.

---

## 4. Current Findings Addressed by This Plan

| Finding | Impact | Planned response |
|---|---|---|
| UI types are fixed payloads while stack schemas still imply UI overlays may be possible | Confusing product model | Explicitly exclude all UI types from overlays |
| `apply --detect` can report a backend stack for a UI type | Misleading dry-run | Report stack as not applicable for UI |
| Explicit `--stack` is silently ignored for UI apply | User intent is discarded | Fail clearly before writing |
| `stack apply` does not reject a UI target | Framework docs could be mixed into a standalone UI install | Validate marker type before applying |
| React guidance assumes client-SPA React Query MVVM | Incorrect fit for App Router | Create isolated Next.js layered contracts |
| Current React docs contain Tailwind/CSS-module and global-style inconsistencies | Conflicting agent guidance | Keep Next.js styling rules internally consistent |
| UI setup review points at nonexistent `BOUNDARIES.md`, `API_CONVENTIONS.md`, and `TESTING.md` paths | Calibration is unreliable | Build UI-type-specific review checklists |
| UI CI assumes Vite conventions and port 4173 | Next.js build/E2E mismatch | Add dedicated Next.js CI templates |
| No project brand contract exists | Generated UI lacks visual direction | Add editable `BRAND.md` |
| No structured mockup or screen-reference workflow exists | Agents may ignore or over-trust images | Add `design.md` and reference-authority rules |
| Existing UI planning skills do not read stack/type-specific tech or visual inputs consistently | Plans can omit rendering and visual decisions | Update UI skills in parity |
| Existing Codex UI nested rule destinations do not align cleanly with feature-slice paths | Rules may not load where expected | Design valid Next.js `AGENTS.md` hierarchy and test it |

---

## 5. Target Installed Shape

An L4 Codex/GitHub `ui-nextjs` installation should conceptually contain:

```text
AGENTS.md
src/
  AGENTS.md
  app/
    AGENTS.md
  features/
    AGENTS.md
  shared/
    AGENTS.md
docs/
  ui/
    architecture/
      ACCESSIBILITY_STANDARDS.md
      MVVM_CONTRACT.md
      NFRS_CONVENTIONS.md
      ADR/
      nextjs/
        TECH_STACK.md
        APPLICATION_STRUCTURE.md
        API_BOUNDARY.md
        SERVER_CLIENT_BOUNDARIES.md
        COMPONENT_CONVENTIONS.md
        STATE_MANAGEMENT.md
        STYLING.md
        TESTING.md
    design/
      BRAND.md
    evaluation/
governance/
  ui/
features/
ci/
  github/
.govkit/
  marker.json
  skill_context.yaml
```

The exact agent-owned paths differ for Claude Code and Copilot, following their
native loading mechanisms. The architecture and behavioral content must remain
equivalent.

No `docs/ui/architecture/react/` or `docs/ui/architecture/angular/` directory
is installed by `ui-nextjs`.

---

## 6. Architecture Contract Set

### 6.1 `TECH_STACK.md`

Defines:

- reviewed Node.js, Next.js, React, TypeScript, and Tailwind ranges
- App Router and build/runtime assumptions
- approved test and accessibility tools
- HTTP client strategy
- observability boundary
- supported browser baseline
- package-script contract used by CI

### 6.2 `APPLICATION_STRUCTURE.md`

Defines:

- `src/app/` route and layout responsibilities
- vertical feature organization
- shared-code promotion rules
- metadata, loading, error, and not-found placement
- route groups and colocation guidance
- forbidden cross-feature imports

### 6.3 `API_BOUNDARY.md`

Defines:

- API-only business access
- typed request/response contracts
- location of API adapters
- authentication and token-forwarding rules
- backend error mapping
- retry, timeout, and cancellation expectations
- direct-database prohibition
- BFF restrictions
- allowed UI validation versus authoritative backend validation

### 6.4 `SERVER_CLIENT_BOUNDARIES.md`

Defines:

- Server Components as the default
- criteria for adding `"use client"`
- serializable prop boundaries
- server-only and client-only module isolation
- secret handling
- Server Action constraints
- Route Handler constraints
- prevention of unnecessary client-bundle expansion

### 6.5 `COMPONENT_CONVENTIONS.md`

Defines:

- server versus client component naming/placement
- component props and composition
- loading, empty, error, and success states
- accessible semantics
- shared primitive promotion through ADR
- prevention of business logic in components

### 6.6 `STATE_MANAGEMENT.md`

Defines:

- server-fetched data ownership
- client-side query-cache use only where justified
- URL state
- local component state
- form state
- optional client store criteria
- cache invalidation and mutation coordination
- prohibition on duplicating backend data into UI stores

### 6.7 `STYLING.md`

Defines:

- Tailwind CSS 4 integration
- allowed global CSS for Tailwind import, theme variables, resets, and
  narrowly scoped global primitives
- semantic token mapping from `BRAND.md`
- class composition
- responsive conventions
- dark mode
- reduced motion
- accessibility contrast
- prohibition on unreviewed arbitrary design values where semantic tokens
  exist

### 6.8 `TESTING.md`

Defines:

- pure-function and API-adapter unit tests
- supported Client Component tests
- treatment of async Server Components
- Playwright E2E coverage
- axe checks
- visual-regression rules
- API mocking boundaries
- deterministic fixtures and test data

---

## 7. Implementation Increments

Each increment must be independently reviewable and leave the repository tests
green for the behavior implemented so far.

### Increment 1 - Enforce the Standalone UI Boundary

**Goal:** Make the existing product model unambiguous before adding the new
type.

#### Changes

- Add a shared definition or helper for UI project types.
- Reject `--stack` when `--type` is `ui-react`, `ui-angular`, or `ui-nextjs`.
- Make UI detection dry-runs report `stack: (not applicable)`.
- Reject `govkit stack apply` for a target with any UI marker type.
- Remove UI values from the stack-overlay schema's `supported_types` enum.
- Update stack documentation to state overlays apply only to API, CLI, and data
  types.
- Preserve backend/data stack behavior.

#### Tests

- Each UI type rejects explicit `--stack`.
- A UI dry-run does not mention `python-fastapi` or another backend stack as
  selected.
- `stack apply` against a UI marker fails before writing.
- Backend and data stack selection tests remain green.
- Stack-overlay schema rejects UI `supported_types`.

### Increment 2 - Add `ui-nextjs` Type Plumbing

**Goal:** Make `ui-nextjs` a valid, discoverable, marker-backed project type.

#### Changes

- Add `ui-nextjs` to:
  - CLI apply choices
  - all three manifest type choices
  - manifest type variants
  - marker/type-area mappings
  - compatibility validation
  - `govkit list`
  - help text and examples
  - setup/init type prompts
  - relevant schemas and test fixtures
- Add Next.js and Tailwind detection signals for fit reporting and doctor
  checks.
- Do not automatically change an explicitly selected type based on detection.
- Record `options.type = ui-nextjs` and `stack = null`.

#### Tests

- All agents resolve `ui-nextjs` at L3/L4/L5.
- Markers record `ui-nextjs` and no stack.
- Detection recognizes representative Next.js package/config signals.
- Type mismatch diagnostics distinguish Next.js from React/Vite and Angular.

### Increment 3 - Author the Next.js Architecture Payload

**Goal:** Install a complete, internally consistent Next.js contract set.

#### New files

- `docs/ui/architecture/nextjs/TECH_STACK.md`
- `docs/ui/architecture/nextjs/APPLICATION_STRUCTURE.md`
- `docs/ui/architecture/nextjs/API_BOUNDARY.md`
- `docs/ui/architecture/nextjs/SERVER_CLIENT_BOUNDARIES.md`
- `docs/ui/architecture/nextjs/COMPONENT_CONVENTIONS.md`
- `docs/ui/architecture/nextjs/STATE_MANAGEMENT.md`
- `docs/ui/architecture/nextjs/STYLING.md`
- `docs/ui/architecture/nextjs/TESTING.md`

#### Changes

- Update framework-neutral UI contracts where they incorrectly require a
  client-SPA MVVM implementation.
- Preserve the separation goals of MVVM while allowing the Next.js layered
  model defined in D5.
- Ensure every document cites the correct neighboring contracts.
- Add the Next.js directory only to `ui-nextjs` manifest variants.

#### Tests

- `ui-nextjs` installs all Next.js docs.
- It installs no React/Vite or Angular framework directory.
- `ui-react` and `ui-angular` do not install Next.js docs.
- All installed markdown references resolve.

### Increment 4 - Enforce the API and Database Boundary

**Goal:** Turn the approved API-only rule into agent guidance and executable
evidence.

#### Changes

- Add binding rules covering:
  - no ORM/database-driver imports
  - no SQL/database connections
  - business operations through typed APIs
  - Server Actions and Route Handlers as thin API consumers only
  - backend-authoritative validation
- Add a reusable static boundary check for `ui-nextjs`.
- Check at minimum:
  - disallowed dependencies in the UI target's package manifests
  - disallowed database imports under UI source roots
  - SQL or migration files under UI-owned source/migration paths
  - common database connection-string variables in UI runtime configuration
- Keep checks target-scoped for monorepos.
- Avoid scanning docs, vendored dependencies, generated test reports, or a
  sibling backend target.
- Surface actionable file-level failures in CI and/or `govkit doctor`.

#### Tests

- Representative Prisma, Drizzle, `pg`, `mysql2`, and `mssql` imports fail.
- A Server Component calling the shared typed API adapter passes.
- A Server Action calling an API mutation passes.
- A thin Route Handler forwarding to the backend API passes.
- A Route Handler importing an ORM fails.
- A sibling backend project outside the UI target does not contaminate results.

### Increment 5 - Add Agent Guidance in Parity

**Goal:** Make all three supported agents apply the Next.js contracts
automatically and equivalently.

#### Changes

- Add L3/L4/L5 root guidance for `ui-nextjs`.
- Add progressive Next.js guidance:
  - Claude Code through its governed rules/nested instruction layout
  - Codex through valid ancestor `AGENTS.md` placement
  - Copilot through `applyTo`-scoped instruction files
- Cover:
  - route composition
  - Server/Client boundaries
  - API adapters
  - no database access
  - thin BFF restrictions
  - Tailwind/brand usage
  - accessibility and testing
- Update manifests in lockstep.

#### Tests

- Manifest parity passes.
- Skill frontmatter parity passes.
- Every declared source file exists.
- Codex rules are placed at ancestor paths that actually govern intended
  descendants.
- Copilot globs cover `src/app/**`, `src/features/**`, and `src/shared/**`.
- Claude guidance references installed Next.js contracts only.

### Increment 6 - Add Brand and Visual-Reference Artifacts

**Goal:** Give UI development an explicit visual source of truth.

#### New shared file

- `docs/ui/design/BRAND.md`

#### Starter changes

- Add `design.md` to the common UI starter and the Next.js UI starter.
- Add `design/references/README.md` so the directory survives packaging and
  documents supported formats and authority labels.

#### Planning behavior

- Architecture preflight reads `BRAND.md` and feature `design.md`.
- It inventories referenced images when present.
- It records missing screens and states rather than inventing them.
- It halts on conflicts between authoritative artifacts.
- Spec planning carries visual states and responsive expectations into
  increments.
- Implementation planning includes visual verification and approved snapshot
  work.

#### Tests

- All new UI features receive the design brief.
- Absence of mockups is allowed and explicitly represented.
- A design brief with unresolved authoritative conflicts blocks preflight by
  instruction.
- Existing five-artifact validation remains unchanged.

### Increment 7 - Add the Next.js Feature Starter and Skills

**Goal:** Make `govkit init` produce Next.js-aware feature planning artifacts.

#### Changes

- Add `features/starter_ui_nextjs/`.
- Map `ui-nextjs` markers and `--starter ui-nextjs` to that starter.
- Add Next.js prompts for:
  - affected routes and layouts
  - Server/Client Component decisions
  - loading, empty, error, success, unauthorized, and not-found states
  - API contracts and backend availability
  - metadata and navigation
  - caching/revalidation
  - responsive screens and visual references
- Update UI architecture-preflight, spec-planning, and implementation-plan
  skills across all agents.
- Have skills resolve the framework directory from marker type rather than
  reading every UI framework directory.

#### Tests

- `govkit init` under `ui-nextjs` selects `starter_ui_nextjs`.
- React and Angular markers retain their current starter behavior except for
  the shared visual brief.
- Skills cite the Next.js contract set when the marker type is `ui-nextjs`.

### Increment 8 - Add Dedicated Next.js CI

**Goal:** Install CI templates that execute the Next.js quality contract
without Vite assumptions.

#### New templates

GitHub:

- `ci/github/l3-ui-nextjs-quality-gate.yml`
- `ci/github/ui-nextjs-quality-gate.yml`
- `ci/github/ui-nextjs-eval-gate.yml`

Azure:

- `ci/azure/l3-ui-nextjs-quality-gate.yml`
- `ci/azure/ui-nextjs-quality-gate.yml`
- `ci/azure/ui-nextjs-eval-gate.yml`

#### Baseline checks

- dependency installation
- TypeScript type checking
- ESLint as a separate step from `next build`
- API/database boundary check
- unit and supported component tests
- `next build`
- production-like Next.js server startup for Playwright
- Playwright E2E
- axe accessibility checks
- feature evaluation/schema checks at L4/L5
- report/artifact upload
- optional approved visual comparisons

#### Script contract

The architecture docs define a small package-script contract so CI templates do
not depend on private project commands. The initial templates may use npm,
matching existing UI CI conventions, while documenting where teams calibrate a
different package manager.

#### Tests

- CI dispatch selects Next.js templates only for `ui-nextjs`.
- L3 does not receive L4 feature-evaluation gates.
- L4/L5 receive quality and evaluation gates.
- React/Vite and Angular CI dispatch remain isolated.
- Both CI providers have equivalent coverage.

### Increment 9 - Repair UI Setup Review and Calibration

**Goal:** Make the post-install review match the selected standalone UI type.

#### Changes

- Resolve the framework architecture root:
  - `docs/ui/architecture/react`
  - `docs/ui/architecture/angular`
  - `docs/ui/architecture/nextjs`
- Replace backend-oriented UI calibration steps with UI steps:
  - installed type and maturity
  - tech stack
  - application structure
  - component conventions
  - state/data management
  - API boundary
  - styling and brand
  - testing/accessibility
  - agent rules, CI, and skill context
- Do not present a stack assumption for UI types.
- Include `BRAND.md` readiness and the design-reference workflow.

#### Tests

- Every UI checklist path exists in a pristine install.
- No UI checklist references backend-only architecture documents.
- Next.js calibration reports detected Next.js/Tailwind signals.
- Noninteractive calibration emits the corrected paths.

### Increment 10 - Documentation, Migration Notes, and Full Verification

**Goal:** Ship the project type as a coherent documented product feature.

#### Changes

- Update:
  - `README.md`
  - `CLAUDE.md`
  - `cli/stacks/README.md`
  - `docs/MONOREPO_PATTERN.md`
  - `ci/README.md`
  - `features/README.md`
  - `scripts/README.md`
  - relevant schemas and contributor/parity documentation
- Document:
  - `ui-nextjs` is standalone
  - UI types reject `--stack`
  - API-only business access
  - no database access
  - thin BFF allowance and limits
  - brand and reference workflow
  - monorepo example with separate API and UI targets
- Add/update smoke coverage.
- Verify wheel contents include every new payload file.

#### Verification

- Targeted tests for each increment.
- `pytest -k parity`
- agent skill and manifest tests
- schema tests
- full fast test suite
- full E2E test tier before merge
- wheel build/install smoke
- standalone apply matrix:
  - 3 agents
  - L3/L4/L5
  - GitHub/Azure
- `govkit validate`, `govkit doctor`, and
  `govkit calibrate --non-interactive` against representative `ui-nextjs`
  sandboxes.

---

## 8. Backward Compatibility and Migration

### Existing markers

No existing marker uses `ui-nextjs`; the new type is additive.

### Existing `ui-react` and `ui-angular` installs

They remain standalone and retain their framework-specific payloads. Changes
shared across all UI types are limited to:

- corrected UI setup review/calibration behavior
- the new editable brand document
- the visual-design brief in newly initialized features
- explicit rejection of `--stack`, which replaces today's silent ignore

User-edited governed documents continue to receive normal edit protection.

### Full-stack monorepos

The supported pattern remains:

```text
govkit apply --type api       --target apps/api
govkit apply --type ui-nextjs --target apps/web
```

The API target owns business logic and database access. The UI target consumes
the API contract and remains database-free.

---

## 9. Non-Goals

This implementation does not:

- add a `fullstack` project type
- turn Next.js into a backend project type
- scaffold `create-next-app` source code
- choose a deployment platform
- create backend endpoints
- define database schemas
- install a component library
- require Figma or another hosted design tool
- generate mockups automatically
- make `design.md` a hard sixth L4 artifact
- convert React/Vite or Angular into stack overlays
- allow stack swapping among UI frameworks

---

## 10. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Next.js version conventions drift | Record reviewed version/range and date; keep framework details isolated under `nextjs/` |
| BFF code grows into business logic | Binding API boundary, agent rules, preflight review, and executable boundary checks |
| Database scan produces false positives | Target-scope scans; exclude docs, dependencies, reports, and sibling apps; test representative cases |
| Agent payloads drift | Update all three agents in one increment and run parity tests |
| Next.js guidance accidentally leaks into React/Vite | Manifest isolation and negative install tests |
| Binary mockups inflate repositories | Prefer optimized PNG/WebP/SVG; allow stable links with ownership metadata |
| Mockups conflict with accessibility or NFRs | Explicit authority ordering and preflight halt |
| Visual snapshots become flaky | Controlled CI environment, stable fixtures, masking, reviewed updates |
| Adding brand docs surprises existing UI upgrades | Editable headers, setup review explanation, and normal edit protection |

---

## 11. Acceptance Criteria

The plan is complete when all of the following are true:

### Type and isolation

- `govkit apply --type ui-nextjs` works for all agents, maturity levels, and CI
  providers.
- The marker records `type: ui-nextjs` and no stack.
- `ui-nextjs` installs no React/Vite or Angular framework payload.
- React/Vite and Angular installs receive no Next.js framework payload.
- UI types reject `--stack` and `stack apply`.

### Architecture

- Installed guidance uses the API-first layered architecture.
- Server Components are the default.
- Client boundaries are explicit and minimal.
- Route Handlers and Server Actions are limited to thin UI/BFF duties.

### API and database boundary

- Business operations flow through typed backend APIs.
- Direct database dependencies, connections, SQL, and migrations are
  prohibited.
- Static checks demonstrate failure for representative violations.
- A monorepo sibling backend does not create false UI failures.

### Visual development

- Every UI install receives an editable brand document.
- New UI features receive a design brief and reference directory guidance.
- Planning skills read and report visual sources and authority.
- Missing images are allowed; contradictory authoritative inputs block.

### Quality

- Next.js-specific GitHub and Azure CI templates install correctly.
- Tests cover type resolution, isolation, API boundaries, visual artifacts,
  calibration, CI dispatch, parity, and packaging.
- All targeted, parity, full-suite, E2E, and wheel-smoke verification passes.
- Documentation consistently describes `ui-nextjs` as standalone.

---

## 12. Implementation Discipline

- Implement increments in order unless this plan is updated with a documented
  reason.
- Keep all three agent payloads in parity within each increment.
- Do not begin application-source scaffolding as part of this plan.
- Do not weaken the API/database boundary through an ADR or framework
  convenience.
- Preserve unrelated user changes in the worktree.
- After each increment, run its targeted verification before starting the
  next increment.
- Before declaring the feature complete, run the complete acceptance matrix in
  Section 11.

---

## 13. Primary References

- Next.js App Router installation and system requirements:
  <https://nextjs.org/docs/app/getting-started/installation>
- Next.js Server and Client Components:
  <https://nextjs.org/docs/app/getting-started/server-and-client-components>
- Next.js backend-for-frontend guidance:
  <https://nextjs.org/docs/app/guides/backend-for-frontend>
- Next.js testing guidance:
  <https://nextjs.org/docs/app/guides/testing>
- Tailwind CSS with Next.js:
  <https://tailwindcss.com/docs/installation/framework-guides/nextjs>
- Playwright visual comparisons:
  <https://playwright.dev/docs/test-snapshots>
