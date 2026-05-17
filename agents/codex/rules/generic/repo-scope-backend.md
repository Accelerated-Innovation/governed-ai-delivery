# Repository Scope Enforcement — Backend

These rules apply to all files in this backend project.

---

## Repository Scope Clarity

Before planning any feature, verify the "Repository Scope" section in `features/<feature>/nfrs.md` is complete:

- [ ] "This feature is contained to" has a checked box (single repo OR multi-repo)
- [ ] If multi-repo: "Multi-Repository Details" table is filled with all repos, owners, modules, and contracts
- [ ] "Primary Owner" field names the orchestrating repo
- [ ] "Key Cross-Repo Contracts" lists the integration points

**HALT if incomplete.** Do not begin planning until the feature owner completes repo scope. Request clarification with specific gaps.

---

## Scope Validation During Planning

When you prepare an architecture preflight or implementation plan:

1. **Confirm this repo is listed as owner** in the scope table
   - If NOT listed: stop and report the feature is out-of-scope for this repo
   - If listed: proceed to identify which modules/services in THIS repo will be affected

2. **For each external repo listed** (if multi-repo):
   - Document the contract it exposes (e.g., "Auth Service publishes `/jwks` endpoint")
   - Note that implementation of the contract belongs in the external repo
   - This repo consumes the contract, not implements it

3. **Validate that THIS repo does not own code in external repos**
   - Never add imports from external repos as if they were internal modules
   - Never write implementation code intended for another repo

---

## Code Writing Discipline

When implementing a feature:

**Allowed:**
- Code that implements features listed under this repo's ownership in the scope table
- Code that calls external contracts (REST APIs, gRPC services, shared schemas, message queues)
- Test code that mocks external contracts for integration testing

**Forbidden:**
- Writing implementation code for modules owned by another repo
- Adding code to `services/`, `adapters/`, `ports/`, or `api/` that belongs in another repo's codebase
- Creating dependencies on code that hasn't been published by the external repo yet (coordinate in nfrs.md first)
- Assuming a cross-cutting concern can be fully implemented in one repo without explicit owner assignment

---

## Multi-Repo Feature Pattern

If a feature spans multiple repos (determined in nfrs.md):

1. **Coordinate in NFRs first**
   - List all repos, owners, and modules
   - Define the contracts upfront (API schemas, message formats, gRPC protobuf, etc.)
   - Document which repo owns which part

2. **Each repo executes its own portion**
   - Repo A creates its feature branch with its own spec, plan, and implementation
   - Repo B creates its feature branch with its own spec, plan, and implementation
   - Each repo has its own PR with its own tests and CI validation

3. **Contract-Driven Integration**
   - Each repo implements against the shared contract (not tight coupling)
   - Integration happens at contract boundaries (HTTP, gRPC, message schemas)
   - Cross-repo integration tests (if any) verify contracts are met

---

## Anti-Patterns

- **"I'll implement it all in this repo and they can call it later"** — violates ownership, coupling, and duplicates effort
- **"The contract can be figured out during implementation"** — blocks parallel work and causes scope creep
- **"We don't need to list repos in nfrs.md because it's obvious"** — agents need explicit scope to avoid mistakes
- **"I'll add their code here and they can copy it to their repo"** — violates DRY, creates maintenance debt, violates ownership
