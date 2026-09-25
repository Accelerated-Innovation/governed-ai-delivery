---
name: govkit-llm-evaluation
description: Run the selected exact-match evaluation check on recorded model outputs.
---

# Llm Evaluation

Read the evaluation reference and accepted quality policy. Obtain actual outputs from the project's model runner; never replace them with expected outputs. From the repository root, run `govkit pack check --target . llm-exact-match -- --results evaluation-results.json`. Report the exit code and failures. This check only evaluates supplied records; it does not prove their origin or freshness, run a model, or replace broader quality/security evaluation.

Read [reference](references/guide.md). Use `govkit pack preview` and `govkit pack verify` to inspect the selected resources and controls. If only the source was copied with legacy `extension add`, complete explicit profile/pack setup before invoking a locked control.
