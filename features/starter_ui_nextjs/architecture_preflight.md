# Architecture Preflight: <feature_name>

Complete before finalizing the implementation plan.

## Artifact Readiness

- [ ] `acceptance.feature` is complete
- [ ] `nfrs.md` has no unresolved requirements
- [ ] `design.md` covers required states and brand application
- [ ] `eval_criteria.yaml` is complete
- [ ] Backend API contracts are identified and available

## Server-First Design

- Route and layout ownership:
- Server Components:
- Client Components and the browser capability requiring each:
- Suspense/loading/error boundaries:
- Cache and freshness behavior:

## Layer and Dependency Review

- `src/app/` composition:
- `src/features/<feature>/application/` use cases:
- `src/features/<feature>/api/` typed backend calls:
- `src/features/<feature>/components/` UI:
- Shared primitives required:
- Cross-feature dependencies:

## API Boundary

| Backend endpoint | Method | Contract available | Auth handling | Blocker |
|---|---|---|---|---|
| | | | | |

- Thin BFF needed: yes / no
- If yes, allowed reason (session, token protection, protocol adaptation,
  limited aggregation):
- Direct database, ORM, SQL, migration, or connection-string use found:
  no (required)
- Business logic in Next.js server code found: no (required)

The database boundary cannot be waived by ADR.

## Design and Accessibility

- `docs/ui/design/BRAND.md` reviewed:
- Reference images reviewed with advisory authority:
- WCAG implications:
- Responsive and reduced-motion behavior:

## Decision

- ADRs required:
- Backend contract blockers:
- Final status: Approved for planning / Blocked
