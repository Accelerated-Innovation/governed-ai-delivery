---
name: govkit-architecture-preflight
description: Validate architecture boundaries, standards alignment, and ADR need before planning a feature. Use when starting a new feature or invoking /govkit-architecture-preflight.
---

# Architecture Preflight

You are preparing to plan and implement a feature. Determine the feature name from the user's request; if it is not provided, ask before proceeding.

Before generating any code or detailed plan, produce an Architecture Preflight Report.

## Behavior contract (skip unless this project has one)

Read `authority` in `.govkit/skill_context.yaml` before anything else. If
`source` is `none` — the default, and where most projects are — **skip this
section entirely**: nothing in it applies, and you should not mention it.

If `source` is `pdg`, this feature's behavior is a **versioned commitment**.
An approved baseline binds its Rules and scenarios to an exact revision, and
what somebody approved is that revision — not the working tree in front of
you, and not your reading of it. The governing rule is the one govkit
installed as `behavior-contract`; it is already loaded, and it is binding.

Before relying on anything in the feature folder:

- Run the `validate-baseline` and `verify-authority` checks exactly as that
  rule specifies them. Both need `--target` and `--baseline`, and
  `verify-authority` also needs `--commitment` — omit it and the answer is
  *not authorized* about the pointer you did not supply, which says nothing
  about your work.
- **Check `sources` in the baseline first.** More than one entry means the
  contract spans repositories and every one of them needs its own
  `--source <source_key>=<path>` checkout. Without them you get refusals
  about missing sources, which are not a verdict on the contract.
- **Drift means stop.** The spec in front of you is not the one that was
  approved, and everything you plan from it inherits that.
- **Unverified is not permission.** An unreachable graph, or an unset
  `GOVKIT_PDG_URL`, leaves the question unanswered rather than answered yes.

Then change nothing that is committed. A scope change, an exclusion you
inferred, a behavior nobody asked for, or a relaxed threshold is a decision
for a person: name the scenario in conflict and wait. You may still refactor,
and this plan may still evolve, as long as every committed scenario keeps
passing.

## 1. Summary

- What is the feature or change?
- What input specs are being used (NFRs: `features/<feature_name>/nfrs.md`, Gherkin: `features/<feature_name>/acceptance.feature`, Eval criteria: `features/<feature_name>/eval_criteria.yaml`)?
- What affected modules or layers are in scope?

## 2. Standards Check

For each of the following, state which architectural rules apply (cite file and section):

- Layering (from `docs/{{docs_area}}/architecture/ARCH_CONTRACT.md`)
<!-- govkit:docs-area backend -->
- API conventions (from `docs/{{docs_area}}/architecture/API_CONVENTIONS.md`)
- Auth/security patterns (from `docs/{{docs_area}}/architecture/SECURITY_AUTH_PATTERNS.md`)
- NFR section contract (from `docs/{{docs_area}}/architecture/NFRS_CONVENTIONS.md`)
- Error model and response shape
- Logging and observability expectations
<!-- /govkit:docs-area -->
<!-- govkit:docs-area data -->
- Query conventions from the selected stack overlay, when installed
- Data quality tiers (from `docs/{{docs_area}}/architecture/DATA_QUALITY_CONTRACT.md`)
- PII handling (from `docs/{{docs_area}}/architecture/PII_HANDLING_CONTRACT.md`)
- Lineage (from `docs/{{docs_area}}/architecture/LINEAGE_CONTRACT.md`)
- Environments (from `docs/{{docs_area}}/architecture/ENVIRONMENTS.md`)
<!-- /govkit:docs-area -->

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
- Are any boundary rules at risk of violation? (from `docs/{{docs_area}}/architecture/BOUNDARIES.md`)
- Does this require a new interface between services?

## 3.5 Repository Scope Analysis

Before proceeding to ADR determination, validate repository scope. See: `docs/REPO_SCOPE_ANALYSIS_GUIDANCE.md`

Verify the "Repository Scope" section in `features/<feature>/nfrs.md` is complete:

- [ ] **Scope:** declares `single-repo` or `multi-repo`
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

- [ ] `nfrs.md` has a **non-empty** `## Out of scope` section: yes/no

If **yes**: note "Out-of-scope is author-declared — spec planning carries it into the plan verbatim."
If **no** (missing or empty): note "Spec planning will infer Out-of-scope and label it `<!-- INFERRED -->` in the plan. Recommend the feature owner add a non-empty `## Out of scope` to nfrs.md."

This is informational and does not block planning.

---

<!-- govkit:docs-area data -->
## 3.7 Data Impact

Add these four sections to the report.

### Pipeline Impact

- Schedule or SLA changes: run cadence, freshness targets, alert/block
  thresholds affected by this feature
- Backfill: required? Window strategy and idempotency expectations
- Orchestration dependencies: upstream sources and downstream jobs affected

### Contract Impact

- Mart schema changes: added, renamed, or removed columns — renames and
  removals are breaking per the mart layer rule's breaking-change table;
  they require a deprecation notice and consumer coordination
- Downstream exposures affected (check the exposures file for consumers)

### PII Impact

- New or reclassified PII columns and their categories
- Masking treatment per `PII_HANDLING_CONTRACT.md`, including non-prod
  environments

### Lineage Impact

- Source-to-mart lineage changes introduced by this feature
- Column-level lineage entries required for PII-tagged columns
- Exposure or lineage-tool entries to add or update

<!-- /govkit:docs-area -->
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

- [ ] `features/<feature_name>/agent_topology.md` exists — if missing, **HALT**: request `/govkit-multi-agent-design <feature_name>` first
- [ ] Orchestrator section is complete: role, system prompt path, model alias, routing strategy
- [ ] Each specialist agent has: role, typed input state fields, typed output state fields, system prompt path, model alias
- [ ] All system prompt files declared in `agent_topology.md` exist in the repository
- [ ] Routing Logic covers all edge conditions — every node has a path to END
- [ ] Failure Modes define per-node timeout, graph timeout, and node failure behavior
- [ ] State schema reference is present (TypedDict path declared)
- [ ] ADR required? (Yes if this is a new multi-agent feature or any topology change from prior preflight)

**Section 15 Status:** Approved / Blocked (strike one — Blocked if any item above is unchecked)
