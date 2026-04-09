# LLM Evaluation Instructions

These instructions apply when editing files in `**/tests/eval/**` and `**/eval_sets/**`.

Contract: `docs/backend/architecture/EVALUATION_LLM_CONTRACT.md`

---

- DeepEval = quality metrics (faithfulness, relevancy, hallucination) — required for `mode: llm`
- Promptfoo = adversarial testing (jailbreak, injection, regression) — required when user-facing
- RAGAS = retrieval metrics (context recall, precision) — required only for RAG features
- Each `deepeval_*` criterion in `eval_criteria.yaml` must have a corresponding test
- Evaluation datasets live in `tests/eval/<feature>/eval_sets/` — versioned in git
- Promptfoo configs use YAML in `tests/eval/<feature>/promptfoo.yaml`

**Tool boundaries:** Do not use DeepEval for adversarial testing. Do not use Promptfoo for quality metrics. Do not use RAGAS on non-retrieval features.

**Prohibited:** Importing eval tools outside `tests/eval/`. Storing datasets outside version control.
