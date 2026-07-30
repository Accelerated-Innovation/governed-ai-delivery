# Non-Functional Requirements: <feature_name>

## Repository Scope

**Scope:** `single-repo`
<!-- Replace `single-repo` with `multi-repo` if this feature spans multiple
     repositories, then complete the table below. -->

### Multi-Repository Details

*Complete only if scope is `multi-repo`.*

| Repository | Owner Team | Modules/Services | Contracts to Implement |
|---|---|---|---|
| (primary repo) | (team name) | (list modules) | (for example, UI routes and typed API client) |
| (external repo) | (team name) | (list modules) | (for example, backend API operation and schema) |

**Primary Owner:** (repository that orchestrates the feature)

**Key Cross-Repo Contracts:**
- List versioned API schemas, authentication contracts, and integration points.
- The UI may consume published backend contracts but never replace them with
  direct database access.

---

## Out of Scope

- none declared yet

## Accessibility

- Standard: WCAG 2.1 AA or stricter project standard
- Keyboard, focus, screen-reader, and contrast requirements:

## Performance

- Rendering and Core Web Vitals targets:
- Server/client bundle constraints:
- Caching and freshness expectations:

## Resilience

- Backend API unavailable behavior:
- Timeout and retry behavior:
- Loading, empty, and error-state expectations:

## Security and Privacy

- Authentication and authorization expectations:
- Sensitive data and token handling:
- Browser/server data exposure constraints:

## Compatibility

- Supported browsers and devices:
- Responsive breakpoints or content constraints:

## Testing

- Unit and component coverage:
- Playwright flow coverage:
- Visual regression scope, if explicitly enabled:
