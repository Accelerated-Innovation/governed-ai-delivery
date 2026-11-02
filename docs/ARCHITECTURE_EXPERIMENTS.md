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
> as described below. For backend, CLI and data features, the agent skills,
> rules, entry instructions, templates and starters guide teams through the
> workflow. Request planning and change conformance consume the records
> through `experiment` references ([request workflows](REQUEST_WORKFLOWS.md),
> [change conformance](CHANGE_CONFORMANCE.md)). UI guidance is a later
> increment of the [Phase A plan](../plans/SOAA_GOVKIT_INCREMENTAL_IMPLEMENTATION_PLAN.md).

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

## The development loop

1. **Preflight.** Architecture preflight decides whether the design rests on
   an untested assumption. If it doesn't, record `approved-for-planning` and
   take the short path. For SOAA features, also copy the applicability block
   from the extension's `templates/preflight-soaa.md` into Section 15a.
2. **Record the experiment.** Set `experiment-required` and list the
   experiment IDs. Then add each experiment to `experiments.yaml` with status
   `planned`: its criteria, scope, permitted effects and the evidence class it
   needs. `govkit validate` warns until the experiment resolves.
3. **Run it and record the result.** Record per-criterion outcomes with
   digest-bound evidence files, then the decision. A failure closes with
   `revise-design`, `reject-approach` or `narrow-supported-behavior`; a
   revised design gets a new experiment.
4. **Rely on the result.** When the design is settled, set
   `approved-for-planning` and add `relies_on` entries naming passed, adopted
   experiments with their `result_digest`. If the digest is wrong,
   `govkit validate` reports the current one.
5. **Plan and conform.** In `request.json`, reference the record with kind
   `experiment` and no digest. The request then routes to full-feature work.
   Change conformance assesses the records as `artifact:experiment-record`. It
   needs the comparison base and a separate trusted policy checkout:

   ```bash
   govkit conform --request request.json --target . --base <base-sha> \
     --policy-target <trusted-policy-checkout> --observed-at <time>
   ```

   See [request workflows](REQUEST_WORKFLOWS.md) and
   [change conformance](CHANGE_CONFORMANCE.md).
6. **Optionally check SOAA coverage.** The `soaa-applicability` pack check
   reports which GK-SOAA cases the passed criteria cover. It needs GovKit
   0.23.0 or later.
7. **Complete.** Run `govkit validate --target . --strict`. Any change to a
   requirement, skill, policy or implementation file named by a result makes
   it stale, and step 3 repeats for that experiment.

`tests/wheel_experiment_smoke.py` runs this loop from a clean wheel for all
three agents, on both the legacy and declarative routes, using the bundled
scenarios.

## Starting a consuming-project pilot

For a backend API project such as the first pilot. Use a wheel built from
`main` or a published release; the `soaa-applicability` check needs 0.23.0 or
later.

```bash
python -m pip install /path/to/govkit-<version>-py3-none-any.whl
govkit apply --agent <claude-code|codex|copilot> --target . --level 5 --type api --ci <github|azure>
govkit extension add llm-application --target .     # only if the runtime calls models
govkit extension add skill-oriented-agent-architecture --target .
govkit extension list --installed --target .        # resolve any conflict before continuing
govkit init <feature> --target . --starter backend
```

**Declarative alternative.** Accept a profile that declares
`project_type: api` and selects the capabilities:
- SOAA (`skill-oriented-agent-architecture`);
- `llm-evaluation`, when the runtime calls models.

Then run `govkit profile apply` and `govkit pack apply`. The SOAA pack supports
only `api` and `cli` projects. Feature folders still come from `govkit init`.

**First slice.**
1. Pick one real task and one skill, and write the acceptance criteria.
2. Run architecture preflight and decide each SOAA applicability condition.
3. Where an assumption is untested, record EXP-001 with
   `required_evidence_class: application`, then follow the loop above.

**Facts to collect at the start:**
- the repository and revision, and the accountable owner;
- the task, its acceptance criteria, and the actual skills and how they are
  selected;
- data, tenant and effect boundaries, and the credentials involved;
- runtime, skill, dependency and test-adapter pins;
- the baseline effort, latency, cost and recovery burden.

File findings as GovKit issues. The bundled scenarios are synthetic. The
pilot's records carry `evidence_class: application` and are first-party
evidence, not independent verification.

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
