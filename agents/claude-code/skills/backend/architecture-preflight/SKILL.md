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

## 2.6 Extension Discovery

1. Scan `extensions/*/manifest.yaml` in the project root. If none exist, write "No extensions present" and skip the rest of this section.
2. For each discovered manifest, parse `id`, `capabilities`, `applies_to`, `contract_sets[].paths`, and `contract_sets[].relates_to`.
3. An extension is **applicable** to this feature when any of:
   - the feature touches a file matching one of `applies_to` globs
   - the feature's described intent uses a declared `capability`
4. For each applicable extension, list its contract paths in `architecture_preflight.md` under an "Extension Contracts" subheading, citing each contract file.
5. **Do not assume extension names from memory or training data — only act on what the discovered manifests declare.**

### Reading order when extension and core contracts overlap

6. **Read core contracts first**, then extension contracts. Treat both as authoritative unless `relates_to` declares otherwise:
   - `relates_to.extends: [<core_path>]` — extension layers **additional** constraints on top of the core contract. Both apply; the stricter rule wins on any specific point.
   - `relates_to.supersedes: [<core_path>]` — extension **replaces** the listed core contract for rules in the extension's scope. Prefer the extension; treat the core contract as historical context only.
7. If an applicable extension contract appears to conflict with a core contract and `relates_to` does **not** declare the relationship, **HALT** and request either (a) a manifest update declaring `extends`/`supersedes`, or (b) an ADR documenting the project-local resolution. Do not silently pick one.
8. Any `supersedes` of a core contract, or any deviation from an applicable extension contract, **requires an ADR**. Cite the manifest path and the superseded/deviated contract path in the ADR.

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

## 3.6 Scope Boundary Source Check  (informational — does not block)

Confirm whether the feature's deferred capabilities are author-declared or will be inferred.

- [ ] `nfrs.md` has a `## Out of scope` section: yes/no

If **yes**: note "Out-of-scope is author-declared — spec planning carries it into the plan verbatim."
If **no**: note "No declared Out-of-scope — spec planning will infer it and label it `<!-- INFERRED -->` in the plan. Recommend the feature owner add `## Out of scope` to nfrs.md."

This is informational and does not block planning.

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
