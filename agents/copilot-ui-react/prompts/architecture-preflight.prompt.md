---
description: "Run before planning any UI feature to validate MVVM boundaries, backend contract availability, accessibility impact, and ADR need"
agent: "ask"
---

# Architecture Preflight — React UI

You are preparing to plan a new React UI feature.

Before generating any code or plan, read:
- `docs/ui/architecture/MVVM_CONTRACT.md`
- `docs/ui/architecture/COMPONENT_CONVENTIONS.md`
- `docs/ui/architecture/STATE_MANAGEMENT.md`
- `docs/ui/evaluation/eval_criteria.md`
- All accepted ADRs in `docs/ui/architecture/ADR/`

Produce an Architecture Preflight Report covering:

## 1. Feature Summary

- What is the feature from the user's perspective?
- Which feature artifacts are being used (acceptance.feature, nfrs.md, eval_criteria.yaml)?

## 2. MVVM Layer Impact

For each layer, describe what is needed:
- **View (components):** new components required?
- **ViewModel (hooks):** server state needed, query keys, data transforms?
- **ViewModel (store):** client UI state needed?
- **Model (API):** which backend endpoints are consumed?

## 3. Backend Contract Analysis

| Endpoint | Method | Exists? | Blocker? |
|---|---|---|---|

If any endpoint does not exist, flag it as a blocker. UI implementation cannot begin until the contract is negotiated and documented via ADR.

## 4. Shared Component Impact

Does this feature require new shared components? If yes — are they truly generic or feature-specific? Shared component promotion requires an ADR.

## 5. State Management Decision

- Server state: confirm React Query is sufficient
- Client state: confirm Zustand is sufficient, or "none required"
- Cross-feature state: Yes (ADR required) / No

## 6. Accessibility Impact

List WCAG 2.1 AA requirements for this feature. Note any complex interaction patterns (modals, dynamic updates, custom controls).

## 7. ADR Determination

Is an ADR required? Choose one and explain:
- ✅ ADR required → state the reason
- ✅ No ADR needed → confirm why not

If ADR required: implementation must not proceed until the ADR status is Accepted.

## 8. Preliminary Evaluation Assessment

- Component test achievability: High / Medium / Low
- Accessibility compliance risk: Low / Medium / High
- E2E complexity: Low / Medium / High

Output as structured Markdown. If any required inputs are missing, stop and ask before proceeding.
