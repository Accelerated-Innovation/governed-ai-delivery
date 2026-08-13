# Evaluation Stack

This document defines the approved tooling for evaluation and how each tool fits into the evaluation pipeline.

The *what* is defined in `eval_criteria.md`. This document defines the *how*.

---

# 1. Evaluation Architecture

Evaluation is modelled as a hexagonal concern. `govkit evidence` defines the **evaluation port** — the contract that all features must satisfy. Other tools are **outbound adapters** that implement observation, evaluation, and reporting against that contract.

```
┌──────────────────────────────────────────────┐
│            Evaluation Contract               │  ← eval_criteria.md (non-negotiable)
│   FIRST · 7 Virtues · LLM criteria          │
└──────────────┬───────────────────────────────┘
               │
       ┌───────┼──────────┬──────────┬──────────┐
       ▼       ▼          ▼          ▼          ▼
  govkit      DeepEval  Promptfoo  RAGAS    Langfuse
  evidence    (quality) (safety)  (retrieval) (visibility)
  (CI gate)
```

No single tool owns all roles. Projects activate the adapters appropriate to their stage and feature type.

---

# 2. Tool Roles

## govkit evidence

**Role:** CI gate on measured quality evidence

**When:** Every build, L4+

`govkit evidence` reads the reports your test run produced and gives a verdict
per rubric dimension: `PASS`, `FAIL`, `INCONCLUSIVE`, or `ERROR`. It is wired up
by `ci/<platform>/evidence-gate.yml`.

It reads the standard XML test report every mainstream runner can emit, and — for
UI projects — accessibility results as JSON:

```bash
pytest --junitxml=junit.xml                       # python
npx vitest run --reporter=junit --outputFile=junit.xml   # node
# any runner that writes the same report format works; nothing is stack-specific
```

- Working — the test run had no failures
- Accessibility — no critical or serious axe violations
- Fast — blocking once the team sets `--fast-max-seconds`
- Everything else — `INCONCLUSIVE`, and **INCONCLUSIVE is not a pass**

This is the tool that blocks merges for code quality.

### What replaced what

Earlier versions of this document described a "Home-Grown Evaluation Framework"
that enforced FIRST and Virtue scores at CI time and was "required on all
projects". **No such framework was ever built.** The only implementation was a
parser that read the FIRST/Virtue numbers out of `plan.md` — numbers written by
the agent that did the work.

`docs/backend/evaluation/EVIDENCE_CONTRACT.md` names that a producer self-check
and makes it advisory: *"the task owner never commits its own final gate."* The
prediction gates still run and still report, but as a **planning forecast**, not
a quality verdict. Merge is gated on evidence.

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

| Environment | govkit evidence | DeepEval | Promptfoo | RAGAS | Langfuse |
|-------------|-----------|----------|-----------|-------|----------|
| Local dev | optional | enabled | optional | optional | optional |
| CI | **required** | **required** (if mode: llm) | **required** (if preflight says so) | **required** (if RAG) | disabled |
| Staging | required | optional | optional | optional | enabled |
| Production | required | off | off | off | **required** |

---

# 4. Project Configuration

Each project configures active adapters via environment variables:

```bash
# govkit evidence reads CI artifacts; no env var. Emit JUnit XML (and axe
# JSON for UI) from your test run and the evidence gate picks them up.

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

Secrets must come from your stack's typed settings mechanism — never hardcoded.

---

# 5. Customisation for New Projects

When applying govkit to a new project, review:

- Which evaluation adapters are needed at this project's current stage
- Whether DeepEval is relevant (required for `mode: llm` features)
- Whether Promptfoo is needed (required for user-facing LLM features)
- Whether RAGAS is needed (required for RAG features)
- Whether Langfuse is configured (required for production LLM features)
- `govkit evidence` is always required. Which dimensions it can judge depends on what your test run emits; set `--fast-max-seconds` to make per-test duration blocking

---

# 6. When an ADR Is Required

An ADR must be created if:

- Replacing or removing the `govkit evidence` CI gate
- Replacing DeepEval, Promptfoo, RAGAS, or Langfuse with a different tool
- Introducing a new evaluation tool not listed here
- Changing evaluation thresholds below the minimums defined in `eval_criteria.md`
- Disabling LLM evaluation for a production feature with `mode: llm`
