# Non-Functional Requirements: Task Dashboard

## Accessibility

- All interactive elements must be keyboard accessible (WCAG 2.1 AA — 2.1.1 Keyboard)
- The open task count badge must expose its value to assistive technology (WCAG 1.3.1 Info and Relationships)
- Task status changes must be announced via an `aria-live` region (WCAG 4.1.3 Status Messages)
- Focus must never be trapped unexpectedly during normal navigation (WCAG 2.1.2 No Keyboard Trap)
- All images and icons must have appropriate alt text or `aria-label` values (WCAG 1.1.1 Non-text Content)
- Zero critical axe-core violations on component render and zero serious violations on Playwright E2E scans
- WCAG 2.1 AA compliance is the minimum standard

## Performance

- Largest Contentful Paint (LCP) must be ≤ 1.0s under a simulated fast 4G connection (Core Web Vitals)
- Cumulative Layout Shift (CLS) must be < 0.1 during initial load and after task status updates
- The task list must be interactive within 200ms of a successful API response
- Optimistic updates must provide visual feedback before the API mutation resolves — no blocking spinner on "Mark complete"
- Background refetch polling interval must not be shorter than 30s to avoid unnecessary load

## Security

- The task dashboard must require an authenticated session — unauthenticated users are redirected to the login page before any data is fetched
- Task data must be scoped to the authenticated user — no cross-user data must be accessible via the API or exposed in the rendered DOM
- All API calls must route through the shared API service (see `docs/ui/architecture/react/TECH_STACK.md`) — no bare `fetch()` calls with inline auth headers
- Task identifiers and user identifiers must not appear in browser console logs or error messages surfaced to the user

## Availability

- The component must render a graceful error state (not crash or throw an unhandled exception) when the task API returns 4xx or 5xx responses
- Stale task data must remain visible during a background refetch — React Query `staleTime` must be configured to prevent content flash
- An offline or connectivity error state must appear if the network request fails due to connectivity loss

## Browser Compatibility

- Must function correctly on the latest two stable releases of Chrome, Firefox, and Safari
- No IE11 or legacy Edge support required
- Responsive layout required for viewport widths from 375px (mobile) to 1440px (desktop)
- Touch interaction must be supported — tap targets must be at minimum 44×44px (WCAG 2.5.5)

## Usability

- Filter selection (All / Open / Done) must persist within the session without a page reload (stored in Zustand client state)
- Task status change must provide immediate visual feedback before the API mutation resolves (optimistic update pattern)
- A loading skeleton must appear within 150ms of navigation to the dashboard to prevent a blank flash
- Error messages must be actionable — they must tell the user what went wrong and provide a retry action where applicable

## Testing Requirements

- All NFR categories above must have at least one tagged Gherkin scenario in `acceptance.feature`
- `@accessibility`-tagged scenarios must have jest-axe assertions in component tests and axe scans in Playwright E2E tests
- `@e2e`-tagged scenarios must have passing Playwright tests before merge
- `@nfr-performance` targets must be verified via Lighthouse CI in the CI pipeline
- No TBD entries are permitted in this file before Architecture Preflight begins
