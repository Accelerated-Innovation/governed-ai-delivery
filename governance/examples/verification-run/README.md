# Verification run example

`verification-run.json` is what `govkit verification-run build` writes for the feature in `../evidence-report/`, with that example's result files and record.

The baseline is `acceptance.baseline.feature` and the example's own `eval_criteria.yaml`. The baseline lacks one scenario and holds another with different text, so the document shows three results that are sent and five that are left out: one `not-in-baseline`, one `revision-changed` and three `no-result`.

Only `request` would be sent to the Product Definition Graph. `tests/test_verification_run.py` rebuilds this file from its inputs and compares it; `tests/wheel_evidence_smoke.py` validates it from a clean wheel.

The repository, run reference, addresses, commit and time identify nothing outside this example.
