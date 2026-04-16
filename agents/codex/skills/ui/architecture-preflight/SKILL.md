---
name: ui-architecture-preflight
description: Validate UI architecture boundaries, backend contracts, and ADR need before spec planning
---

# Architecture Preflight — UI

You are performing an Architecture Preflight for a UI feature. Determine the feature name from the user's request; if it is not provided, ask before proceeding.

Read the following before proceeding:

- `docs/ui/architecture/MVVM_CONTRACT.md`
- `docs/ui/architecture/*/COMPONENT_CONVENTIONS.md`
- `docs/ui/architecture/*/STATE_MANAGEMENT.md`
- `docs/ui/evaluation/eval_criteria.md`
- All accepted ADRs in `docs/ui/architecture/ADR/`

---

Produce `features/<feature_name>/architecture_preflight.md` for this feature covering:

## 1. MVVM Layer Impact

Which layers does this feature touch? For each:
- View (components): what new components are required?
- ViewModel (hooks/store): what server state and client state is needed?
- Model (API): what backend endpoints are consumed?

## 2. Backend Contract Analysis

- Which backend API endpoints does this feature consume?
- Are those endpoints already available or do they need to be built first?
- If a new contract is required from the backend team, flag it — this blocks UI implementation until the contract is accepted

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

## 6. ADR Determination

Is an ADR required? An ADR is required if:
- A new shared component library or UI dependency is introduced
- Cross-feature state is needed
- A backend contract does not exist yet and must be negotiated
- Any MVVM boundary rule is intentionally violated

If yes: do not proceed to Spec Planning until the ADR is Accepted.

## 7. Evaluation Prediction (preliminary)

Preliminary assessment of:
- Component test coverage achievability
- Accessibility compliance risk
- E2E scenario complexity
