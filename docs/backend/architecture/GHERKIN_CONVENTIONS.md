# Gherkin Conventions

This document defines tagging, coverage, and naming rules for all `.feature` files in this repository.

These conventions are binding. All agents must reference this document when reviewing or generating Gherkin scenarios.

---

## 1. File Naming and Location

Each feature's acceptance criteria live at:

```
features/<feature_name>/acceptance.feature
```

One `.feature` file per feature folder. If a feature requires multiple independently runnable scenario groups, use a `features/<feature_name>/` subfolder with named `.feature` files.

---

## 2. Required NFR Tags

Every NFR category populated in `nfrs.md` must have at least one corresponding tagged scenario in `acceptance.feature`.

| NFR Category | Required Tag |
|---|---|
| Performance | `@nfr-performance` |
| Security | `@nfr-security` |
| Availability | `@nfr-availability` |
| Scalability | `@nfr-scalability` |
| Observability | `@nfr-observability` |
| Compliance | `@nfr-compliance` |

A populated NFR category is one where all fields have been filled (no TBD entries).

If a category in `nfrs.md` is not applicable, it must be explicitly marked `N/A` — not left blank or TBD.

---

## 3. Shared Contract Tag

Features that produce a shared artifact (schema, API contract, event definition, data model) consumed by other features, services, or agents must tag at least one scenario:

```
@contract
```

This tag triggers contract compatibility checks in CI.

---

## 4. Coverage Rule

Before implementation proceeds, an agent must verify:

1. Every populated NFR category in `nfrs.md` has at least one scenario tagged with the corresponding `@nfr-*` tag.
2. If the feature produces a shared artifact, at least one `@contract` scenario exists.
3. At least one scenario exercises the primary happy path.
4. At least one scenario exercises a significant failure or edge case.

If any of these are missing, stop and request completion before proceeding to planning.

---

## 5. Tag Placement

Tags are placed on the line immediately before the `Scenario:` or `Scenario Outline:` keyword they apply to.

Tags may also be placed at the `Feature:` level if they apply to all scenarios.

Example:

```gherkin
Feature: Schema contract publication

  @contract @nfr-availability
  Scenario: Published schema is retrievable by downstream consumers
    Given a schema has been published to the contract registry
    When a downstream service requests the schema by version
    Then the schema is returned with status 200

  @nfr-security
  Scenario: Unauthorized access to schema registry is rejected
    Given a request without valid credentials
    When the request is made to the schema registry
    Then the response is 401 Unauthorized
```

---

## 6. Enforcement

Agents must check tagging coverage during Architecture Preflight (Section 1: Artifact Review) and during plan finalization.

CI enforces that tagged scenarios are automated. Any Gherkin scenario not backed by an automated test must be documented as a gap in `plan.md`.
