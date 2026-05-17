---
name: architecture-preflight
description: Validate architecture boundaries, standards alignment, and ADR need before planning a feature. Use when starting a new feature or invoking /architecture-preflight.
---

# Architecture Preflight

You are preparing to plan and implement a feature. Determine the feature name from the user's request; if it is not provided, ask before proceeding.

Before generating any code or detailed plan, produce an Architecture Preflight Report.

## 1. Summary

- What is the feature or change?
- What input specs are being used (NFRs: `features/<feature_name>/nfrs.md`, Gherkin: `features/<feature_name>/acceptance.feature`, Eval criteria: `features/<feature_name>/eval_criteria.yaml`)?
- What affected modules or layers are in scope?

## 2. Standards Check

For each of the following, state which architectural rules apply (cite file and section):

- Layering (from `docs/backend/architecture/ARCH_CONTRACT.md`)
- API conventions (from `docs/backend/architecture/API_CONVENTIONS.md`)
- Auth/security patterns (from `docs/backend/architecture/SECURITY_AUTH_PATTERNS.md`)
- Error model and response shape
- Logging and observability expectations

## 3. Boundary Analysis

- What modules or services will this code touch?
- Are any boundary rules at risk of violation? (from `docs/backend/architecture/BOUNDARIES.md`)
- Does this require a new interface between services?

## 3.5 Repository Scope Analysis

Before proceeding to ADR determination, validate repository scope. See: `docs/REPO_SCOPE_ANALYSIS_GUIDANCE.md`

Verify the "Repository Scope" section in `features/<feature>/nfrs.md` is complete:

- [ ] One box is checked: "This repository only" OR "Multiple repositories" (with table)
- [ ] If multi-repo: all repos, owners, modules, and contracts are documented
- [ ] "Primary Owner" and "Key Cross-Repo Contracts" are listed

**HALT if incomplete.** Request the feature owner complete the Repository Scope section. Specify what is missing.

Once complete:
1. Confirm THIS repo is listed as owner in the scope table (stop if not)
2. For each external repo listed: document the contract it exposes
3. Identify module/service impact in THIS repo only — do not implement other repos' portions

**Decision:** Is this a single-repo or multi-repo feature? Proceed with boundary analysis for THIS repo's portion only.

---

## 4. ADR Decision

Choose one:

- ADR required → Include proposed ADR title and reason
- No ADR needed → Explain why

## 5. Tests Required

- What test types are needed? (unit, contract, integration, evals)
- What test coverage or metrics are required by the NFRs?

## 6. Risks & Unknowns

- List assumptions, open design questions, or external risks
- Flag any missing constraints, incomplete specs, or potential conflicts

---

Write this report to `features/<feature_name>/architecture_preflight.md`.

If any spec inputs are missing, ask before proceeding.

---

## 15. Agent Topology (multi-agent features only)

Check if `features/<feature_name>/eval_criteria.yaml` declares `multi_agent: true`.

If **not declared**, write: "Section 15: Not applicable — multi_agent not declared." and skip the rest of this section.

If **declared**:

- [ ] `features/<feature_name>/agent_topology.md` exists — if missing, **HALT**: request `/multi-agent-design <feature_name>` first
- [ ] Orchestrator section is complete: role, system prompt path, model alias, routing strategy
- [ ] Each specialist agent has: role, typed input state fields, typed output state fields, system prompt path, model alias
- [ ] All system prompt files declared in `agent_topology.md` exist in the repository
- [ ] Routing Logic covers all edge conditions — every node has a path to END
- [ ] Failure Modes define per-node timeout, graph timeout, and node failure behavior
- [ ] State schema reference is present (TypedDict path declared)
- [ ] ADR required? (Yes if this is a new multi-agent feature or any topology change from prior preflight)

**Section 15 Status:** Approved / Blocked (strike one — Blocked if any item above is unchecked)
