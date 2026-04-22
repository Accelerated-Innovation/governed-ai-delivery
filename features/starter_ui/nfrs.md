# Non-Functional Requirements: <feature_name>

## Repository Scope

This feature is contained to:
- [ ] This repository only
- [ ] Multiple repositories (complete table below if selected)

### Multi-Repository Details

If this feature spans multiple repos, document each below:

| Repository | Owner Team | Modules/Services | Contracts to Implement |
|---|---|---|---|
| (primary repo) | (team name) | (list modules) | (e.g., JWKS endpoint, message schema) |
| (external repo) | (team name) | (list modules) | (e.g., JWT validation, API client) |

**Primary Owner:** (repo that orchestrates the feature)

**Key Cross-Repo Contracts:**
- List shared schemas, API contracts, or integration points
- Example: "Backend provides authenticated API; UI calls it with Bearer token"

---

## Accessibility
- TBD
<!-- Minimum: WCAG 2.1 Level AA. Zero critical or serious axe-core violations. -->

## Performance
- TBD
<!-- Targets: LCP < Xms, CLS < 0.1, FID < Xms. Define thresholds for your project. -->

## Browser Compatibility
- TBD
<!-- List supported browsers and versions (e.g. Chrome 120+, Firefox 120+, Safari 17+, Edge 120+). -->

## Usability
- TBD
<!-- Keyboard navigation, screen reader support, error message clarity. -->

## Security
- TBD
<!-- XSS prevention, CSRF protection, input sanitisation, sensitive data handling. -->

## Availability
- TBD
<!-- Graceful degradation when backend API is unavailable. Loading and error state requirements. -->

## Compliance
- TBD
<!-- GDPR, cookie consent, data retention display requirements (if applicable). -->

## Testing Requirements
- TBD
<!-- Component test coverage target, E2E scenario coverage, accessibility scan requirements. -->
