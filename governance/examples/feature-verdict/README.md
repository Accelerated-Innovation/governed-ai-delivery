# Feature answer example

`feature-verdict.json` is what `govkit conform --request ... --feature 07_invoice_approval --json` printed for a real change in a temporary repository: one scenario failed and one test was skipped, so the state is `continue`, and the skipped test is listed as a reason for a person.

The document holds the evidence report under `evidence` and the change results under `change`. `parse_feature_verdict` in `cli/change_conformance.py` validates all three and recomputes the answer from the two reports; `tests/test_change_verdict.py` and `tests/wheel_change_smoke.py` replay this file.

The commit, digests and time are those of the temporary repository. They identify nothing outside this example.
