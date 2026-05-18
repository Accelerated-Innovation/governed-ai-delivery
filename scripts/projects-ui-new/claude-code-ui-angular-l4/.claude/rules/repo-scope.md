# Repository Scope Enforcement — UI

These rules apply to all files in this UI project.

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
   - If listed: proceed to identify which features/components in THIS repo will be affected

2. **For each external repo listed** (if multi-repo):
   - Document the contract it exposes (e.g., "Backend publishes authenticated REST API at `/api/v1`")
   - Note that implementation of the contract belongs in the external repo (typically a backend service)
   - This UI repo consumes the contract, not implements it

3. **Validate that THIS repo does not own code in external repos**
   - Never add server-side implementation code as if it lived in this UI repo
   - Never write backend services, database schemas, or LLM gateway code in this UI repo

---

## Code Writing Discipline

When implementing a feature:

**Allowed:**
- Code that implements features listed under this repo's ownership in the scope table
- Code that calls external contracts (REST APIs, GraphQL endpoints, shared component libraries, design tokens)
- Test code (component tests, hook tests, MSW-based mocks) that exercises external contracts
- Code under `src/features/<feature>/` and `src/shared/` per the MVVM contract

**Forbidden:**
- Writing backend implementation code (services, adapters, ports, database queries, LLM gateway logic) in this UI repo
- Adding code to `src/features/<other-feature>/` internals — features are vertical slices and own their own state
- Adding to `src/shared/` without ADR approval — shared components are a shared contract
- Creating dependencies on backend code that hasn't been published yet (coordinate in nfrs.md first)
- Importing LLM provider SDKs directly — LLM calls go through backend endpoints

---

## Multi-Repo Feature Pattern

If a feature spans multiple repos (determined in nfrs.md):

1. **Coordinate in NFRs first**
   - List all repos, owners, and modules
   - Define the contracts upfront (REST endpoints, GraphQL schemas, shared types, message formats)
   - Document which repo owns which part (typically: this UI repo owns the View+ViewModel; a backend repo owns the Model implementation and any LLM gateway)

2. **Each repo executes its own portion**
   - This UI repo creates its feature branch with its own spec, plan, and implementation
   - The backend repo creates its feature branch with its own spec, plan, and implementation
   - Each repo has its own PR with its own tests and CI validation

3. **Contract-Driven Integration**
   - Each repo implements against the shared contract (not tight coupling)
   - Integration happens at contract boundaries (HTTP calls, API contracts, shared types, accessibility expectations)
   - Cross-repo integration tests (if any) verify contracts are met — typically via E2E Playwright tests pointing at a deployed backend

---

## Anti-Patterns

- **"I'll implement the backend here too and they can call it later"** — violates ownership, couples UI to backend internals, and duplicates effort
- **"The contract can be figured out during implementation"** — blocks parallel work and causes UI/backend mismatch
- **"We don't need to list repos in nfrs.md because it's obvious"** — agents need explicit scope to avoid mistakes
- **"I'll add their backend code here and they can copy it to their repo"** — violates DRY, creates maintenance debt, violates ownership
- **"The UI can call the LLM directly to avoid a backend round-trip"** — bypasses the LLM gateway, observability, and guardrail layers; an ADR is required and almost certainly rejected
