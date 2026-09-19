---
name: govkit-ui-implementation-plan
description: Generate an ordered UI implementation checklist from a validated plan and preflight. Use when the user asks to draft UI implementation steps or invokes /govkit-ui-implementation-plan.
---

# Implementation Plan — UI

You are producing an Implementation Plan for a UI feature. Determine the feature name from the user's request; if it is not provided, ask before proceeding.

Read the following before proceeding:

- `features/<feature_name>/plan.md`
- `features/<feature_name>/architecture_preflight.md`
- `features/<feature_name>/design.md`
- `docs/ui/architecture/MVVM_CONTRACT.md`
- `docs/ui/architecture/nextjs/` for `ui-nextjs`
- `docs/ui/architecture/*/STATE_MANAGEMENT.md`

---

Produce an ordered implementation checklist. Sequence must follow MVVM layer order: API → ViewModel → View.

For `ui-nextjs`, use: contracts/types → backend API adapter → application use
case/view model → Server Component composition → minimal Client Components.
Never include SQL, database packages, ORM/migration work, connection strings,
or business logic in Next.js server code.

## Behavior contract (skip unless this project has one)

Read `authority` in `.govkit/skill_context.yaml` before anything else. If
`source` is `none` — the default, and where most projects are — **skip this
section entirely**: nothing in it applies, and you should not mention it.

If `source` is `pdg`, this feature's behavior is a **versioned commitment**.
An approved baseline binds its Rules and scenarios to an exact revision, and
what somebody approved is that revision — not the working tree in front of
you, and not your reading of it. The governing rule is the one govkit
installed as `behavior-contract`; it is already loaded, and it is binding.

Before relying on anything in the feature folder:

- Run the `validate-baseline` and `verify-authority` checks exactly as that
  rule specifies them. Both need `--target` and `--baseline`, and
  `verify-authority` also needs `--commitment` — omit it and the answer is
  *not authorized* about the pointer you did not supply, which says nothing
  about your work.
- **Drift means stop.** The spec in front of you is not the one that was
  approved, and everything you plan from it inherits that.
- **Unverified is not permission.** An unreachable graph, or an unset
  `GOVKIT_PDG_URL`, leaves the question unanswered rather than answered yes.

Then change nothing that is committed. A scope change, an exclusion you
inferred, a behavior nobody asked for, or a relaxed threshold is a decision
for a person: name the scenario in conflict and wait. You may still refactor,
and this plan may still evolve, as long as every committed scenario keeps
passing.

## Implementation Order

### 1. Types and Interfaces
- [ ] Define request/response types in `src/features/<feature>/types/`
- [ ] Define ViewModel types (shaped for component consumption)

### 2. API Layer
- [ ] Create API functions in `src/features/<feature>/api/`
- [ ] Wire to shared base client / ApiService
- [ ] Write unit tests for API functions (mock HTTP at boundary)

### 3. ViewModel — Query Hooks / Inject Functions
- [ ] Define query keys in `queryKeys.ts` / `query-keys.ts`
- [ ] Create query hooks with `select` transforms
- [ ] Create mutation hooks with cache invalidation
- [ ] Write unit tests using the framework's test harness + MSW

### 4. ViewModel — Client Store (if applicable)
- [ ] Define store with typed actions (Zustand for React / Signal store for Angular)
- [ ] Write unit tests for store actions without rendering

### 5. View — Components
- [ ] Build components bottom-up (leaf components first)
- [ ] Wire to hooks — no direct API calls
- [ ] No code imported or copied from `design/references/` prototypes —
      references inform; implementation follows the architecture contracts
- [ ] Write component tests (React Testing Library / Angular Testing Library)
- [ ] Run axe accessibility check in each test

### 6. E2E — Playwright
- [ ] Map each `@e2e`-tagged Gherkin scenario to a Playwright test
- [ ] Run axe scan on each page/flow

### 7. CI Verification
- [ ] All component tests pass
- [ ] Zero critical axe violations
- [ ] All Playwright E2E scenarios pass
- [ ] Bundle size within budget (if configured)
- [ ] `govkit doctor --target .` passes the API/database boundary check
- [ ] Approved brand and `design.md` are reflected in every required state
- [ ] Visual regression runs only when explicitly enabled for stable references

---

Review and approve this plan before beginning implementation. Do not skip layers or reorder steps.
