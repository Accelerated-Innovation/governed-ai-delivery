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

Both examples validate/replay in tests and installed wheels. The complete
maintenance scenario set, fleet aggregation and voluntary adoption protocol
remain I11c. Synthetic results are not provider-health or team-adoption evidence.
