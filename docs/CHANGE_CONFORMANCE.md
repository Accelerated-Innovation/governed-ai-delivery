# Conformance for an actual change

`govkit conform --request` selects the actual-change inspection path. It combines the accepted
profile, normalized request, pinned checks and actual Git changes. Plain
`govkit conform --target ...` retains the repository inspection behavior described
in [CONFORMANCE.md](CONFORMANCE.md). Request normalization and planning remain in
[REQUEST_WORKFLOWS.md](REQUEST_WORKFLOWS.md).

```sh
govkit conform --target /work/project \
  --request /work/accepted/request.json \
  --base <accepted-base-commit> \
  --policy-target /work/trusted-policy \
  --observed-at 2026-09-23T12:00:00Z \
  --execute-check project:tests --json
```

Without execution flags this inspects inputs and reports configured commands as
skipped. Required unknown, skipped or failed checks block a successful exit.
`--plan previous-plan.json` checks a saved plan for changed intent, policy,
references, workflow and obligations. Requirements are always recomputed; an
edited plan cannot remove them. The CLI provides no path-filter escape hatch.

## Accepted policy and trust

`--policy-target` and the inspected repository must be separate: neither directory
may contain the other, including through resolved symlinks. It contains the
accepted `.govkit/profile.yaml`, verified `.govkit/pack-lock.json`, installed
pinned resources, and local accepted source references. Add an optional accepted
reference to the profile:

```yaml
policy:
  source: {reference: policy.md, authority: accepted}
  conformance: {reference: conformance.json, authority: accepted}
```

The trusted caller must select this checkout, base, normalized intent and execution
flags. In CI use protected configuration or a separately fetched accepted revision,
not files or arguments controlled by the proposed change. Do not run untrusted
project code with privileged credentials. Local paths, digests and the word
`accepted` do not authenticate authority. The shared command and JSON contract are used by
[generated provider entry points](PIPELINE_GENERATION.md).
[Provider admission and evidence](PROVIDER_EVIDENCE.md) check caller-supplied
PR context and bind exported observations; protected-caller configuration and
authenticated enforcement evidence remain separate requirements.
No local result manufactures reviewer/platform approval. Architecture requests
retain required `approval:architecture = unknown` until a future platform adapter
can supply independently verified approval.

The accepted `conformance.json` follows `change-policy.schema.json`:

```json
{
  "schema_version": 1,
  "impact_rules": [{"paths": ["src", "docs"], "impacts": {}},
                   {"paths": ["src/auth"], "impacts": {"auth": true}}],
  "artifacts": [{"id": "spec", "references": ["docs/existing-spec.md"]}],
  "commands": [{"id": "project:tests", "argv": ["{python}", "-m", "pytest"],
                "timeout_seconds": 60}],
  "constraints": [{"id": "service-boundary", "source": "architecture.md",
                   "paths": ["src"], "forbidden_text": ["import forbidden_adapter"]}]
}
```

This is an illustrative configuration, not a complete feature fixture. Configure
references for all artifacts selected by your accepted workflow. Paths are literal
repository-relative file/directory prefixes, with `.` meaning the whole repository;
globs, traversal and external paths are rejected. Matching impact rules may only
add risks (`true`). An empty impacts object explicitly classifies that scope as
having no *additional* path-derived risks; it never erases request risks.
Unclassified changes block and make unmeasured risks visible. A broad rule such as
`.` is a consequential accepted policy choice, not automatic source-code analysis.

Commands have unique IDs, argv arrays and explicit timeouts (1–300 seconds).
`{python}` selects the running interpreter. There is no shell interpolation by
GovKit. Commands execute in the inspected project only on repeatable
`--execute-check ID` opt-in, are trusted and unsandboxed, and may themselves write
files or contact services. Built-in/approval/defect IDs cannot be replaced.
Stdout/stderr are represented by digests, not copied into the report. A shared
project-test provider supplies `project:tests` and `artifact:test-evidence`.
Command exit status only measures the configured behavior; it is not semantic
approval. Unknown providers stay unknown.
Directory separation is an input guard, not an execution sandbox; trusted commands
still have the invoking user's filesystem permissions.

