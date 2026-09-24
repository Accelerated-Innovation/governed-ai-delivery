# Posture examples

`maintenance.json` is a synthetic `posture-export` v1 record validated by the
runtime schema and replay parser. It projects a canonical local maintenance
assessment with a compatible optional pack update, matching installed resources
and unknown CI. References are opaque synthetic join keys, not live evidence or
permissions. No raw assessment, local path, source URL, developer identity or
request content is included.

Use `govkit posture export --assessment /private/assessment.json --json` to generate
a report from your own canonical assessment. See
[posture reporting](../../../docs/POSTURE_REPORTING.md) for the privacy boundary,
version display rules, source lookup, command exit status and publication choices.

`change.json` is a synthetic `change-posture` v1 record from real isolated change
conformance with a bounded workflow and passing independent LLM evaluation. It
preserves executed control/finding/action descriptors and accepted architecture
references, with no maintenance or provider-enforcement evidence. Generate one
using `govkit posture change --results /private/change-results.json --json`; see
[change posture](../../../docs/CHANGE_POSTURE.md).

Both examples validate/replay in tests and installed wheels. The scenario set
and replayable fleet below extend them. Synthetic results are not provider-health
or team-adoption evidence.

## Maintenance scenarios and an explicit fleet

The ten files in `scenarios/` are privacy-filtered exports produced through real
isolated profile/pack installations and canonical assessments. They contain
synthetic policy, discovery and CI inputs; a passing synthetic CI observation is
not evidence of live branch/reviewer enforcement. `tests/posture_scenarios.py`
constructs each scenario; runtime tests verify the action/identity/customization
contracts and the bundled records validate/replay in the installed wheel.

| File | What it demonstrates |
|---|---|
| `current.json` | Matching resources, compatible current versions, unchanged reviewed discovery and explicitly synthetic passing CI; all canonical maintenance dimensions pass |
| `optional-update.json` | Available compatible pack target, optional upgrade |
| `resource-drift.json` | Same installed version with user customization and reconciliation action |
| `changed-needs.json` | Current versions with new LLM use and a capability review |
| `incompatible.json` | Newer release excluded by runtime compatibility; no required upgrade |
| `unavailable.json` | Unavailable source/unknown freshness, with other dimensions still useful |
| `stale.json` | Old source metadata remains stale |
| `intentional-pin.json` | Compliant installed pin with a newer excluded release, no required upgrade |
| `required-upgrade.json` | Verified installed pack outside accepted version policy with a compatible target |
| `overlap.json` | Optional update, modified resource, changed needs and unknown CI all coexist |

`fleet.json` embeds these ten selected maintenance exports, the separate change
example and an explicit unassessed repository. Its cohort has 12 repositories:
ten maintenance snapshots, one change-only repository and one with neither kind.
Maintenance coverage is 10/12; change coverage is 1/12. The change has one executed
LLM evaluation. Category counts overlap and must not be summed as distinct repos.
All references are synthetic pseudonyms; the full aggregate replays offline.

Generate a corresponding report by passing each selected scenario file and the
change file as repeated `--report` arguments to `govkit posture aggregate`, and
passing every `cohort` reference from `fleet.json` as repeated `--repository-ref`
arguments, with `--as-of 2026-09-24T12:00:00Z --json`. No collector is required.
[Aggregation documentation](../../../docs/POSTURE_AGGREGATION.md) defines every
denominator and freshness rule; [the pilot protocol](../../../docs/ADOPTION_PILOT.md)
separates effort/usefulness evaluation from these synthetic conformance examples.
