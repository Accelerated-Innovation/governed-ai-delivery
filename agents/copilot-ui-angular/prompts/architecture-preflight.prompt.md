---
description: "Run before planning any Angular UI feature to validate MVVM boundaries, backend contracts, accessibility impact, and ADR need"
agent: "ask"
---

# Architecture Preflight — Angular UI

You are preparing to plan a new Angular UI feature.

Before generating any code or plan, read:
- `docs/ui/architecture/MVVM_CONTRACT.md`
- `docs/ui/architecture/angular/COMPONENT_CONVENTIONS.md`
- `docs/ui/architecture/angular/STATE_MANAGEMENT.md`
- `docs/ui/evaluation/eval_criteria.md`
- All accepted ADRs in `docs/ui/architecture/ADR/`

Produce an Architecture Preflight Report covering:

## 1. Feature Summary
What is the feature from the user's perspective? Which feature artifacts are being used?

## 2. MVVM Layer Impact
- **View (components):** new standalone components required?
- **ViewModel (query functions):** server state, query keys, select transforms?
- **ViewModel (signal store):** client UI state needed?
- **Model (API):** which backend endpoints are consumed?

## 3. Backend Contract Analysis

| Endpoint | Method | Exists? | Blocker? |
|---|---|---|---|

Flag any missing endpoint as a blocker.

## 4. Shared Component Impact
New shared components required? Genuinely generic or feature-specific? Promotion requires an ADR.

## 5. State Management Decision
- Server state: TanStack Angular Query sufficient?
- Client state: Angular Signals sufficient, or "none required"?
- Cross-feature state: Yes (ADR required) / No

## 6. Accessibility Impact
WCAG 2.1 AA requirements. Note any complex patterns requiring Angular CDK.

## 7. ADR Determination
- ✅ ADR required → reason
- ✅ No ADR needed → why not

## 8. Preliminary Evaluation Assessment
Component test achievability / Accessibility risk / E2E complexity: High / Medium / Low

Output as structured Markdown. Stop and ask if any required inputs are missing.