Pinned pack checks retain `--execute-pack-check ID` (or `--execute-check ID`) and
`--pack-arguments arguments.json`. Every argument entry must name a required pack
check explicitly selected to run. Resources are verified in the trusted checkout;
the command runs against the inspected project. LLM checks run independently of
workflow size and native skill loading. The shipped exact-match example evaluates
supplied outputs, without calling a model. `artifact:change-record` reflects the
validated intent snapshot. Other artifacts reuse nonempty contained references
(up to 64 KiB each), proving presence and bytes, not semantic acceptance.

**Experiment records and preflight outcomes.** A request that references an
experiment record gets the `artifact:experiment-record` check:
- **What it reads:** each referenced `<feature>/experiments.yaml` in the inspected
  checkout, assessed with the [experiment assessor](ARCHITECTURE_EXPERIMENTS.md) at
  `--observed-at`. Without an observation time, expiry stays unverifiable.
- **FAIL:** a missing or unreadable record, or errors such as contradictions,
  stale reliance or digest mismatches.
- **UNKNOWN:** outstanding experiments or unverifiable evidence. UNKNOWN never
  passes a required check.
- **PASS:** consistent, current records. The evidence carries the limitation that
  it validates records and their bound digests and does not authenticate execution
  or results.

`artifact:architecture-preflight` also honors a declared `preflight_outcome` block
in its configured references:
- `blocked` or an invalid block FAILs.
- `experiment-required` and `adr-required` are UNKNOWN.
- `approved-for-planning`, or no block, behaves as before.

## Git scope, transitions and defects

The explicit base is resolved to a commit. The snapshot compares it with Git-visible
working-tree bytes, including committed changes since base, staged/unstaged edits,
untracked nonignored files, deletions and executable-mode changes. Renames appear
as add/delete. Repository-root inspection avoids partial-directory blind spots.
Default bounds are 2,048 files per tree, 1 MiB per file, 16 MiB per tree and 256 changed
paths. Unsupported kinds (including symlinks/submodules), unavailable Git inputs,
unsafe paths and exceeded bounds leave scope incomplete and blocking.
Limit diagnostics identify the inventory or content budget exceeded, its limit,
and the observed count or byte size. Per-file diagnostics include a JSON-escaped
repository-relative path; bounded working-tree reads report a lower bound on size.
Paths whose JSON representation exceeds 2,048 characters use an independently
escaped 128-character prefix, an explicit truncation marker and the SHA-256 of the
full UTF-8 relative path. This keeps diagnostics within report-schema limits
without splitting escapes or losing the ability to distinguish matching prefixes.
The first exceeded budget stops capture, so resolving it may reveal another bound.
Human and JSON conformance reports retain these diagnostics while scope remains
unknown and the command exits nonzero. They contain no file contents or raw Git
errors. These raw local reports may identify repository paths; use the
[privacy-filtered change posture export](CHANGE_POSTURE.md) for sharing.
The diagnostics do not change budgets or authorize excluding files, removing assets
or accepting policy. Review such changes separately before retrying.
Sparse/skip-worktree and conflicted indexes are unsupported and remain incomplete;
missing sparse files are not reported as deletions. The index's object IDs, modes
and flags contribute to the captured identity. If content changed from the base in
the index differs from working-tree bytes or modes, its path remains in scope and
scope is unverified. Reconcile the index and working tree before retrying: commands
run on the working tree and cannot prove a different staged version conforms.
Ignored untracked content is unmeasured. No checkout, index refresh, textconv or diff helper
runs. This is not a filesystem transaction; the final `change:stable-inputs` check
recaptures Git and accepted inputs and rejects changes observed during execution.

The separately selected accepted conformance configuration may set
`observation_limits.max_file_bytes` to an integer from 1 through 8,388,608 (8 MiB).
Omitting the object or field retains 1,048,576 (1 MiB). For example:

```yaml
observation_limits:
  max_file_bytes: 8388608
```

Only this per-file bound is configurable. Booleans, floats, nulls, unknown fields,
zero/negative values and values above the ceiling are rejected. Profile and
conformance sources remain bounded to 64 KiB. Target configuration, environment
values, request labels and imported reports cannot select the trusted limit.
Rechecking the accepted source before each executable check withholds commands
if it changes; final recapture uses the original budget and invalidates the run.
Larger limits do not waive architecture checks or exclude any tracked asset.

