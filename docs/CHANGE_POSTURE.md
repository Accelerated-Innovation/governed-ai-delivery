# Change posture reports

`govkit posture change` projects saved canonical `change-results` into a versioned,
privacy-filtered `change-posture` report. Run
[actual-change conformance](CHANGE_CONFORMANCE.md) first to capture trusted policy,
request obligations and the controls that ran.

```sh
govkit posture change --results /private/change-results.json
govkit posture change --results /private/change-results.json --json
govkit posture change --results /private/change-results.json \
  --target /work/project --output /private/change-posture.json --json
```

Default output is human-readable; `--json` selects deterministic JSON. Export
success exits zero even if conformance failed: the source state, summary and exit
code remain in `results`. This is an export operation, not a gate. Invalid input
or output exits one; invalid CLI syntax exits two. Export never reinspects the
checkout, executes checks, refreshes metadata or transmits content.

## Recorded facts and coverage

| Field | Meaning |
|---|---|
| `repository_ref`, `report_ref`, `as_of` | Pseudonymous repository/source identity and original observation time, not export time |
| `identity` | Revision, Git-visible tree, profile, request plan, pack lock, actual change and base references |
| `running_cli` | Producer's public version and exact-value reference; private local version labels are omitted |
| `capabilities` | Configured, repository-required, lock-recorded and change-required capabilities |
| `configured_controls` | Policy declarations, including conditional workflow declarations, explicitly `not-assessed` |
| `workflow` | Replayed category, three-valued impact flags, scope/requirement/artifact/reassessment references and blocking decisions |
| `architecture` | Accepted contracts and scoped current/target transitions, modes, applicability and exception expiry; no architecture text |
| `results.controls` | Every control's required status, canonical state/execution, evidence descriptors, finding/action references and private-source lookup pointer |
| `coverage` | Explicit snapshot origin and unsupplied maintenance, discovery and provider-enforcement coverage |

Configured controls are declarations. Presence does not establish that a
conditional rule applied or a check executed. `workflow.requirements` records
selected obligations; `results.controls` contains actual recorded outcomes,
including additional conformance guards. Export rejects missing/weakened planned
controls and repository identity that contradicts the replayed profile.

Canonical `pass`, `fail`, `warn`, `unknown`, `skipped`, `waived` and
`not-applicable` remain distinct from `executed`, `not-run` and `error`. Execution
errors stay unknown even with an error-severity finding. Required unknown,
skipped, waived and not-applicable results are not satisfied under the canonical
aggregation rules. Not-applicable is not relabeled as a failed check; an optional
not-applicable result need not block the gate. There is no new compliance score.

`llm-exact-match` is a public check label; other IDs are referenced. The label names
the source identifier, not proof of provider authenticity or general model quality.
Custom evaluations retain references, outcomes and evidence. Independent LLM
evaluation remains visible for bounded changes; unexecuted evaluations never pass.

## Privacy and source lookup

The [maintenance posture](POSTURE_REPORTING.md) allowlist/reference rules apply:
no raw request, prompt, ticket, code, command output, finding prose, developer
identity, arbitrary URL or local filename is copied. Free text and custom IDs
become category-scoped references. These are pseudonymous, not anonymization or
access controls; guessable values can be correlated.

`local_ref` is a JSON Pointer into the private source. Follow a control pointer to
read its full reasons, findings, evidence and suggested actions. Human output
includes the same control states and finding/action references as JSON. Keep the
source private and inspect exports before sharing. Schema/digest/replay validation
establishes consistency, not authenticity, approval or current health.

## Publication and separate snapshots

`--output` requires `--target`, since canonical change results do not record a
checkout's filesystem root. Select the protected checkout explicitly; export does
not verify the source against that path. The flags must be supplied together.
The existing artifact writer creates private JSON outside that target and refuses
existing files/symlinks, retaining its POSIX/concurrent-writer limitations. For CI,
explicitly upload only the new JSON using the
[posture publication guidance](POSTURE_REPORTING.md#safe-local-and-ci-publication).

Maintenance and change are separate snapshot contracts. A change carries a
request-plan identity and base-specific Git-visible tree; maintenance uses
installation resolution and inventory observations. Never join them as one
execution solely because repository references match. Installed versions,
release candidates, resource drift and discovery are not supplied here; use
`posture export` for maintenance facts. Local results do not establish provider
enforcement. Old observations remain old when exported again.

I11c retains fleet aggregation, freshness/coverage denominators, the complete
maintenance scenario set and the separate voluntary team adoption protocol.
No collector, automatic telemetry, individual tracking or productivity metric is
introduced.
