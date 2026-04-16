# LLM Evaluation Rules

These rules apply when editing LLM evaluation tests and datasets.

Contract: `docs/backend/architecture/EVALUATION_LLM_CONTRACT.md`

---

## Rules

- DeepEval measures LLM output quality (faithfulness, relevancy, hallucination) — required for `mode: llm` features
- Promptfoo tests adversarial resilience (jailbreak, injection, regression) — required when user-facing
- RAGAS evaluates retrieval quality (context recall, precision) — required only for RAG features
- Each criterion in `eval_criteria.yaml` with a `deepeval_*` eval_class must have a corresponding test in `tests/eval/<feature>/`
- Evaluation datasets live in `tests/eval/<feature>/eval_sets/` and must be versioned in git
- DeepEval tests run via `deepeval test run` in CI
- Promptfoo configs use YAML format in `tests/eval/<feature>/promptfoo.yaml`
- RAGAS metrics run as part of the DeepEval test suite

## Tool Boundaries

- Do not use DeepEval for adversarial testing — Promptfoo owns this
- Do not use Promptfoo for quality metrics — DeepEval owns this
- Do not use RAGAS on non-retrieval features

## Prohibited

- Importing `deepeval`, `promptfoo`, or `ragas` outside `tests/eval/`
- Storing evaluation datasets outside version control
- Skipping DeepEval for `mode: llm` features