New `change-results` records use schema version 2. `change.observation` records
the effective limits, raw accepted-source SHA-256 and source state, and contributes
to the canonical change identity. Omitting optional `policy.conformance` uses
`default` provenance and can establish complete Git scope; missing conformance
mapping still leaves its required checks unknown and execution withheld.
A declared source that is invalid or unavailable leaves scope incomplete.
Version-1 records retain their historical default-limit interpretation and original
digests on replay. Older readers reject version 2; update the reader before sharing
new records. Raw records and digests are consistency evidence, not authenticated
approval. Consumer policy adoption still requires its own review.

Current architecture constraints scan all matching Git-visible files, including
unedited files. Target constraints apply only within the accepted transition and
contract scopes: `new`, `new-and-changed`, or `all`; `retain` does not activate the
target. The built-in measurement counts configured forbidden literal text per
file. It is not a language parser, dependency graph or complete prose/NFR verifier.
Unconfigured contracts, uncovered files and non-text files remain unknown. Other
semantic controls need explicit trusted providers.

Existing occurrence counts are compared with the base. Only existing occurrences
can use an exception within the transition, current contract and exception scopes.
Each overlapping transition must satisfy its own exceptions; a valid exception in
one transition cannot excuse an expired or absent exception in another. Shared
top-level contracts are measured within each applicable transition context.
Extra occurrences in that file are new violations; moving code to a new path does
not transfer its exception. The literal check cannot distinguish replacement or
movement of identical text within a file with an unchanged count. Exception expiry
requires explicit `--observed-at` and a recorded expiry; unavailable expiry is
unknown, and dates before that observation date fail. Exception evidence remains
visible even when other checks fail. Nothing automatically retires current rules
or approves migration completion.
Observation timestamps must include a timezone in RFC 3339 syntax; invalid input
is rejected before command execution. Valid offsets and lowercase `t`/`z` normalize
to an ISO timestamp with an explicit offset.

Defect requests retain the existing bundled `fix_record` schema and eligibility
checks. Configure exactly one `fix-record` artifact at `fixes/<id>/fix.yaml`, with
accepted established-behavior and regression-test references matching the normalized
request. Actual changed paths must fit the recorded surface (apart from the record
itself). To measure red/green, explicitly select `defect:eligibility` and configure
`project:tests`. The trusted command must pass on the current project and an isolated
current snapshot before baseline failure can count as red evidence. Both isolated
runs use the same temporary path, rebuilt between runs, with captured executable
modes and the same **current** declared regression-test bytes. Declare all regression
test inputs in the normalized request; a missing or obsolete base test cannot prove
a defect. A healthy baseline with a newly added passing test fails eligibility.
This does not check out or mutate either source tree. Snapshots omit Git metadata,
ignored dependencies and unsupported file kinds. If the isolated current run fails
(even though the real checkout passes), eligibility remains unknown. The caller
must configure tests that run equivalently in this bounded environment; command
exit status does not distinguish every possible infrastructure failure from an
assertion failure. Only the configured tests are evidenced; record assertions alone are
not test execution. Broader changes escalate through request routing.

## A change cannot weaken a feature's definition

A feature is done when its scenarios pass and its criteria are met. A change could reach that by editing the scenarios or criteria instead of the code. When a change touches `features/<name>/acceptance.feature` or `features/<name>/eval_criteria.yaml`, the report includes `change:definition`, which compares each file with what it was at the base.

What passes:

- a new scenario, criterion or definition file;
- a comment, reordering or reformatting that leaves the content the same. A number written another way (`1` and `1.0`) is the same; `1` and `true` are not.

What fails, each with its own finding:

| Code | Meaning |
|---|---|
| `scenario-removed` | A scenario that was at the base is gone, or was renamed without a `@scenario:` tag |
| `scenario-altered` | Its steps, tags, title or examples changed |
| `shared-steps-changed` | A `Background` above it was changed, added or removed, or it was moved under another |
| `criterion-removed` | A criterion that was at the base is gone from its list |
| `criterion-altered` | Its threshold, target or any other field changed |
| `criteria-changed` | Something else in `eval_criteria.yaml` changed, or its criteria are not all named and its parsed content changed |
| `definition-removed` | The file was deleted |
| `definition-unreadable` | The file can no longer be identified or parsed |

A finding does not say the edit made the definition worse. GovKit cannot tell a correction from a weakening, so any change to what existed needs a person. The message names the file and the scenario or criterion, and holds no step text or values.

A base file that cannot be identified gives `unknown` with `definition-not-compared`, never a pass. The check runs nothing and reads only the captured snapshot. A change that touches no definition file has no such check.

