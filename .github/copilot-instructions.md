# GitHub Copilot Instructions

These instructions govern how GitHub Copilot plans, reasons, and generates code in this repository.

They are mandatory.

Copilot must treat this repository as a governed delivery system, not an open coding environment.

Repository artifacts are the source of truth. Chat memory is not.

---

## 1. Operating Mode

Copilot operates aligned to:

* Product specifications under `features/`
* Architecture contracts under `docs/architecture/`
* Evaluation standards under `docs/evaluation/`
* Governance rules under `governance/`

Before planning or generating code:

* Read all files under `docs/architecture/`
* Read `docs/evaluation/eval_criteria.md`
* Apply architecture and evaluation contracts as binding constraints
* Confirm required feature artifacts exist

If required inputs are missing, stop and ask.

---

## 2. Mandatory Feature Structure

Every feature must live under:

`features/<feature_name>`

Required artifacts:

* `acceptance.feature`
* `nfrs.md`
* `eval_criteria.yaml`
* `plan.md`
* `architecture_preflight.md`

Implementation must not begin unless these artifacts exist.

---

## 3. Feature Lifecycle (Mandatory Order)

All work follows this sequence:

1. Architecture Preflight (feature-level)
2. ADR creation (if required)
3. Plan finalization
4. Evaluation Compliance Summary
5. Incremental implementation
6. Automated tests
7. Static analysis and evaluation gates

Steps may not be skipped.

Architecture Preflight is required once per feature and must be updated if scope materially changes.

---

## 4. Architecture Preflight

Architecture Preflight must:

* Be written to `features/<feature_name>/architecture_preflight.md`
* Follow `governance/templates/architecture_preflight.md`
* Be completed before plan finalization or implementation

Preflight is required:

* Once per feature
* When scope expands
* When new dependencies are introduced
* When security/auth patterns change
* When evaluation mode changes
* When an ADR trigger condition is met

If Preflight status is "Blocked", implementation must not proceed.

---

## 5. Planning Discipline

Copilot must not rely on chat output as a plan.

For every feature:

* Generate and maintain `features/<feature_name>/plan.md`
* Base it on `governance/templates/plan.md`
* Use required headings exactly as defined

### Plan Requirements

The plan must:

* Define explicit increments (`### Increment 1`, etc.)
* List deliverables per increment
* List tests per increment
* State evaluation impact per increment
* Include an **Evaluation Compliance Summary** predicting:

  * FIRST average score
  * 7 Virtue average score
  * Refactor triggers
* Reference ADRs
* Reference architecture contracts
* Reference evaluation standards

If predicted evaluation thresholds are not met:

* Revise the plan before implementation
* Do not generate code

If scope changes:

* Update `plan.md`
* Document rationale under `## Risks`
* Update ADRs if required
* Update `architecture_preflight.md` if boundaries change

Plan files are durable, versioned artifacts.

---

## 6. ADR Rules

An ADR is required when:

* A standard is extended, overridden, or bypassed
* A new architectural pattern is introduced
* A security or auth approach changes
* A boundary rule changes
* A new dependency direction is introduced

### 6.1 Location and Template

All ADRs:

* Live under `docs/architecture/ADR/`
* Follow `docs/architecture/ADR/TEMPLATE.md`
* Are referenced in `plan.md`
* Are referenced in the PR description

### 6.2 Template Completion Requirements

When an ADR is required:

* Create the ADR before implementation
* Complete Sections 1 through 9 of the template
* Sections 3 (Architectural Impact), 5 (Evaluation Impact), and 7 (Plan Alignment) must be explicit
* Cite relevant architecture contracts

If incomplete, stop and request clarification.

### 6.3 ADR Gate

If Preflight determines "ADR required":

Implementation must not proceed until:

* ADR exists
* ADR status is **Accepted**
* ADR is referenced in `plan.md`
* ADR is referenced in the PR description

Copilot must not generate implementation code until these conditions are satisfied.

---

## 7. Implementation Rules

### 7.1 Incremental Delivery

* Implement one increment at a time
* Do not expand scope beyond the active increment

### 7.2 Boundaries and Layering

* Respect all rules in `BOUNDARIES.md`
* Follow Hexagonal Architecture (ports and adapters)
* Do not introduce cross-layer imports
* Do not bypass ports or service interfaces

### 7.3 API Conventions

* Follow naming, versioning, and error rules
* Update OpenAPI definitions when APIs change
* Maintain backward compatibility unless ADR states otherwise

### 7.4 Security

* Use approved auth patterns
* No custom crypto or token logic
* Enforce authorization at entry points
* Avoid sensitive data in logs

---

## 8. Evaluation Discipline

Every feature must include `eval_criteria.yaml`.

Before implementation:

* Read `docs/evaluation/eval_criteria.md`
* Read `features/<feature_name>/eval_criteria.yaml`
* Confirm FIRST enforcement thresholds
* Confirm 7 Virtue thresholds
* Confirm LLM evaluation dimensions (if enabled)

### 8.1 Evaluation Compliance Gate

Implementation must not proceed unless:

* An Evaluation Compliance Summary exists in `plan.md`
* Predicted FIRST average ≥ required threshold
* Predicted Virtue average ≥ required threshold
* Refactor triggers are identified and mitigated

If predicted scores are below thresholds:

* Revise the plan before implementation
* Do not generate code

CI evaluation gates are binding.

---

## 9. Testing Requirements

Each increment must include:

* Unit tests compliant with FIRST:

  * Fast
  * Isolated
  * Repeatable
  * Self-verifying
  * Timely
* Contract tests (if APIs involved)
* Integration tests (if cross-boundary)

Tests must avoid:

* Real network calls
* Real database access
* Shared mutable state
* Order-dependent execution

FIRST violations require refactor before proceeding.

---

## 10. Static Analysis and Quality Gates

All generated code must pass:

* SonarQube quality gates
* Boundary enforcement rules
* Security scans
* Evaluation gates (if applicable)

Violations must be fixed before proceeding.

---

## 11. Automatic Refactor Conditions

Copilot must trigger refactor before proceeding if:

* Duplicate logic detected
* Structural complexity excessive
* FIRST score < threshold
* 7 Virtue score < threshold
* Code violates structural simplicity rules
* Test flakiness detected

Refactor must occur before expanding scope.

---

## 12. Output Expectations

Plans and implementations must include:

* Referenced standards
* ADR status
* Architecture compliance confirmation
* Test coverage summary
* Evaluation impact summary

If alignment is unclear, stop and ask.

---

## 13. Authority

Architecture decisions belong to the Architect.

Exceptions require:

* An ADR
* Explicit approval

Copilot follows standards. It does not invent them.

---

## 14. Design Principles

All plans and code must follow:

* SOLID principles
* Structural simplicity rules defined in `docs/evaluation/eval_criteria.md`
* Clear separation of ports and adapters

Generated code must avoid violations flagged by SonarQube rules tagged with `solid-*`.

If complexity or duplication emerges, refactor before proceeding.
