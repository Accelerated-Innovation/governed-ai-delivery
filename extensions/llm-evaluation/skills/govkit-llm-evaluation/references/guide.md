# Guidance

Read the evaluation reference and accepted quality policy. Obtain actual outputs from the project's model runner; never replace them with expected outputs. From the repository root, run `govkit pack check --target . llm-exact-match -- --results evaluation-results.json`. Report the exit code and failures. This check only evaluates supplied records; it does not prove their origin or freshness, run a model, or replace broader quality/security evaluation.

A loaded skill is guidance, never evidence that a check passed. Accepted project policy remains authoritative. Removing this skill does not waive required controls.