See ADR 0026. Existing tests and other files are covered by the next section.

## A change cannot weaken the tests and files that check it

A change could also pass by editing an existing test, a fixture, a test setting or the CI workflow, or by marking a test as skipped. GovKit cannot guess which paths these are, so the accepted conformance configuration declares them:

```json
"protected": {
  "tests": ["tests"],
  "files": ["tests/conftest.py", "pytest.ini", ".github/workflows", "known-failures.json"],
  "escape_markers": ["pytest.mark.skip", "pytest.mark.xfail", "@wip"]
}
```

The section is optional, and it is read from the trusted policy checkout, so the change being judged cannot edit it. When it is present, the report includes `change:protected`.

| Key | Rule for an existing file | A new file |
|---|---|---|
| `tests` | It may only gain lines. Every line it had at the base must still be there, in the same order | Passes |
| `files` | It may not change | Passes |

A path under both follows `files`. A changed file mode, such as a lost executable bit, counts as a change to an existing file under either rule. Paths are literal and relative to the repository root; a folder covers everything under it.

`escape_markers` are literal text. The number of times each appears in the files under `tests` and in feature definition files may fall and may not rise.

| Code | Meaning |
|---|---|
| `test-altered` | An existing test file lost or changed a line |
| `test-removed` | An existing test file was deleted |
| `protected-file-changed` | An existing file under `files` changed |
| `protected-file-removed` | An existing file under `files` was deleted |
| `escape-marker-added` | A file has more of a declared marker than at the base, and the total rose |

A finding means a person must look. It does not say the edit made a test worse.

What to declare:

- under `tests`, the folders that hold tests;
- under `files`, shared fixtures and helpers, the test runner's settings, CI workflows, the known-failures record, and any datasets or rubrics an evaluation reads;
- under `escape_markers`, the ways your runner skips or expects failure, and any pending tag you use in Gherkin.

Limits to know:

- A line inserted inside an existing test, such as an early return, keeps every earlier line and is not seen.
- GovKit does not trace imports. A helper outside the declared paths is not protected.
- A marker is counted as text, so a comment that mentions it counts.
- Nothing is protected by default. Without the section there is no such check.

See ADR 0027.

## One answer for a feature: done, continue or escalate

Add `--feature NAME` to a change run to get one answer for that feature:

```bash
pytest --junitxml=junit.xml          # run the tests
govkit evidence --record             # tie the results to this commit and working tree
govkit conform --request request.json --base origin/main \
  --policy-target ../policy --execute-check project:tests --feature 07_invoice_approval
```

The feature's [evidence report](EVIDENCE_REPORT.md) joins the change report as a required check, `evidence:feature`. The answer is one of three states.

| State | Exit | Meaning |
|---|---|---|
| `done` | 0 | Every required check passed, and every scenario and criterion has a current passing result |
| `continue` | 1 | Work is left that the agent can do |
| `escalate` | 3 | What is left needs a person |

With `--feature`, a run that could not start exits 2. A feature name that matches no feature directory is one such case. `evidence:feature` is reserved: a run with `--feature` is refused when the accepted configuration or a pack uses that identifier for its own check.

Every reason is listed. The state is the first of these that applies:

1. `escalate` when a reason in the first table below is present. A person is needed now, whatever else is open.
2. `continue` when a reason in the second table is present.
3. `escalate` when a reason in the third table is present.
4. `done` when there is no reason.

A person is needed now:

| Code | Meaning |
|---|---|
| `definition-changed` | `change:definition` failed: the change removed or altered part of the definition |
| `protected-changed` | `change:protected` failed: the change altered an existing test or a protected file |
| `result-error` | A test or evaluation ended in an error |
| `evidence-unreadable` | A definition or result file could not be read |
| `check-error` | A required check did not complete, for example a command that timed out |

The agent can act:

| Code | Meaning | What to do |
|---|---|---|
| `result-failed` | A scenario or criterion failed | Fix the implementation and run the tests again |
| `result-missing` | A scenario or a free criterion has no result | Run the tests and free evaluations, then record |
| `results-stale` | The commit, the working tree or a result file changed after the record | Run the tests again and record |
| `results-unrecorded` | There is no evidence record | Run `govkit evidence --record` |
| `record-unusable` | The evidence record cannot be read | Run the tests again and record |
| `check-failed` | Another check failed | Resolve its findings |

