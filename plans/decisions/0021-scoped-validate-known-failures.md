# ADR 0021: Feature-scoped validate and the known-failures record

Status: Proposed with the L01 PR for #248. Merging that PR accepts the
contract below.

## Context

`govkit validate` checks every feature directory and exits non-zero when any
one fails. Checks are added over time, so a repository accumulates older
features that fail checks written after them. In a level 5 pilot repository
with 30 feature packages on govkit 0.23.0, 10 packages failed for that reason
and the command exited 1 on every run. People read the output by eye and
ignored the exit status.

Two things were missing. The command could not be narrowed to the features
being worked on. And a check was a function returning a status and a message,
so nothing durable identified the same failure between two runs.

`govkit validate-baseline` already uses "baseline" for an approved behavioural
baseline of a specification. The first increment of
`plans/LOOP_READY_GATES_PLAN.md` (L01) addresses both gaps without that word.

## Decision

Add `--feature`, `--known-failures`, `--known-failures-digest` and
`--print-known-failures` to `govkit validate`, one versioned record contract,
and stable identifiers for every result `validate` reports.

- **No change without the options.** With none of the four options the command
  calls the existing runner. Output and exit status are byte-identical.
  Identifiers and the new summary line appear only when an option is used.
- **Selection.** `--feature` is repeatable and matches a feature directory name
  exactly. A name that matches nothing is an error. Repository-level checks
  (extensions, fix records, approval policy) still run in a scoped run.
- **Identity.** A failure is identified by scope, check identifier and an
  optional finding code. Message text is never part of identity.
  - Scope is typed: `feature`, `extension`, `fix` or `approval`.
  - `completeness` reports one finding per missing or empty artifact.
  - `architecture-experiments` uses the assessor's finding code, joined to the
    experiment identifier when there is one.
  - Other checks have no finding code. For those, identity is the check.
- **Record.** `known-failures` v1 lists accepted failures by that identity.
  - A listed failure is known and does not fail the run.
  - An unlisted failure is new and fails the run.
  - A listed failure that now passes is resolved. It fails the run only under
    `--strict`.
  - An entry that does not apply to the run is ignored: a feature outside the
    selection, a check the run did not evaluate, or a finding that is only a
    warning without `--strict`.
  - An entry for a feature directory that no longer exists is resolved.
  - A check identifier GovKit does not know for the scope kind makes the
    record invalid.
- **Authority.** GovKit never writes, updates or accepts a record.
  `--print-known-failures` prints one to stdout for the caller to review and
  save. A record that is missing, unreadable, malformed or invalid stops the
  run. It is never read as empty.
- **Location and pinning.** The record may be at any path, including inside
  the inspected tree. The output states which and prints the SHA-256 digest of
  the record's bytes. `--known-failures-digest` fails the run when the digest
  differs.
- **Conform is unchanged.** `govkit conform` keeps its positional feature
  codes. Aligning them is #253.

## Consequences and boundary

A passing scoped or known-failures run shows artifact consistency for the
selection, apart from the listed failures. It is not review, approval or
evidence that a project control ran. A valid record is well-formed; it is not
evidence of review, and its digest authenticates nothing about who produced
it.

Identity at check level is coarse where a check has no finding code. A known
check that later fails for a different reason is still reported as known.
Finer finding codes can be added per check later; adding one changes the
identity of that check's failures, so it needs a record schema version or a
migration note.

Check identifiers are now a public contract. They may be added but not
renamed.

A change can edit an in-tree record to hide its own failures. This increment
only makes that detectable through the printed digest and the pin. Checking
protected paths against the actual diff is L04. Treating skipped or degraded
checks as unknown is L03. Structured output is L06.

Validation is test first: the acceptance criteria in #248 as unit tests, a
parity test between the named and legacy check lists, schema and example
tests, and a runtime-only wheel smoke for all three agents.
