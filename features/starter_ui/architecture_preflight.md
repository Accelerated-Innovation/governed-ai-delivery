# Architecture Preflight: <feature_name>

<!-- INSTRUCTIONS
     Complete every section before plan finalization.
     Status must be "Approved for planning" before implementation begins.
     Template source: governance/ui/templates/architecture_preflight.md
-->

---

## 1. Artifact Review

Feature folder: `features/<feature_name>/`

- acceptance.feature reviewed: yes/no
- nfrs.md reviewed: yes/no — no TBD entries: yes/no
- eval_criteria.yaml exists: yes/no
- plan.md exists: yes/no
- All `@e2e`-tagged Gherkin scenarios have planned Playwright tests: yes/no
- All `@accessibility`-tagged scenarios have planned axe checks: yes/no

If any required artifact is missing or nfrs.md contains TBD entries, stop.

---

## 2. Standards Referenced

- `docs/ui/architecture/MVVM_CONTRACT.md` — sections:
- `docs/ui/architecture/react/COMPONENT_CONVENTIONS.md` or `docs/ui/architecture/angular/COMPONENT_CONVENTIONS.md` — sections:
- `docs/ui/evaluation/eval_criteria.md` — sections:

---

## 3. MVVM Layer Impact

### View (Components)
- New components required:
- Shared components required (needs ADR if new):
- Cross-feature component usage:

### ViewModel — Query Layer
- Server state needed (React Query / TanStack Angular Query):
- Query keys required:
- Data transforms required:
- Mutations required (with cache invalidation strategy):

### ViewModel — Store Layer
- Client UI state needed (Zustand / Angular Signals):
- State shape:
- Or: "None — no client UI state required"

### Model — API Layer
- Backend endpoints consumed:
- Endpoint availability: available | pending (blocker)
- New endpoints required: yes/no

---

## 4. Backend Contract Analysis

| Endpoint | Method | Exists? | Blocker? |
|---|---|---|---|
| `/api/...` | GET | yes/no | yes/no |

If any endpoint does not exist: implementation is blocked until the contract is negotiated and accepted via ADR.

---

## 5. Accessibility Impact

- WCAG 2.1 AA requirements for this feature:
- Complex interaction patterns (modals, dynamic updates, custom controls): yes/no
- Angular CDK required (focus trapping, live announcer): yes/no/n-a
- Accessibility risk: Low / Medium / High

---

## 6. Evaluation Impact

- Mode: ui | none
- FIRST enforcement required: yes/no
- Accessibility threshold achievable: yes/no
- E2E coverage achievable: yes/no
- Evaluation risk areas:

---

## 7. ADR Determination

ADR required: yes/no

If yes:
- Proposed title:
- Trigger condition (new library / cross-feature state / missing contract / boundary violation / WCAG exception):

If no:
- Justification:

---

## 8. Preflight Conclusion

- MVVM alignment: compliant | requires ADR | blocked
- Accessibility alignment: compliant | requires review | blocked
- Evaluation alignment: compliant | update required | blocked

Final status:
- Approved for planning
- Blocked pending ADR
- Blocked pending backend contract
- Blocked pending clarification
