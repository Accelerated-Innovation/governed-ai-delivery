# Repository Scope Analysis Guidance

This document provides shared content for architecture-preflight skills and prompts across all agents (claude-code, copilot, codex).

---

## Repository Scope Analysis

Before proceeding to boundary analysis or ADR determination, validate repository scope.

### Checklist

Verify the "Repository Scope" section in `features/<feature_name>/nfrs.md` is **complete and explicit**:

- [ ] One of these is checked:
  - [ ] "This repository only"
  - [ ] "Multiple repositories" (with table filled in)
- [ ] If multi-repo:
  - [ ] "Multi-Repository Details" table lists all repos, owner teams, modules/services, and contracts
  - [ ] "Primary Owner" field identifies the orchestrating repo
  - [ ] "Key Cross-Repo Contracts" lists the integration points

**HALT if incomplete.** Request the feature owner complete the Repository Scope section before proceeding. Specify what is missing.

### Scope Validation

Once the Repository Scope section is complete:

1. **Confirm this repo is listed as owner** in the scope table
   - If NOT listed: STOP — this feature is **out-of-scope** for this repository
   - If listed: proceed to identify which modules/services in **THIS repo** will be affected

2. **For each external repo listed** (if multi-repo feature):
   - Document what contract it exposes (e.g., "Auth Service publishes `/jwks` endpoint", "Backend provides REST API at `/api/v1`")
   - Document what THIS repo will implement (e.g., "Frontend calls backend API with Bearer token")
   - Note: Implementation of the external repo's contract belongs in the external repo, not this one

3. **Identify module/service impact in THIS repo only**
   - If the scope table says "Repo A owns JWT validation" and "Repo B owns JWT issuance":
     - Repo A should plan JWT validation code
     - Repo B should plan JWT issuance code
     - Do NOT implement both in one repo

### Integration Points (Contracts)

For multi-repo features, document the contracts that bind repositories together:

**Examples:**
- REST API endpoint (method, path, request shape, response shape)
- gRPC service (protobuf definition)
- Message schema (async messages via Kafka/RabbitMQ)
- GraphQL schema
- Shared TypeScript types (if monorepo)
- Database schema (if shared database)

**Why this matters:** Contracts are the interface. Each repo implements against the contract without coupling to the other repo's internals. Integration tests verify contracts are met.

### Decision: Single-Repo vs Multi-Repo

After validation:

- **Single-repo feature:** Proceed to standard boundary and ADR analysis. This repo owns all modules touched by the feature.
- **Multi-repo feature:** Proceed to boundary analysis for **this repo's portion only**. Document which external repos must complete their portions in parallel. Integration testing verifies contracts.

---

## Agent-Specific Integration

This guidance is embedded into architecture-preflight for:
- `agents/claude-code/skills/backend/architecture-preflight/SKILL.md` — Section 3.5
- `agents/claude-code/skills/ui/architecture-preflight/SKILL.md` — Section 3.5
- `agents/copilot/prompts/backend/architecture-preflight.prompt.md` — Section 3.5
- `agents/copilot/prompts/ui/architecture-preflight.prompt.md` — Section 3.5
- `agents/codex/skills/backend/architecture-preflight/SKILL.md` — Section 3.5
- `agents/codex/skills/ui/architecture-preflight/SKILL.md` — Section 3.5
