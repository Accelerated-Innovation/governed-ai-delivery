# ADR 0024: The evidence record and result freshness

Status: Proposed with the L05 PR for #263. Merging that PR accepts the contract below.

## Context

`govkit evidence --feature` (ADRs 0022 and 0023) read whatever result files it found. A JUnit file or an evaluation results file from an earlier run looked the same as a fresh one, so a feature could report `PASS` for code edited after the tests ran, or for another commit. The evidence contract says evidence must be scoped to the exact commit it describes and that stale evidence is `INCONCLUSIVE`.

Something has to note the commit and working tree at the moment the tests run. Test runners do not, and each has its own output format.

The maintainer decided on 2026-11-24: GovKit records the commit and tree in a separate step, and results with no record are `INCONCLUSIVE`.

## Decision

1. **A record step.** `govkit evidence --record` writes `govkit-evidence-record.json` in the target: the commit, a working tree digest, the time, and the path and SHA-256 of each result file. Schema `evidence-record` version 1.
2. **Results count only while the record holds.** The report compares each result file it reads, the commit and the working tree digest with the record. Any difference is `stale`. No record is `unrecorded`. Both make the feature `INCONCLUSIVE`.
3. **What stale results said stays visible.** Scenario and criterion states are unchanged, and the detail repeats the finding. Only its authority is removed. An `ERROR` is not softened.
4. **The working tree digest comes from Git, by difference.** `tree_identity.py` hashes the commit, the index and the content of every file Git reports as modified, deleted or untracked. It asks Git which files differ instead of reading every file, so the cost follows the size of the change. It is read-only.
5. **The result files and the record are left out of the digest.** A test run rewrites them, and that must not make its own results stale. The set left out is the record's own list, so it is the same when recording and when checking.
6. **The whole repository is observed**, also for a target below its root, and each submodule checked out inside it is described by its own commit and changes. Git is run without inherited repository-location variables, and an index that changes during the observation makes it unavailable.
7. **The record is its own step.** `--record` cannot be combined with `--feature` or `--json`. Recording inside the report would make every result current.
8. **An unusable record is not "no record".** It is `unavailable`, so a damaged record cannot pass as an absent one.
9. **The report gains `provenance`**: state, detail, commit, tree digest and record time.

## Alternatives considered

- **GovKit runs the tests** and writes the record around the run. A record could not exist without a run. It makes GovKit execute project commands, which needs the opt-in and isolation rules the repository applies elsewhere. Left for later.
- **The test run writes it**, as a JUnit property and fields in the results file. Every runner would need a hook that computes the same digest GovKit does.
- **Warn only when there is no record.** A pass could still rest on an old file.
- **Hashing every file Git sees**, as `change_scope.py` does within fixed limits. A large repository would exceed the limits and could never be shown current.
- **Modification times.** Unreliable across checkouts and tools.

## Consequences

- An honest mistake is caught: results from before an edit or from another commit no longer count.
- Every project must add the record step before a feature can pass. This is a behaviour change for anyone using `--feature` from the unreleased L03 and L04.
- The record can be written again without running the tests. It is an observation by the party that ran them, not proof. Locally a `PASS` remains a stop condition; CI on a clean checkout is the gate.
- The target must be inside a Git repository with at least one commit.
- An untracked file that Git does not ignore, written by any tool after the record, makes results stale. Projects should ignore build outputs.
- `--record` is the first option of this command that writes a file. It writes only the record, refuses to write through a link, replaces the previous record in one step, and leaves it untouched when it fails.
- The record's fields, the provenance states and the record's file name are public. Add, never rename.
