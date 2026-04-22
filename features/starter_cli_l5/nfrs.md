# Non-Functional Requirements: <feature_name>

## Repository Scope

This feature is contained to:
- [ ] This repository only
- [ ] Multiple repositories (complete table below if selected)

### Multi-Repository Details

If this feature spans multiple repos, document each below:

| Repository | Owner Team | Modules/Services | Contracts to Implement |
|---|---|---|---|
| (primary repo) | (team name) | (list modules) | (e.g., gRPC service, message schema) |
| (external repo) | (team name) | (list modules) | (e.g., CLI client, integration adapter) |

**Primary Owner:** (repo that orchestrates the feature)

**Key Cross-Repo Contracts:**
- List shared schemas, protocols, or integration points
- Example: "CLI calls backend gRPC service; backend publishes protobuf schema"

---

## Performance
- TBD

## Availability
- TBD

## Security
- TBD

## Compliance
- TBD

## Scalability
- TBD

## Observability
- TBD

## Dependencies
- TBD

## Testing Requirements
- TBD

## LLM Latency
- TBD
<!-- Example: p50 < 500ms, p95 < 2s, p99 < 5s for LLM calls -->

## LLM Cost
- TBD
<!-- Example: per-request budget < $0.05, monthly budget < $500 -->

## LLM Fallback
- TBD
<!-- Example: fallback to secondary model within 3s if primary fails -->

## LLM Safety
- TBD
<!-- Example: guardrail mode = nemo, zero jailbreak passes in adversarial suite -->
