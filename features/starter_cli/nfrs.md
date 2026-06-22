# Non-Functional Requirements: <feature_name>

## Repository Scope

**Scope:** `single-repo`
<!-- Replace `single-repo` with `multi-repo` if this feature spans multiple repositories, then complete the table below -->

### Multi-Repository Details

*Complete only if scope is `multi-repo`.*

| Repository | Owner Team | Modules/Services | Contracts to Implement |
|---|---|---|---|
| (primary repo) | (team name) | (list modules) | (e.g., gRPC service, message schema) |
| (external repo) | (team name) | (list modules) | (e.g., CLI client, integration adapter) |

**Primary Owner:** (repo that orchestrates the feature)

**Key Cross-Repo Contracts:**
- List shared schemas, protocols, or integration points
- Example: "CLI calls backend gRPC service; backend publishes protobuf schema"

---

## Out of scope

<!-- Deferred capabilities — list what a reviewer might expect but that is postponed to a
     later increment or separate feature. Spec planning carries these into the plan's
     `### Out of scope`. If left as "none declared yet", the plan's Out-of-scope will be
     inferred and labelled. -->
- none declared yet

---

## Performance
- TBD

## Security
- TBD

## Reliability
- TBD

## Observability
- TBD

## Compatibility
- TBD

## Dependencies
- TBD

## Testing Requirements
- TBD
