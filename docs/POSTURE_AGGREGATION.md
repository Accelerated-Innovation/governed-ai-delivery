# Aggregate selected posture snapshots

`govkit posture aggregate` summarizes existing privacy-filtered maintenance and
change exports without a collector, network connection or repository inspection.
Supply the expected cohort, including repositories without an assessment:

```sh
govkit posture aggregate \
  --repository-ref ref:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --report /private/selected-maintenance.json \
  --as-of 2026-09-24T12:00:00Z --max-age-hours 24 --json
```

Replace the illustrative reference with the `repository_ref` from an export.
Repeat `--repository-ref` for every expected repository and `--report` for each
selected export. Omitting all reports is valid and shows the whole cohort missing.
Do not pass raw maintenance assessments or change results: first use `posture
export` or `posture change`. Omit `--json` for a human summary with the same counts
identified by their JSON paths. Successful aggregation exits zero even with missing
or failing evidence; it is not a conformance gate.

## Selection, identity and replay

Select at most one maintenance and one change export per repository. Identical
repeated exports are ignored. Conflicting snapshots, duplicate cohort entries,
unknown report kinds and reports outside the roster are rejected before output.
There is no implicit latest-wins rule. Choose the intended observation before
invoking the command; this is a cohort snapshot, not a history of every change.

Maintenance and change snapshots remain separate. A shared repository reference
never establishes matching revision, profile, request or evidence. Their complete
privacy-filtered identities, findings and actions remain in `snapshots`. The strict
`posture-aggregate` v1 schema embeds both export schemas. `parse_aggregate` validates
them, replays their source contracts and recomputes every observation/count from the
roster and explicit clock. Changing the summary and recomputing its digest cannot
make incorrect counts valid. Replay is consistency checking, not authentication.

## Denominators and overlapping categories

No overall health, maturity, compliance or productivity score is emitted. Counts
are facts about supplied snapshots. A zero denominator means no observations, never
100% coverage or a pass. `summary.repositories` is the distinct explicit cohort size.

| Fields | Unit and denominator |
|---|---|
| `maintenance.assessed_repositories`, `changes.assessed_repositories` | Repositories with a selected snapshot of that kind / entire cohort |
| Each kind's `missing_repositories` | Entire cohort minus that kind's selected snapshots |
| Each kind's `freshness` | Fresh, stale, undated/unknown or future snapshots / selected snapshots of that kind |
| Each kind's `capabilities` | Repositories declaring, requiring or recording that capability / entire cohort; missing snapshots are not declarations, and recorded locks need not be verified |
| `maintenance.categories` | Repositories with that canonical fact / selected maintenance snapshots; report missing coverage alongside these counts |
| `maintenance.fresh_categories` | The same facts in fresh maintenance snapshots / **all** selected maintenance snapshots, including stale/undated ones; compatible updates additionally require fresh release metadata |
| `maintenance.dimensions[].counts` | Recorded maintenance outcomes for that dimension / selected maintenance snapshots; these are not project-check execution |
| `changes.controls` | Recorded control occurrences / selected change snapshots; control IDs in different repositories remain separate occurrences |
| `changes.evaluations` | The subset explicitly labeled `llm-exact-match`; arbitrary custom controls are not inferred to be evaluations |

Control and evaluation counts include `total`, `applicable` (all states except
`not-applicable`), and `required` (including required not-applicable records).
`states` preserves all seven canonical outcomes; `execution` separately counts
executed, not-run and error. `fresh_executed_passes / applicable` is the explicitly
defined fresh-pass fraction, if requested by a downstream consumer. Unknown,
skipped and waived controls remain in that denominator and never in its numerator.
Not-applicable is reported separately, not as failure. For mandatory obligations
use `fresh_required_passes / required`; a required not-applicable record cannot
satisfy an obligation. Both numerators require an executed canonical pass in a
fresh selected snapshot. The release maintenance dimension additionally requires
fresh release metadata; a recent assessment cannot refresh an old source. An executed failing evaluation is execution evidence,
not a passing evaluation. Maintenance counts cannot fill missing change evidence.

Category definitions:

| Category | Canonical fact counted once per maintenance repository |
|---|---|
| `compatible_updates` | A candidate has a selected target; no version comparison or upgrade choice is re-derived |
| `required_upgrades` | A required `upgrade-cli` or `upgrade-pack` recommendation |
| `resource_drift` | At least one missing or modified resource; unavailable resources stay visible in source facts and dimension unknowns |
| `governance_reviews` | A `review-policy` or `review-capability` recommendation |
| `ci_repairs` | A `repair-ci` recommendation; unknown CI can need repair without proving failure |
| `compliant_pins` | A pinned candidate whose canonical installed-policy state is compliant; this is not a general compliance verdict |
| `fresh_metadata` | Candidate/source coverage exists, all lookup/timestamp facts are known within the reporting window, and no candidate is canonically stale/unknown |
| `stale_metadata`, `unknown_metadata` | Any stale or unknown source/candidate; missing comparison coverage is unknown; these categories can overlap |

Never sum categories as a count of distinct repositories. An optional update, drift,
capability review and CI repair can all concern the same repository. A compliant
pin can coexist with known newer excluded versions without a required upgrade;
inspect the embedded candidate exclusions and action references for that distinction.

## Time, privacy and storage

`--as-of` is required and timezone-aware; the default age window is 24 hours and
can be explicitly changed. It is a reporting filter, not a replacement for accepted
policy. Age is the elapsed hours from the source observation, never a new export
time. Exactly the configured age limit remains fresh; later observations are stale.
Future/undated records have no usable age and cannot supply fresh-pass numerators.
Release source timestamps are evaluated against this window too. Unknown/future
lookup times or a source timestamp later than its lookup are unknown evidence;
canonical stale
or unknown flags are retained even with a longer window. Historical actions remain
visible under `categories` and in the source snapshots, with age beside them.

The aggregate contains only the supplied strict export allowlists and fixed count
fields. No developer identity, raw code, request/prompt/ticket, credential, path,
source URL or new behavioral telemetry is added. Pseudonymous references can still
be correlated; they are not anonymization or access controls. Review every artifact
before sharing. No network request or automatic transmission is performed.

Stdout is the only destination of this command. The caller controls storage,
permissions, retention and any explicit CI artifact upload; publish only the reviewed
aggregate, never raw source assessments or a containing directory. Existing
[per-repository private publication](POSTURE_REPORTING.md#safe-local-and-ci-publication)
continues to protect its selected target. No repository file is written by aggregation.

The [scenario examples](../governance/examples/posture/README.md) demonstrate these
counts offline. The [voluntary team pilot](ADOPTION_PILOT.md) measures usefulness
and effort separately. Synthetic examples are not team-adoption evidence.
