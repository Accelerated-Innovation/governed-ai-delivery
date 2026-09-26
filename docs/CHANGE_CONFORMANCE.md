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

## Git scope, transitions and defects

The explicit base is resolved to a commit. The snapshot compares it with Git-visible
working-tree bytes, including committed changes since base, staged/unstaged edits,
untracked nonignored files, deletions and executable-mode changes. Renames appear
as add/delete. Repository-root inspection avoids partial-directory blind spots.
Bounds are 2,048 files per tree, 1 MiB per file, 16 MiB per tree and 256 changed
paths. Unsupported kinds (including symlinks/submodules), unavailable Git inputs,
unsafe paths and exceeded bounds leave scope incomplete and blocking.
Limit diagnostics identify the inventory or content budget exceeded, its limit,
and the observed count or byte size. Per-file diagnostics include a JSON-escaped
repository-relative path; bounded working-tree reads report a lower bound on size.
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
the seven normalized request examples with an isolated ungoverned Git repository and separately
accepted policy. Tests exercise passing measurements, real failures, unchanged
source bytes/mtimes, and JSON replay with runtime-only dependencies. Architecture
measurements pass while unavailable platform approval remains unknown. These are
synthetic contract tests, not live team adoption or provider-enforcement evidence.
For existing installations, use [legacy migration](LEGACY_MIGRATION.md).
[Maintenance assessment](MAINTENANCE_ASSESSMENT.md) separately evaluates release,
resource, repository-fit and CI facts; a passing change does not establish
maintenance currency.
