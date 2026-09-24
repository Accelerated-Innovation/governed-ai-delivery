# Maintenance posture example

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

This first example covers maintenance projection. The full scenario set, actual
change/evaluation reporting, fleet aggregation and voluntary adoption protocol
remain I11b in the implementation plan. No effectiveness claim follows from it.
