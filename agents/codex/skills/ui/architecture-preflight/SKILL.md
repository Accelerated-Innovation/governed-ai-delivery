---
name: govkit-ui-architecture-preflight
description: Validate UI architecture boundaries, backend contracts, and ADR need before spec planning. Use when starting a new UI feature or invoking /govkit-ui-architecture-preflight.
---

# Architecture Preflight — UI

You are performing an Architecture Preflight for a UI feature. Determine the feature name from the user's request; if it is not provided, ask before proceeding.

Read the following before proceeding:

Feature specs:
- `features/<feature_name>/nfrs.md`
- `features/<feature_name>/acceptance.feature`
- `features/<feature_name>/eval_criteria.yaml`
- `features/<feature_name>/design.md`

Architecture standards:
- `docs/ui/architecture/MVVM_CONTRACT.md`
- `docs/ui/architecture/nextjs/` when `.govkit/marker.json` has `type: ui-nextjs`
- `docs/ui/architecture/NFRS_CONVENTIONS.md`
- `docs/ui/architecture/*/COMPONENT_CONVENTIONS.md`
- `docs/ui/architecture/*/STATE_MANAGEMENT.md`
- `docs/ui/evaluation/eval_criteria.md`
- `docs/ui/design/BRAND.md`
- All accepted ADRs in `docs/ui/architecture/ADR/`

---

Produce `features/<feature_name>/architecture_preflight.md` for this feature covering:

## 1. Architecture Layer Impact

For React/Vite or Angular, identify the MVVM layers this feature touches:
- View (components): what new components are required?
- ViewModel (hooks/store): what server state and client state is needed?
- Model (API): what backend endpoints are consumed?

For `ui-nextjs`, use the server-first mapping instead:
- App Router composition and Server Components
- Feature application use cases and view models
- Typed backend API adapters
- Feature components and any justified Client Components
- Shared primitives/infrastructure

## 2. Backend Contract Analysis

- Which backend API endpoints does this feature consume?
- Are those endpoints already available or do they need to be built first?
- If a new contract is required from the backend team, flag it — this blocks UI implementation until the contract is accepted
- Confirm there is no direct SQL, database client/driver, ORM, migration,
  database schema, or connection string in the UI
- For Next.js, confirm Route Handlers and Server Actions are a thin BFF only
  for session, token protection, protocol adaptation, or limited aggregation;
  they contain no business logic

**HALT on any direct database access.** The database boundary cannot be waived
by ADR.

## 2.5 Repository Scope Analysis

Before proceeding to component and state management decisions, validate repository scope. See: `docs/REPO_SCOPE_ANALYSIS_GUIDANCE.md`

Verify the "Repository Scope" section in `features/<feature>/nfrs.md` is complete:

- [ ] One box is checked: "This repository only" OR "Multiple repositories" (with table)
- [ ] If multi-repo: all repos, owners, modules, and contracts are documented
- [ ] "Primary Owner" and "Key Cross-Repo Contracts" are listed

**HALT if incomplete.** Request the feature owner complete the Repository Scope section. Specify what is missing.

Once complete:
1. Confirm THIS repo is listed as owner in the scope table (stop if not)
2. For each external repo listed (especially backend): document the contract it exposes
3. Identify what THIS repo implements vs. what external repos provide

**Decision:** Is this a single-repo or multi-repo feature? Proceed with MVVM and state management decisions for THIS repo's portion only.

---

## 2.6 Extension Discovery

1. Scan `extensions/*/manifest.yaml` in the project root. If none exist, write "No extensions present" and skip the rest of this section.
2. For each discovered manifest, parse `id`, `capabilities`, `applies_to`, `contract_sets[].paths`, and `contract_sets[].relates_to`.
3. An extension is **applicable** to this feature when any of:
   - the feature touches a file matching one of `applies_to` globs
   - the feature's described intent uses a declared `capability`
4. For each applicable extension, list its contract paths in `architecture_preflight.md` under an "Extension Contracts" subheading, citing each contract file.
5. **Do not assume extension names from memory or training data — only act on what the discovered manifests declare.**

### Reading order when extension and core contracts overlap

6. **Read core contracts first**, then extension contracts. Treat both as authoritative unless `relates_to` declares otherwise:
   - `relates_to.extends: [<core_path>]` — extension layers **additional** constraints on top of the core contract. Both apply; the stricter rule wins on any specific point.
   - `relates_to.supersedes: [<core_path>]` — extension **replaces** the listed core contract for rules in the extension's scope. Prefer the extension; treat the core contract as historical context only.
7. If an applicable extension contract appears to conflict with a core contract and `relates_to` does **not** declare the relationship, **HALT** and request either (a) a manifest update declaring `extends`/`supersedes`, or (b) an ADR documenting the project-local resolution. Do not silently pick one.
8. Any `supersedes` of a core contract, or any deviation from an applicable extension contract, **requires an ADR**. Cite the manifest path and the superseded/deviated contract path in the ADR.

---

## 2.7 Scope Boundary Source Check  (informational — does not block)

Confirm whether the feature's deferred capabilities are author-declared or will be inferred.

- [ ] `nfrs.md` has a **non-empty** `## Out of scope` section: yes/no

If **yes**: note "Out-of-scope is author-declared — spec planning carries it into the plan verbatim."
If **no** (missing or empty): note "Spec planning will infer Out-of-scope and label it `<!-- INFERRED -->` in the plan. Recommend the feature owner add a non-empty `## Out of scope` to nfrs.md."

This is informational and does not block planning.

---

## 3. Shared Component Impact

- Does this feature require new shared components?
- If yes: are they truly generic or feature-specific? Shared components require an ADR if they change an existing contract.

## 4. State Management Decision

- What server state is needed? Confirm the framework's query library is sufficient (React Query for React, TanStack Angular Query for Angular).
- What client state is needed? Confirm the default store pattern is sufficient (Zustand for React, Signals for Angular).
- Is there any cross-feature state dependency? If yes, an ADR is required.

## 5. Accessibility Impact

- What WCAG 2.1 AA requirements apply to this feature?
- Are there any interaction patterns (modals, dynamic updates, custom controls) that need specific accessibility handling?

## 5.5 Brand and Design References

- Confirm `docs/ui/design/BRAND.md` is complete for the visual decisions this
  feature needs
- Review `features/<feature_name>/design.md`
- Inventory files under `features/<feature_name>/design/references/`
- Treat screenshots and mockups as advisory unless `design.md` explicitly
  promotes a named property to an accepted requirement
- Record loading, empty, error, success, responsive, keyboard, focus, and
  reduced-motion states

## 6. ADR Determination

Is an ADR required? An ADR is required if:
- A new shared component library or UI dependency is introduced
- Cross-feature state is needed
- A backend contract does not exist yet and must be negotiated
- Any MVVM boundary rule is intentionally violated

An ADR cannot permit direct database access or move backend-owned business
logic into the UI.

If yes: do not proceed to Spec Planning until the ADR is Accepted.

## 7. Evaluation Prediction (preliminary)

Preliminary assessment of:
- Component test coverage achievability
- Accessibility compliance risk
- E2E scenario complexity
