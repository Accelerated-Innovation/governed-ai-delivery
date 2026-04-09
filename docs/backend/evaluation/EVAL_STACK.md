# Evaluation Stack

This document defines the approved tooling for evaluation and how each tool fits into the evaluation pipeline.

The *what* is defined in `eval_criteria.md`. This document defines the *how*.

---

# 1. Evaluation Architecture

Evaluation is modelled as a hexagonal concern. The home-grown evaluation framework defines the **evaluation port** — the contract that all features must satisfy. Other tools are **outbound adapters** that implement observation, evaluation, and reporting against that contract.

```
┌──────────────────────────────────────────────┐
│            Evaluation Contract               │  ← eval_criteria.md (non-negotiable)
│   FIRST · 7 Virtues · LLM criteria          │
└──────────────┬───────────────────────────────┘
               │
       ┌───────┼──────────┬──────────┬──────────┐
       ▼       ▼          ▼          ▼          ▼
  Home-grown  DeepEval  Promptfoo  RAGAS    Langfuse
  (CI gates)  (quality) (safety)  (retrieval) (visibility)
```

No single tool owns all roles. Projects activate the adapters appropriate to their stage and feature type.

---

# 2. Tool Roles

## Home-Grown Evaluation Framework

**Role:** CI gate enforcement for FIRST and 7 Virtues

**When:** Every build, all levels

Used to enforce the project's code and test quality contract at CI time:

- FIRST score enforcement
- 7 Code Virtue score enforcement
- Feature-level `eval_criteria.yaml` thresholds
- Fail-fast on regression

This adapter is **required** on all projects. It is the only evaluation tool that blocks merges for code quality.

---

## DeepEval

**Role:** Feature-level LLM quality evaluation

**When:** Development and CI for features with `mode: llm`

Used to evaluate LLM output quality:

- Faithfulness (output grounded in context)
- Answer relevancy (response addresses the question)
- Hallucination detection (no fabricated facts)
- Contextual relevancy (retrieved context is relevant)
- Custom GEval criteria (LLM-as-judge with user-defined rubrics)

Rules:

- DeepEval tests live in `tests/eval/<feature>/`
- Evaluation datasets live in `tests/eval/<feature>/eval_sets/` and are versioned in git
- DeepEval is required for all features with `mode: llm` in `eval_criteria.yaml`
- CI enforcement via `deepeval-gate.yml`
- Do not use DeepEval for adversarial testing — Promptfoo owns that

---

## Promptfoo

**Role:** Adversarial and regression attack suites

**When:** CI for user-facing features or features processing untrusted input

Used to test LLM resilience:

- Jailbreak attempts
- Prompt injection attacks
- Toxic output elicitation
- Regression baselines across prompt/model changes

Rules:

- Promptfoo configs live in `tests/eval/<feature>/promptfoo.yaml`
- Architecture preflight must explicitly state whether Promptfoo is required
- CI enforcement via `promptfoo-gate.yml`
- Do not use Promptfoo for quality metrics — DeepEval owns that

---

## RAGAS

**Role:** Retrieval-specific evaluation

**When:** CI for RAG (retrieval-augmented generation) features only

Used to evaluate retrieval pipeline quality:

- Context recall (retriever finds all relevant documents)
- Context precision (retrieved documents are relevant, low noise)
- Faithfulness (generated answer is faithful to retrieved context)
- Answer relevancy (generated answer addresses the question)

Rules:

- RAGAS is required only when the feature uses retrieval
- RAGAS metrics run as part of the DeepEval test suite
- Architecture preflight must state whether RAGAS is required
- Do not use RAGAS on non-retrieval features

---

## Langfuse

**Role:** Trace storage, prompt versioning, and production evaluation visibility

**When:** Development through production

Used for:

- End-to-end request trace viewing (LLM calls, latency, cost)
- Prompt versioning and management (prompts managed in Langfuse, not in code)
- Evaluation result dashboards (DeepEval and RAGAS results visible in Langfuse)
- Production monitoring (latency trends, cost trends, error rates)

Rules:

- Langfuse SDK is imported only in `adapters/observability/`
- Domain layer must not reference Langfuse directly — route through `ObservabilityPort`
- Langfuse replaces LangSmith (dev tracing) and Arize (production monitoring)
- Required on projects with production LLM features

---

# 3. Pipeline by Environment

| Environment | Home-Grown | DeepEval | Promptfoo | RAGAS | Langfuse |
|-------------|-----------|----------|-----------|-------|----------|
| Local dev | optional | enabled | optional | optional | optional |
| CI | **required** | **required** (if mode: llm) | **required** (if preflight says so) | **required** (if RAG) | disabled |
| Staging | required | optional | optional | optional | enabled |
| Production | required | off | off | off | **required** |

---

# 4. Project Configuration

Each project configures active adapters via environment variables:

```bash
# Home-grown (always on in CI)
GOVKIT_EVAL_ENABLED=true

# DeepEval
DEEPEVAL_API_KEY=...            # Optional — for DeepEval cloud features
OPENAI_API_KEY=...              # Required — for LLM-as-judge metrics

# Promptfoo
PROMPTFOO_API_KEY=...           # Optional — for Promptfoo cloud dashboard

# Langfuse
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_HOST=...               # Self-hosted or cloud URL

# OpenLLMetry (telemetry emission)
TRACELOOP_BASE_URL=...          # OTel collector endpoint
```

Secrets must use `BaseSettings` — never hardcoded.

---

# 5. Customisation for New Projects

When applying govkit to a new project, review:

- Which evaluation adapters are needed at this project's current stage
- Whether DeepEval is relevant (required for `mode: llm` features)
- Whether Promptfoo is needed (required for user-facing LLM features)
- Whether RAGAS is needed (required for RAG features)
- Whether Langfuse is configured (required for production LLM features)
- The home-grown framework is always required — thresholds may be tuned in `eval_criteria.yaml`

---

# 6. When an ADR Is Required

An ADR must be created if:

- Replacing or removing the home-grown CI gate adapter
- Replacing DeepEval, Promptfoo, RAGAS, or Langfuse with a different tool
- Introducing a new evaluation tool not listed here
- Changing evaluation thresholds below the minimums defined in `eval_criteria.md`
- Disabling LLM evaluation for a production feature with `mode: llm`
