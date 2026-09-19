# Gherkin Tag Reference

Standard tags for all `.feature` files in this repository. These tags are used for filtering test runs, enforcing NFR coverage, and triggering CI checks.

See `GHERKIN_CONVENTIONS.md` for tagging rules, placement, and coverage requirements.

---

## NFR Tags

These tags link Gherkin scenarios to non-functional requirements in `nfrs.md`. Every populated NFR category must have at least one tagged scenario — this is enforced by `govkit validate`.

| Tag | Purpose | Example |
|-----|---------|---------|
| `@nfr-performance` | Response time, throughput, latency targets | "Response returns within 200ms under load" |
| `@nfr-security` | AuthN, AuthZ, data protection, injection prevention | "Unauthorized request returns 401" |
| `@nfr-availability` | Uptime, failover, degradation behavior | "Service returns cached response when upstream is down" |
| `@nfr-scalability` | Concurrent users, data volume, horizontal scaling | "System handles 1000 concurrent requests" |
| `@nfr-observability` | Logging, metrics, tracing, alerting | "Request produces structured log with correlation ID" |
| `@nfr-compliance` | Regulatory, audit trail, data retention | "PII is redacted from exported reports" |
| `@nfr-reliability` | Error recovery, retry behavior, data consistency | "Failed write is retried with exponential backoff" |
| `@nfr-compatibility` | Backward compatibility, API versioning, migration | "V1 clients still receive valid responses after V2 deploy" |

---

## Scenario Type Tags

These tags categorize scenarios by intent. They are not enforced by validation but are useful for organizing test runs and filtering.

| Tag | Purpose | When to use |
|-----|---------|-------------|
| `@happy-path` | Primary success scenario | The main flow a user follows when everything works |
| `@edge-case` | Boundary or unusual input | Empty inputs, maximum values, concurrent access, rare states |
| `@error` | Expected failure scenario | Invalid input, missing resources, permission denied, timeouts |

---

## Governance Tags (Level 4)

These tags trigger specific CI checks or governance workflows. They apply at Level 4 (Spec-Driven Add-On) and higher. Level 3 (Foundations) ships no `features/` directory and therefore no Gherkin scenarios, so these tags do not appear at L3.

| Tag | Purpose | CI behavior |
|-----|---------|-------------|
| `@contract` | Shared artifact scenario (schema, API contract, event) | Triggers contract backward-compatibility check in CI |
| `@e2e` | End-to-end scenario (UI projects) | Mapped to Playwright tests; included in E2E CI gate |
| `@accessibility` | WCAG compliance scenario (UI projects) | Mapped to axe-core scans in component and E2E tests |

---

## Identity Tags

Stable identifiers for a `Rule:` and for a scenario. Outside every other vocabulary here —
they never affect CI routing, coverage checks or filtering.

| Tag | On | Purpose |
|-----|----|---------|
| `@rule:<slug>` | a `Rule:` | Stable identity for the business decision |
| `@scenario:<slug>` | a scenario or `Scenario Outline` | Stable identity for the behavior |

Slugs are lowercase kebab-case: `@rule:only-approved-may-send`,
`@scenario:unapproved-blocked`.

**Why they exist.** Everything that points at a scenario — an `eval_criteria.yaml`
`rule_link`, an NFR row, readiness evidence, a test name — points at a *name* unless an
identifier exists. Rename the scenario and every reference silently means something else,
or nothing. An identifier survives rewording; a name does not.

**When they stop being optional.** If your project commits to behavior through a decision
service, they are **required**. A behavioral baseline binds the exact Rules and scenarios
an approval covers, and `govkit validate-baseline` refuses a *derived* identifier — one a
tool slugified from an element's name — precisely because that slug changes when the name
does. **Readable is not
approvable.**

The practical consequence: an element with no authored tag cannot be part of a commitment
at all. `govkit inspect-package` reports it as needing an identity rather than inventing
one, and no later tooling recovers it. Adding them is one line per element and is best done
before an approval, not after.

If your project has no decision service, they remain a recommendation — a derived
identifier is stable only as long as the name is.

---

## Tag Combinations

Tags can be combined on a single scenario:

```gherkin
@happy-path @nfr-performance
Scenario: Search returns results within SLA
  Given a catalog with 10,000 items
  When the user searches for "widget"
  Then results are returned within 200ms

@error @nfr-security
Scenario: Expired token is rejected
  Given a request with an expired JWT
  When the request reaches the API
  Then the response is 401 Unauthorized

@contract @nfr-compatibility
Scenario: V2 schema is backward compatible with V1 consumers
  Given a V1 consumer reading the schema
  When the schema is updated to V2
  Then the V1 consumer can still parse the response
```

---

## Custom Tags

Teams may define project-specific tags beyond this standard set. Custom tags should:

- Use lowercase with hyphens (e.g., `@slow-test`, `@requires-db`)
- Be documented in the project's `GHERKIN_CONVENTIONS.md` or a project-level tag reference
- Not conflict with the standard tags listed above
