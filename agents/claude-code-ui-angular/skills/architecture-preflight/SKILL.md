# Architecture Preflight — Angular UI

You are performing an Architecture Preflight for an Angular UI feature. Read the following before proceeding:

- `docs/ui/architecture/MVVM_CONTRACT.md`
- `docs/ui/architecture/angular/COMPONENT_CONVENTIONS.md`
- `docs/ui/architecture/angular/STATE_MANAGEMENT.md`
- `docs/ui/evaluation/eval_criteria.md`
- All accepted ADRs in `docs/ui/architecture/ADR/`

Feature: $ARGUMENTS

---

Produce `architecture_preflight.md` covering:

## 1. MVVM Layer Impact

- **View (components):** new standalone components required?
- **ViewModel (query functions):** server state needed, query keys, select transforms?
- **ViewModel (signal store):** client UI state needed?
- **Model (API):** which backend endpoints are consumed?

## 2. Backend Contract Analysis

| Endpoint | Method | Exists? | Blocker? |
|---|---|---|---|

Flag any missing endpoint as a blocker — UI implementation cannot begin until the contract is negotiated and accepted via ADR.

## 3. Shared Component Impact

Does this feature require new shared components? If yes — are they truly generic or feature-specific? Promotion to `shared/` requires an ADR.

## 4. State Management Decision

- Server state: confirm TanStack Angular Query is sufficient
- Client state: confirm Angular Signals is sufficient, or "none required"
- Cross-feature state: Yes (ADR required) / No

## 5. Accessibility Impact

List WCAG 2.1 AA requirements. Note any complex interaction patterns (modals, dynamic updates, custom controls) requiring Angular CDK.

## 6. ADR Determination

- ✅ ADR required → state the reason
- ✅ No ADR needed → confirm why not

If ADR required: implementation must not proceed until status is Accepted.

## 7. Preliminary Evaluation Assessment

- Component test achievability: High / Medium / Low
- Accessibility compliance risk: Low / Medium / High
- E2E complexity: Low / Medium / High
