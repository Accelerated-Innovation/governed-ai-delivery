# Feature-scoped validate and known failures

`govkit validate` checks every feature and exits non-zero when any one of them
fails. In a repository with older features that fail checks added after they
were written, that exit status cannot tell someone working on a new feature
whether their own work is clean.

Two additions make the exit status usable again:

- `--feature` narrows the run to the features being worked on.
- `--known-failures` names a reviewed record of failures accepted as already
  existing, so only failures outside that record fail the run.

With none of the four options described on this page, `govkit validate`
behaves and prints exactly as before.
No check or threshold changes. The contract is recorded in
[ADR 0021](../plans/decisions/0021-scoped-validate-known-failures.md).

## Checking selected features

```bash
govkit validate --target . --feature order_export
govkit validate --target . --feature order_export --feature billing_sync
```

- Only the named feature directories under `features/` are checked and counted.
- A name that matches no feature directory is an error with a non-zero exit.
  It is never an empty passing run. Starter directories (`starter_*`) cannot be
  selected, because `validate` never checks them.
- `--level`, `--strict` and `--only experiments` combine with `--feature` as
  they do without it.
- At level 3 there are no per-feature artifacts, so the command says so, as
  the unscoped command does. Feature names are not checked at level 3,
  because a level 3 project has no `features/` directory to match against.

Repository-level checks are not per-feature. Extension manifests, fix records
and the ADR approval policy still run and still count in a scoped run.

## Check identifiers

A run that uses any of the new options prints an identifier in brackets on
every result line:

```text
features/order_export/
  FAIL  [completeness/plan.md] plan.md is missing
  PASS  [gherkin-syntax] acceptance.feature has valid Gherkin structure
  FAIL  [nfrs-no-tbd] nfrs.md contains TBD entries

1 feature(s) selected: 2 new failure(s), 0 known, 0 resolved
```

The part before the slash is the check. The part after it, when present, is a
finding code that separates distinct failures of one check:

| Check | Finding code |
|---|---|
| `completeness` | The artifact that is missing or empty, one line per artifact. |
| `architecture-experiments` | The finding code, followed by `:` and the experiment identifier when the finding belongs to one experiment. |
| Every other check | None. |

Per-feature checks: `completeness`, `gherkin-syntax`, `nfrs-no-tbd`,
`nfrs-sections`, `eval-criteria`, `eval-prediction`, `gherkin-nfr-coverage`,
`architecture-experiments`, and at level 5 `llm-nfrs`, `l5-eval-criteria`,
`l5-preflight-sections`, `agent-topology-exists` and `agent-topology-sections`.

Repository-level checks: `extension-manifest`, `fix-record` and
`approval-policy`.

Identifiers are stable. Message text is not, and nothing matches on it.
`govkit conform` still labels the same feature checks by position; aligning
the two is tracked in
[#253](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/253).

## The known-failures record

The record is a JSON file that lists failures by scope, check and finding
code. The schema is `governance/schemas/known-failures.schema.json`, with an
example in `governance/examples/known-failures/`.

```json
{
  "schema_version": 1,
  "kind": "known-failures",
  "known_failures": [
    {
      "scope": { "kind": "feature", "name": "order_export" },
      "check": "completeness",
      "finding": "plan.md",
      "note": "Written before plan.md was required."
    },
    { "scope": { "kind": "fix", "name": "fixes/task-filter-reset/fix.yaml" }, "check": "fix-record" },
    { "scope": { "kind": "approval" }, "check": "approval-policy" }
  ]
}
```

| Scope kind | Name |
|---|---|
| `feature` | The feature directory name. |
| `extension` | The extension id. |
| `fix` | The fix record path, relative to the repository root. |
| `approval` | No name. |

An entry without a `finding` matches only a failure that has no finding code.
`note` is for reviewers; GovKit does not read it.

### Creating a record

```bash
govkit validate --target . --print-known-failures > ../known-failures.json
```

`--print-known-failures` prints the current failures in the record format in
place of the report, and exits 0. It honours the same `--feature`, `--level`,
`--strict` and `--only` selection as a normal run.

GovKit never writes the record and never treats printed output as accepted.
Review the output, remove anything that should be fixed and not accepted, and
save it yourself. The output is sorted and carries no timestamp, so the same
failures always produce the same bytes.

### Running against a record

```bash
govkit validate --target . --known-failures ../known-failures.json
```

| Situation | Reported as | Fails the run |
|---|---|---|
| A failure listed in the record | `KNOWN` | No |
| A failure not listed in the record | `FAIL` | Yes |
| A listed failure that now passes | `RESOLVED` | Only with `--strict` |

The closing line counts all three:

```text
30 feature(s) selected: 0 new failure(s), 14 known, 1 resolved
```

Under `--strict` a resolved entry fails the run. A stale entry would report a
later regression of the same check as known, so CI should force the record to
shrink.

Some entries do not apply to a given run. They are ignored, counted on a final
line, and never reported as resolved:

- an entry for a feature outside the `--feature` selection;
- an entry for a check the run did not evaluate, for example any check other
  than `architecture-experiments` under `--only experiments`, or a level 5
  check at level 4;
- an entry for a finding that fails only with `--strict` and is a warning in
  this run.

An entry for a feature directory that no longer exists is reported as
resolved, unless a `--feature` selection leaves it out. Then it is ignored
like any other entry outside the selection.

A record holds at most 5000 entries and 1 MiB. `--print-known-failures` exits
non-zero without printing when the current failures would exceed either
limit; narrow the run with `--feature`.

A record that is missing, unreadable, malformed, invalid against the schema,
or that names a check identifier GovKit does not know, stops the run with a
non-zero exit before any check is reported. It is never treated as an empty
record. Duplicate entries are also invalid.

### Where the record lives, and pinning it

The record may be at any path, including inside the repository. The output
states which, and prints the record's SHA-256 digest:

```text
Known-failures record: known-failures.json (inside the inspected tree)
  digest: sha256:5f2c…
```

A record inside the repository can be edited by the same change it is meant to
check. To pin the reviewed bytes, pass the digest:

```bash
govkit validate --target . --known-failures known-failures.json \
  --known-failures-digest 5f2c…
```

The run exits non-zero when the digest differs. The value may carry a
`sha256:` prefix. Keep the expected digest somewhere the change cannot edit,
such as a protected CI variable.

## What this does not show

- A passing run shows that the selected artifacts are consistent, apart from
  the failures the record lists. It is not review, approval or evidence that a
  project control ran.
- A valid record is well-formed. Nothing shows that anyone reviewed it.
- Matching is by check and finding code. A known check that now fails for a
  different reason, with the same identifier, is still reported as known.
- Warnings are unchanged. A check that is skipped or degraded, such as the
  `check-jsonschema` warning, still prints `WARN` and does not fail the run.
- GovKit does not stop a change from editing an in-tree record. Pin the digest.
- Output is text. Structured results are a later increment.
