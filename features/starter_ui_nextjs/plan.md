# Feature Plan: <feature_name>

<!-- INSTRUCTIONS
     Complete this plan before implementation begins.
     The Evaluation Compliance Summary is mandatory — all score and evidence
     fields must be populated (no null values) before proceeding to code.
-->

## Objective and Scope

- Outcome:
- Users:
- In scope:
- Out of scope:

## Source Contracts

- Acceptance scenarios:
- NFRs:
- Brand and feature design:
- Backend API contracts:
- Relevant Next.js architecture documents:

## Layered Design

| Responsibility | Planned location | Notes |
|---|---|---|
| Route composition | `src/app/` | |
| Feature use cases | `src/features/<feature>/application/` | |
| Backend API access | `src/features/<feature>/api/` | |
| UI components | `src/features/<feature>/components/` | |
| Types | `src/features/<feature>/types/` | |
| Shared code | `src/shared/` | |

## Server and Client Boundaries

- Server Components:
- Client Components and justification:
- Route Handlers or Server Actions and thin-BFF justification:
- Cache/freshness strategy:
- Sensitive data exposure review:

## Backend API Dependencies

| Endpoint | Status | Contract | Blocker |
|---|---|---|---|
| | | | |

No implementation increment may replace a missing backend endpoint with direct
database access or business logic in Next.js.

## Increments

### Increment 1: <vertical outcome>

- Deliverables:
- Tests:
- Accessibility evidence:
- Design-reference evidence:
- Definition of done:

### Increment 2: <vertical outcome>

- Deliverables:
- Tests:
- Accessibility evidence:
- Design-reference evidence:
- Definition of done:

## Risks and Decisions

| Risk or decision | Impact | Mitigation or owner |
|---|---|---|
| | | |

## Evaluation Compliance Summary (MANDATORY)

Predict this evidence before implementation begins. Populate every score and
evidence field.

```yaml
evaluation_prediction:
  component_tests:
    FIRST_scores:
      fast:           { score: null, rationale: "" }
      isolated:       { score: null, rationale: "" }
      repeatable:     { score: null, rationale: "" }
      self_verifying: { score: null, rationale: "" }
      timely:         { score: null, rationale: "" }
    predicted_average: null
  accessibility:
    predicted_axe_violations: null
    wcag_level: AA
  thresholds_met: null   # true | false — false requires plan revision
```

If `thresholds_met` is false or the predicted FIRST average is below 4.0,
revise this plan before implementation begins.

## Definition of Done

- [ ] Acceptance and NFR scenarios pass
- [ ] API/database boundary check passes
- [ ] Server/client boundary is intentional
- [ ] Type checking, linting, unit/component, and Playwright tests pass
- [ ] Accessibility thresholds pass
- [ ] Brand and feature design are reflected in the UI
- [ ] ADRs and API contracts are current
