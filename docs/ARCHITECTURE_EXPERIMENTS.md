# Architecture experiments

Some features depend on an architectural assumption nobody has tested yet. An
example is whether trusted code can admit and select among three runtime skills
without handing authority to the model. Two common responses are both poor:
labeling the design approved in order to start a prototype, or blocking the
feature until the question is settled on paper. GovKit instead records a
**bounded experiment** that answers the question. Its result then informs the
architecture decision, and accepted requirements stay as they are.

Ordinary changes inside established boundaries need none of this. Experiments
are for material uncertainty only.

> **Status.** This page describes the record contracts and assessor added by
> [ADR 0020](../plans/decisions/0020-architecture-experiments.md). `govkit
> validate` and the consumer `quality-gate.yml` (GitHub and Azure) check them,
> as described below. Change conformance and the agent skills do not read
> them yet; those are later increments of the
> [Phase A plan](../plans/SOAA_GOVKIT_INCREMENTAL_IMPLEMENTATION_PLAN.md).

## Checking a project

`govkit validate` adds one result line per finding to each feature that
declares either record. Features that declare neither see no change. These
checks run at every level:

```bash
govkit validate --target .                       # all checks; experiment findings included
govkit validate --target . --only experiments    # only the experiment checks
govkit validate --target . --strict              # feature completion
```

| Finding class | Default | `--strict` |
|---|---|---|
| error | FAIL | FAIL |
| outstanding | WARN | FAIL |
| unknown | WARN | FAIL |

Expiry is measured against the current time.

The consumer quality gate runs the `--only experiments` command without
`--strict` whenever a feature outside `starter_*` declares either record. That
way, pull requests made during experimentation can merge while errors still
fail. Run with `--strict` when you are ready to declare the feature complete.
Both schemas ship with every feature install under `governance/schemas/`.

## The two records

**Preflight outcome.** A single fenced YAML block in
`features/<feature>/architecture_preflight.md`, validated by
`governance/schemas/preflight-outcome.schema.json`:

```yaml
preflight_outcome:
  status: experiment-required   # approved-for-planning | experiment-required | adr-required | blocked
  reason: Skill admission and selection with three skills is untested.
  experiments: [EXP-001]        # only with experiment-required
  relies_on:                    # passed, adopted experiments supporting an approval
    - experiment: EXP-002
      record: features/onboarding/experiments.yaml   # optional; defaults to this feature
      result_digest: <sha256 of the recorded result>
```

**Experiment set.** An optional `features/<feature>/experiments.yaml`,
validated by `governance/schemas/experiment-set.schema.json`. Each experiment
records:

- the material uncertainty, hypothesis and affected decisions;
- the accepted requirements that must stay intact, with their digests;
- the scope and permitted effects (`none`, `local-reversible` or
  `fixture-external`);
- the conditions, the oracle and the required evidence class (`application`
  or `synthetic-fixture`);
- the acceptance criteria, with optional catalog references such as
  `GK-SOAA-04`, plus limits and an optional expiry;
- the dependencies it assumed, each a `requirement`, `skill`, `policy`,
  `interface`, `runtime`, `implementation` or `catalog` file bound by digest;
- its status, its result (per-criterion outcomes, with evidence files bound by
  digest) and the decision taken.

Paths are literal and relative to the repository root. Digests are
lowercase SHA-256 hex. The `governance/examples/experiments/` folder holds six
worked scenarios.

## What the assessor reports

`cli/experiments.py` assesses one feature. It is pure: the caller supplies the
records, a digest reader and an optional clock.
`cli/experiment_store.py` reads them from disk. Reads are bounded, stay inside
the repository and never follow symlinks. When a feature declares neither
record, the store returns nothing, so existing features are unaffected.

| Class | Meaning | Codes |
|---|---|---|
| error | A record is invalid or contradicts itself, or the preflight relies on evidence that cannot support it | `invalid-record`, `invalid-outcome`, `feature-mismatch`, `unknown-criterion`, `duplicate-criterion-result`, `missing-criterion-result`, `status-contradiction`, `evidence-digest-mismatch`, `adopt-without-pass`, `decision-precedes-result`, `unknown-experiment`, `missing-record`, `stale-reliance`, `invalid-reliance` |
| outstanding | Work remains before the feature can complete | `experiment-outstanding`, `experiment-required`, `adr-required`, `preflight-blocked`, `decision-required`, `rerun-pending`, `insufficient-evidence-class`, `stale-requirement`, `stale-dependency`, `criteria-changed-after-result`, `inputs-changed-after-result`, `expired` |
| unknown | A digest or the expiry cannot be verified | `unverifiable-requirement`, `unverifiable-dependency`, `unverifiable-evidence`, `expiry-unverifiable`, `result-in-future`, `reliance-unverifiable` |

A feature is ready for completion only when it has no findings. Missing, stale,
failed or outstanding evidence never counts as a pass.

## Invalidation and reuse

A result records digests of the criteria, of the dependency list, and of every
requirement, dependency and evidence file it used. Any of these makes the
experiment **stale**:

- a named file changes;
- the criteria are edited after the result;
- dependencies are re-pinned without a rerun;
- the result is older than `expires_after_days`.

A preflight that relies on a stale experiment, or on a result whose digest has
changed, reports `stale-reliance`. The fix is to reassess and, where needed,
rerun. Invalidation is deliberately conservative: any edit to a named file
counts.

Evidence is reused through `relies_on`. A later feature can rely on another
feature's passed and adopted experiment while that experiment stays current.
The other feature's unfinished work does not leak into the relying feature.

The decision rules keep experiments from weakening requirements:

- `adopt` requires a passing result.
- A failed experiment is closed with `revise-design`, `reject-approach` or
  `narrow-supported-behavior`.
- `narrow-supported-behavior` must reference an accepted requirement change.
  That change alters the requirement files, which makes the dependent evidence
  stale.
- The schema has no waiver field.

## What a clean assessment does not show

A clean assessment shows only that the supplied records are well formed,
internally consistent and current with respect to the files they name.

- **No proof of execution.** It does not show that an experiment ran, or that
  its evidence is authentic.
- **No conformance claim.** It does not show that a design conforms to SOAA or
  to any other architecture.
- **No forgery detection.** Recomputing digests catches drift and accidental
  re-pinning. It cannot catch someone who deliberately rewrites both the
  evidence and the record.

Observed execution needs a trusted runner. Formal conformance needs a released
profile and assertion catalog.
