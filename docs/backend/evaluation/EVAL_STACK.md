# Evaluation Stack

This document defines the approved tooling for LLM evaluation and how each tool fits into the evaluation pipeline.

The *what* is defined in `eval_criteria.md`. This document defines the *how*.

---

# 1. Evaluation Architecture

Evaluation is modelled as a hexagonal concern. The home-grown evaluation framework defines the **evaluation port** — the contract that all features must satisfy. LangSmith and Arize are **outbound adapters** that implement observation and reporting against that contract.

```
┌─────────────────────────────────────┐
│         Evaluation Contract         │  ← eval_criteria.md (non-negotiable)
│   FIRST · 7 Virtues · LLM criteria  │
└──────────────┬──────────────────────┘
               │
       ┌───────┼───────────┐
       ▼       ▼           ▼
  Home-grown  LangSmith   Arize
  (CI gates)  (dev/test)  (production)
```

No single tool owns all three roles. Projects activate the adapters appropriate to their stage.

---

# 2. Tool Roles

## Home-Grown Evaluation Framework

**Role:** CI gate enforcement

**When:** Every build

Used to enforce the project's custom evaluation contract at CI time:

- FIRST score enforcement
- 7 Code Virtue score enforcement
- Feature-level `eval_criteria.yaml` thresholds
- Fail-fast on regression

This adapter is **required** on all projects. It is the only evaluation tool that blocks merges.

---

## LangSmith

**Role:** Development-time tracing and offline evaluation

**When:** Development and testing

Used to observe and evaluate LLM behaviour during development:

- LangGraph and LangChain run tracing
- Prompt versioning and comparison
- Offline dataset evaluation
- Regression detection across prompt changes

Rules:

- LangSmith tracing must be disabled in production by default (`LANGSMITH_TRACING=false`)
- Evaluation datasets must be stored in `eval_sets/` and versioned in git
- Projects not using LangGraph or LangChain may omit this adapter

---

## Arize

**Role:** Production monitoring and drift detection

**When:** Post-deployment

Used to monitor LLM behaviour in production:

- Embedding drift detection
- Output distribution monitoring
- Online evaluation at scale
- Performance degradation alerting

Rules:

- Arize instrumentation must live in `adapters/observability/`
- Domain layer must not reference Arize directly — route through `ObservabilityPort`
- Required on projects with production LLM features
- Optional on projects in early development

---

# 3. Pipeline by Environment

| Environment | Home-Grown | LangSmith | Arize |
|---|---|---|---|
| Local dev | optional | enabled | off |
| CI | required | optional | off |
| Staging | required | optional | optional |
| Production | required | off | required |

---

# 4. Project Configuration

Each project configures active adapters via environment variables:

```bash
# Home-grown (always on in CI)
GOVKIT_EVAL_ENABLED=true

# LangSmith
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=<project-name>

# Arize
ARIZE_API_KEY=...
ARIZE_SPACE_KEY=...
ARIZE_MODEL_ID=<model-name>
```

Secrets must use `BaseSettings` — never hardcoded.

---

# 5. Customisation for New Projects

When applying govkit to a new project, review:

- Which adapters are needed at this project's current stage
- Whether LangSmith is relevant (required only if using LangChain or LangGraph)
- Whether Arize is needed (required for production LLM features)
- The home-grown framework is always required — thresholds may be tuned in `eval_criteria.yaml`

---

# 6. When an ADR Is Required

An ADR must be created if:

- Replacing or removing the home-grown CI gate adapter
- Introducing a new evaluation tool not listed here
- Changing evaluation thresholds below the minimums defined in `eval_criteria.md`