A person is needed once the agent has nothing left to do:

| Code | Meaning |
|---|---|
| `result-skipped` | A test was skipped |
| `result-owed` | A paid or human evaluation has no result |
| `skips-unmarked` | A result file counts skipped tests it does not mark |
| `criteria-not-compared` | The criteria are in the data form, which is not compared |
| `no-scenarios` | The feature has no scenarios |
| `check-not-satisfied` | A required check has no passing result, for example one that was not executed or a platform approval |
| `evidence-inconclusive` | The evidence is not a pass for another reason |

`--json` prints a `govkit.feature-verdict` document with the state, the reasons, the evidence report under `evidence` and the change results under `change`. Its schema is `governance/schemas/feature-verdict.schema.json`, and `governance/examples/feature-verdict/` holds an example. Without `--feature`, the command prints what it always did.

### Feature artifact checks

With `--feature`, the run also checks the feature's artifacts when the accepted profile selects them. These are the checks `govkit validate` runs on a legacy level 4 or 5 installation, chosen here by capability:

| Capability in the accepted profile | Checks added |
|---|---|
| `gherkin-delivery` | `completeness`, `gherkin-syntax`, `nfrs-no-tbd`, `nfrs-sections`, `eval-criteria`, `eval-prediction`, `gherkin-nfr-coverage` |
| `gherkin-delivery` and `llm-evaluation` | Also `llm-nfrs`, `l5-eval-criteria`, `l5-preflight-sections`, `agent-topology-exists`, `agent-topology-sections` |

Each appears as its own check, `feature:<identifier>`, for the selected feature only. A profile without `gherkin-delivery` gets none of them.

- **A failed check is work for the agent.** It gives `check-failed`, for example when `plan.md` is missing.
- **A check that could not decide needs a person.** It gives `check-not-satisfied`.
- **The forecast is advisory.** `feature:eval-prediction` reads the agent's own forecast in `plan.md`. It is never required and never a pass, so the report's overall state is a warning at best. The answer and the exit status are not affected.

`eval_criteria.yaml` is validated against the schema for the profile's project type:

```yaml
repository:
  id: invoices
  project_type: api      # api, cli, data, ui-react, ui-angular or ui-nextjs
```

The schema is the one bundled with the installed GovKit, not a copy in the checkout. When `project_type` is not set, the file's structure is still checked, schema validation is unknown, and the answer is `escalate` with `feature:eval-criteria` named. Set the project type in the accepted profile to resolve it.

These identifiers are reserved in a run with `--feature`. See ADR 0029.

Limits to know:

- **A local answer is a stop condition, not a gate.** A result file and its record do not prove that the tests ran. The run that counts is CI on a clean checkout.
- **Done is not approval.** It does not replace review, merge authorization or a release decision.
- **Record after the last run.** The evidence is read before `conform` executes any command. If a command it executes rewrites a result file, the next run reports the results as stale until you record again.
- **Ignore the result files.** A result file or record that Git does not ignore is part of the change, and must be covered by an impact rule.
- **Some checks cannot pass locally.** A required check such as a platform approval ends in `escalate`, and the answer names it.

See ADR 0028.

## Local/CI record and pilot

`--json` emits `kind: change-results`, versioned by
`change-results.schema.json`, containing Git identities/digests, the replayable
request plan, and the existing check/evidence report. Its summary and exit code
agree with the nested outcomes. `load_change_report()` validates and replays the
record; this verifies internal consistency, not authenticity or freshness. Keep
reports outside the inspected tree so writing a report does not itself become
another change. Explicit time/base/request/policy/check inputs yield equivalent
local and CI results; environment-dependent commands remain the caller's concern.

[The bundled pilot](../governance/examples/change-conformance/README.md) composes
the eight normalized request examples with an isolated ungoverned Git repository and separately
accepted policy. Tests exercise passing measurements, real failures, unchanged
source bytes/mtimes, and JSON replay with runtime-only dependencies. Architecture
measurements pass while unavailable platform approval remains unknown. These are
synthetic contract tests, not live team adoption or provider-enforcement evidence.
For existing installations, use [legacy migration](LEGACY_MIGRATION.md).
[Maintenance assessment](MAINTENANCE_ASSESSMENT.md) separately evaluates release,
resource, repository-fit and CI facts; a passing change does not establish
maintenance currency.
