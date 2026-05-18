# Architecture Preflight — [Feature Name]

**Feature:** [feature name]
**Date:** [YYYY-MM-DD]
**Status:** Draft | Approved | Blocked (ADR Required)

---

## 1. MVVM Layer Impact

### View (Components)
[List new components required. Note which are feature-specific vs candidates for shared/.]

### ViewModel — Hooks
[List React Query hooks needed. Note query keys, data shapes, and transforms required.]

### ViewModel — Store
[List Zustand store additions needed, or "None — no client UI state required."]

### Model — API
[List backend endpoints consumed. Note HTTP method, path, and whether the endpoint exists.]

---

## 2. Backend Contract Analysis

| Endpoint | Method | Exists? | Blocker? |
|---|---|---|---|
| `/api/...` | GET | Yes/No | Yes/No |

[If any endpoint does not exist: flag as blocker. UI implementation cannot begin until contract is negotiated and accepted via ADR.]

---

## 3. Shared Component Impact

[Does this feature require new shared components? If yes, are they truly generic or feature-specific?]

**ADR required:** Yes / No

---

## 4. State Management Decision

**Server state:** [Describe what React Query will manage]
**Client state:** [Describe what Zustand will manage, or "None"]
**Cross-feature state:** [Yes (ADR required) / No]

---

## 5. Accessibility Impact

[List WCAG 2.1 AA requirements for this feature. Note any complex interaction patterns.]

---

## 6. ADR Determination

**ADR required:** Yes / No

**Reason:** [If yes, explain why]

---

## 7. Evaluation Prediction (Preliminary)

**Component test achievability:** [High / Medium / Low — brief rationale]
**Accessibility compliance risk:** [Low / Medium / High — brief rationale]
**E2E complexity:** [Low / Medium / High — brief rationale]
