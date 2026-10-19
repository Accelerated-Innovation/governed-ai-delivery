# ADR 0020: Architecture experiment records and preflight outcomes

Status: Proposed with the SOAA Phase A Increment 2 PR. Merging that PR accepts
the record contracts and assessor below. It does not wire them into
`govkit validate`, change conformance, CI templates or agent payload; those are
later increments in `plans/SOAA_GOVKIT_INCREMENTAL_IMPLEMENTATION_PLAN.md`.

## Context

GovKit's feature workflow moves from requirements through architecture
preflight to planning and implementation. Preflight has no machine-readable
outcome, and `govkit validate` does not read its status. When a design depends
on an untested architectural assumption, the workflow offers two poor choices:
label the design aligned to start a prototype, or block delivery on
speculation. Results of contained experiments have no structured place, and
nothing invalidates them when the requirements, skills, policy or
implementation they depended on change.

Existing mechanisms supply the parts: strict JSON-shaped YAML parsing and
bundled schemas (`schema_validation`), contained no-symlink reads
(`pack_loading.contained_file`), digest-based staleness (`change:plan`),
timezone-aware timestamps (`release_metadata.timestamp`), and the precedent of
a fenced `evaluation_prediction` YAML block inside `plan.md`.

## Decision

Add two versioned contracts and one pure assessor. No command, skill or policy
engine is added.

- **Experiment set.** `experiment-set` v1 is the schema for an optional
  `features/<feature>/experiments.yaml`. Each experiment records:
  - the material uncertainty and hypothesis, plus the decisions affected;
  - the accepted requirements that must stay intact;
  - scope and permitted effects, conditions and oracle;
  - the required evidence class;
  - acceptance criteria, limits and digest-bound dependencies;
  - status, result and decision.

  A result binds the current criteria and dependency list by digest. Each
  criterion's evidence files are bound by digest too.
- **Preflight outcome.** `preflight-outcome` v1 governs one fenced YAML block
  whose top-level key is `preflight_outcome`, inside
  `architecture_preflight.md`.
  - Status values are `approved-for-planning`, `experiment-required`,
    `adr-required` and `blocked`.
  - `experiment-required` lists its experiments.
  - `relies_on` names passed experiments by result digest. Each may sit in
    another feature's record, which is how evidence is reused.
- **Assessor.** `cli/experiments.py` takes parsed records, a digest reader and
  an optional clock, and returns findings in three classes:
  - **error:** an invalid or contradictory record, or reliance on stale or
    unsupported evidence;
  - **outstanding:** work remains, such as experiments in progress, a missing
    decision, `experiment-required`, `adr-required` or `blocked`;
  - **unknown:** a digest or expiry cannot be verified.

  `cli/experiment_store.py` performs bounded, contained reads. It reports
  `None` when a feature declares neither artifact, so callers can leave
  existing output unchanged.
- **Staleness rules.** An experiment is stale when any of these no longer match:
  - a requirement or dependency digest;
  - the criteria digest;
  - the dependency-list digest;
  - the expiry, when one is set.

  Stale evidence cannot support reliance.
- **Decision rules.**
  - `adopt` requires a passing result.
  - `narrow-supported-behavior` requires a reference to an accepted requirement
    change.
  - A decision cannot predate its result.
- **Evidence class.** `synthetic-fixture` results never satisfy an experiment
  that requires `application` evidence. Required controls cannot pass on missing,
  stale, failed or outstanding evidence.

Digests are bare 64-character lowercase SHA-256 hex, matching every other
GovKit schema. The plan's earlier `sha256:` prefix wording is superseded.

## Consequences and boundary

A valid assessment means the supplied records are well formed, internally
consistent and current with respect to the files they name. It does not show
that an experiment ran, that its evidence is authentic, or that a design
conforms to SOAA or any other architecture. Recomputing digests detects drift
and accidental re-pinning. It cannot detect deliberate forgery by someone who
rewrites both the evidence and the record. Observed execution needs a trusted
runner; formal conformance needs a released profile and assertion catalog.

File-level digests invalidate conservatively: any edit to a named file makes
dependent evidence stale. Scenario-level requirement digests are deferred. The
contracts are additive and optional. No existing feature, command, report,
plan or CI template changes until a later increment consumes them.

Validation is test first: one negative test per finding code, bundled
example scenarios whose expected states are asserted, read-only and bounded
store behavior, and the fast suite.
