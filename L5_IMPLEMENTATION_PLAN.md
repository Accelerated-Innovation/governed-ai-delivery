# Level 5 Implementation Plan — GenAI Evaluation and Operations Stack

> Produced 2026-04-09. This is the source of truth for L5 implementation work.
> Each increment is designed to be independently committable.
> Do not modify unrelated repository areas.

---

## Context

Level 3 (Spec-Driven) and Level 4 (Governed AI Delivery) are complete. Teams using L4 have architecture contracts, FIRST/Virtues scoring, and boundary enforcement — but the evaluation tooling for LLM-specific features is stubbed. EVAL_STACK.md references LangSmith and Arize as placeholders, and `eval_criteria.yaml` has only 6 generic `eval_class` values.

Level 5 adds a concrete, non-overlapping GenAI operations stack so teams building LLM features have governed tooling for model routing, observability, evaluation, safety, and retrieval quality — all within the existing governed-ai-delivery model.

---

## Tool Ownership (non-overlapping — MUST enforce)

| Tool | Sole Responsibility |
|------|-------------------|
| **LiteLLM** | Model routing, fallback, provider abstraction — the ONLY LLM gateway |
| **OpenLLMetry** | Telemetry emission standard (OpenTelemetry for LLMs) |
| **Langfuse** | Trace storage, prompt versioning, production evaluation visibility |
| **DeepEval** | Feature-level LLM evaluation in dev and CI |
| **Promptfoo** | Adversarial and regression attack suites |
| **NeMo Guardrails** | Runtime conversational safety (dialog flow control) |
| **Guardrails AI** | Structured output validation (schema enforcement on LLM responses) |
| **RAGAS** | Retrieval-specific evaluation only (RAG pipelines) |

---

## Cross-Agent Architecture

1. **Contracts (source of truth)** → `docs/backend/architecture/` — 4 new contracts
2. **Schemas (machine enforcement)** → `governance/schemas/` + `governance/backend/schemas/`
3. **Guides (practical how-to)** → `docs/backend/guides/` — NEW directory, 8 guides
4. **Agent adapters** → rules/skills (Claude Code), instructions/prompts (Copilot) — reference contracts, never duplicate

---

## Increment 1: Architecture Contracts --- COMPLETED

**Dependencies:** None — foundation for everything else.

### New files

| File | Purpose |
|------|---------|
| `docs/backend/architecture/LLM_GATEWAY_CONTRACT.md` | LiteLLM as sole gateway. No direct provider SDK calls for chat/completion. LiteLLM client lives in `adapters/llm/`. LangGraph/LangChain route through LiteLLM. Fallback/retry config ownership. Cost tracking. ADR triggers. |
| `docs/backend/architecture/OBSERVABILITY_LLM_CONTRACT.md` | OpenLLMetry emits, Langfuse stores. Auto-instrumentation of LiteLLM calls. Langfuse as adapter behind `ObservabilityPort`. Prompt versioning in Langfuse. Environment matrix (local: optional, CI: off, staging: optional, prod: required). |
| `docs/backend/architecture/GUARDRAILS_CONTRACT.md` | NeMo = conversation flow safety (dialog rails, topic boundaries, jailbreak prevention). Guardrails AI = structured output validation (JSON schema enforcement). Mode selection: `nemo`, `guardrails-ai`, `both`, `none`. Both are adapters in hexagonal model. |
| `docs/backend/architecture/EVALUATION_LLM_CONTRACT.md` | DeepEval = quality metrics (faithfulness, relevancy, hallucination) in dev/CI. Promptfoo = adversarial/regression suites (red-teaming, jailbreak). RAGAS = retrieval-only metrics (context recall, precision). No overlap. Integration with eval_criteria.yaml. |

### Modified files

| File | Changes |
|------|---------|
| `docs/backend/architecture/TECH_STACK.md` | Add sections: "4a. LLM Gateway" (LiteLLM), "10a. LLM Evaluation" (DeepEval, Promptfoo, RAGAS), update "11. Observability" (add OpenLLMetry + Langfuse), add "11a. Runtime Guardrails" (NeMo, Guardrails AI). Update decision matrix to route all LLM calls through LiteLLM. |
| `docs/backend/architecture/AGENT_ARCHITECTURE.md` | Update section 7 (tool integration — LLM calls through LiteLLM adapter), section 9 (observability — OpenLLMetry for LLM tracing), section 10 (evaluation — DeepEval/Promptfoo/RAGAS). Add section 16 "Guardrails Integration" (NeMo + Guardrails AI in agent graphs). |
| `docs/backend/evaluation/EVAL_STACK.md` | Replace LangSmith with Langfuse (dev + prod visibility). Replace Arize with Langfuse. Add DeepEval (CI evaluation). Add Promptfoo (adversarial). Add RAGAS (retrieval). Keep home-grown for FIRST/Virtues. Update environment matrix and config section. |

---

## Increment 2: Practical Usage Guides --- COMPLETED

**Dependencies:** Increment 1 (guides reference contracts)

### New files — all in `docs/backend/guides/`

| File | Content |
|------|---------|
| `litellm-setup.md` | Proxy config, model aliases, fallback chains, cost tracking, environment variables |
| `openllmetry-setup.md` | Auto-instrumentation, custom span attributes, export to Langfuse |
| `langfuse-integration.md` | Project setup, trace viewing, prompt management, production dashboard |
| `deepeval-usage.md` | Test cases, metric types (GEval, Faithfulness, AnswerRelevancy), CI integration, datasets |
| `promptfoo-usage.md` | Adversarial configs, red-team suites, regression baselines, YAML configuration |
| `nemo-guardrails-setup.md` | Colang dialog definitions, rail configs, topic boundaries |
| `guardrails-ai-setup.md` | Guard definitions, validator config, structured output schemas |
| `ragas-evaluation.md` | RAG metrics (context recall, faithfulness, answer relevancy), dataset prep |

---

## Increment 3: Governance Schemas --- COMPLETED

**Dependencies:** Increment 1 (contracts define what schemas enforce)

### Modified files

| File | Changes |
|------|---------|
| `governance/backend/schemas/eval_criteria.schema.json` | Add new `eval_class` enum values: `deepeval_faithfulness`, `deepeval_answer_relevancy`, `deepeval_hallucination`, `deepeval_contextual_relevancy`, `deepeval_geval`, `promptfoo_adversarial`, `promptfoo_regression`, `ragas_context_recall`, `ragas_faithfulness`, `ragas_answer_relevancy`, `ragas_context_precision`. Add optional `tool` field to criterion: `{"type": "string", "enum": ["deepeval", "promptfoo", "ragas", "custom"]}`. All additive — existing values preserved. |
| `governance/schemas/evaluation_prediction.schema.json` | Add optional `llm_evaluation` object inside `evaluation_prediction`: `deepeval_metrics` (array of {metric, predicted_score, threshold}), `promptfoo_required` (boolean), `guardrail_mode` (enum: nemo/guardrails-ai/both/none), `ragas_required` (boolean). Optional — L4 features unaffected. |

### New files

| File | Purpose |
|------|---------|
| `governance/backend/schemas/guardrails_config.schema.json` | Validates guardrails configuration: `mode` (enum), `nemo_config_path` (string), `guardrails_ai_validators` (array of strings), `bypass_allowed` (boolean). Used by L5 preflight validation. |

---

## Increment 4: Feature Starters & Templates --- COMPLETED

**Dependencies:** Increments 1, 3

### New files

**`features/starter_backend_l5/`** (5 files):

| File | Based On | L5 Additions |
|------|----------|-------------|
| `acceptance.feature` | `starter_backend/` | Add `@llm-eval`, `@guardrails`, `@adversarial` tag examples |
| `nfrs.md` | `starter_backend/` | Add sections: LLM Latency, LLM Cost, LLM Fallback, LLM Safety |
| `eval_criteria.yaml` | `starter_backend/` | Add `llm_evaluation.criteria` with DeepEval/Promptfoo examples using new eval_class values |
| `architecture_preflight.md` | `starter_backend/` | Add sections 10-14: LLM Gateway Config, Observability Config, Guardrails Config, Evaluation Strategy, LLM NFR Validation |
| `plan.md` | `starter_backend/` | Add LLM Gateway Configuration section, Guardrails Configuration section, extended `evaluation_prediction` with `llm_evaluation` sub-object |

**`features/starter_cli_l5/`** (5 files) — same pattern, CLI-adapted.

**Templates:**

| File | Purpose |
|------|---------|
| `governance/backend/templates/l5-architecture-preflight.md` | Canonical L5 preflight template (sections 1-9 from L4 + sections 10-14 for L5) |
| `governance/backend/templates/l5-plan.md` | Canonical L5 plan template (L4 plan + LLM gateway, guardrails, extended evaluation_prediction) |

---

## Increment 5: Agent Rules (Claude Code + Copilot) --- COMPLETED

**Dependencies:** Increment 1 (rules reference contracts)

### New Claude Code rules — `agents/claude-code/rules/backend/`

| File | Path Scope | Purpose |
|------|-----------|---------|
| `llm-gateway.md` | `**/adapters/llm/**` | All LLM calls through LiteLLM, no direct SDK imports in domain/service. Refs LLM_GATEWAY_CONTRACT. |
| `guardrails.md` | `**/adapters/guardrails/**`, `**/rails/**` | NeMo for conversation flow, Guardrails AI for output validation. Mode must match preflight. Refs GUARDRAILS_CONTRACT. |
| `llm-evaluation.md` | `**/tests/eval/**`, `**/eval_sets/**` | DeepEval for feature metrics, Promptfoo for adversarial, RAGAS for retrieval. No tool overlap. Refs EVALUATION_LLM_CONTRACT. |
| `llm-observability.md` | `**/adapters/observability/**` | OpenLLMetry for emission, Langfuse for storage. Instrument via ObservabilityPort. Refs OBSERVABILITY_LLM_CONTRACT. |

### New Copilot instructions — `agents/copilot/instructions/backend/`

| File | Equivalent To |
|------|-------------|
| `llm-gateway.instructions.md` | `llm-gateway.md` rule |
| `guardrails.instructions.md` | `guardrails.md` rule |
| `llm-evaluation.instructions.md` | `llm-evaluation.md` rule |
| `llm-observability.instructions.md` | `llm-observability.md` rule |

---

## Increment 6: Agent Skills & Copilot Prompts --- COMPLETED

**Dependencies:** Increments 1, 4 (skills reference contracts and starter templates)

### New Claude Code skills

| File | Skill | Purpose |
|------|-------|---------|
| `agents/claude-code/skills/backend/genai-preflight/SKILL.md` | `/genai-preflight <feature>` | Validates L5-specific decisions: LiteLLM is gateway, tracing defined, eval thresholds set, Promptfoo stated, guardrail mode defined, RAGAS if retrieval, LLM NFRs present. Writes sections 10-14 of architecture_preflight.md. |
| `agents/claude-code/skills/backend/eval-suite-planning/SKILL.md` | `/eval-suite-planning <feature>` | Plans DeepEval metrics, Promptfoo adversarial scenarios, RAGAS metrics (if retrieval), dataset planning, threshold recommendations. Writes to eval_criteria.yaml llm_evaluation section. |

### New Copilot prompts

| File | Equivalent To |
|------|-------------|
| `agents/copilot/prompts/backend/genai-preflight.prompt.md` | `/genai-preflight` skill |
| `agents/copilot/prompts/backend/eval-suite-planning.prompt.md` | `/eval-suite-planning` skill |

---

## Increment 7: CI Templates --- COMPLETED

**Dependencies:** Increment 3 (schemas for validation)

### New files — GitHub Actions (`ci/github/`)

| File | Purpose |
|------|---------|
| `deepeval-gate.yml` | Detects features with `deepeval_*` eval_class, installs deepeval, runs test suite against eval_sets, checks regression. Secrets: LLM provider key. |
| `promptfoo-gate.yml` | Detects features with `promptfoo_*` eval_class, installs promptfoo, runs adversarial suite, checks regression. Secrets: LLM provider key. |
| `guardrails-check.yml` | Validates guardrails config files exist and parse correctly (NeMo Colang, Guardrails AI guards). Structural only — no secrets needed. |

### New files — Azure DevOps (`ci/azure/`)

| File | Equivalent To |
|------|-------------|
| `deepeval-gate.yml` | GitHub `deepeval-gate.yml` |
| `promptfoo-gate.yml` | GitHub `promptfoo-gate.yml` |
| `guardrails-check.yml` | GitHub `guardrails-check.yml` |

---

## Increment 8: CLAUDE.md / Copilot Instruction Variants --- COMPLETED

**Dependencies:** Increments 1, 5, 6

### New files

| File | Based On | L5 Additions |
|------|----------|-------------|
| `agents/claude-code/claude-md/l5-backend-api.md` | `backend-api.md` (L4) | Add: read L5 contracts before planning, `/genai-preflight` in lifecycle after `/architecture-preflight`, `/eval-suite-planning` skill, L5 rules listed, L5 NFR requirements, DeepEval/Promptfoo/RAGAS in evaluation discipline |
| `agents/claude-code/claude-md/l5-backend-cli.md` | `backend-cli.md` (L4) | Same pattern |
| `agents/copilot/copilot-instructions/l5-backend-api.md` | `backend-api.md` (L4) | Copilot equivalent |
| `agents/copilot/copilot-instructions/l5-backend-cli.md` | `backend-cli.md` (L4) | Copilot equivalent |

---

## Increment 9: Manifest Updates --- COMPLETED

**Dependencies:** Increments 4-8 (all referenced files must exist)

### Approach

Add `"5"` to level choices. Add `level_5` sub-key to each variant — **full replacement** (includes all L4 files plus L5 additions), consistent with how `level_3` works. The existing `resolve_variant_files()` already handles this via `level_key = f"level_{level}"`.

### Modified files

| File | Changes |
|------|---------|
| `agents/claude-code/manifest.json` | Add `"5"` to `options.level.choices`. Add `level_5` to `type.api` (all L4 files + L5 rules + L5 skills), `type.cli` (same pattern), `ui.react`, `ui.angular` (L4 UI files — L5 doesn't add UI-specific content yet), `ci.github` (L4 CI + 3 L5 gates), `ci.azure` (same). |
| `agents/copilot/manifest.json` | Same pattern — add `"5"` to choices, `level_5` sub-keys with Copilot-specific L5 files. |
| `governance/schemas/agent-manifest.schema.json` | Add `level_5` to `variant_config` properties (same `$ref: #/$defs/level_override` as `level_3`). |

---

## Increment 10: CLI Updates --- COMPLETED

**Dependencies:** Increment 9 (manifests)

### Modified files

**`cli/govkit.py`:**
- Update `--level` choices from `["3", "4"]` to `["3", "4", "5"]` in all 3 subparsers (apply, init, validate)
- Update `cmd_init()`: add L5 starter selection (`starter_backend_l5`, `starter_cli_l5`), update next-steps to suggest `/genai-preflight` after `/architecture-preflight`
- Update `write_govkit_marker()` version to `"0.4.0"`

**`cli/validate.py`:**
- Add L5 starters to `STARTERS` set: `"starter_backend_l5"`, `"starter_cli_l5"`
- Add 3 new check functions:
  - `check_llm_nfrs(feature_dir)` — verifies nfrs.md has populated LLM-specific categories (latency, cost, fallback, safety) when eval_criteria mode is `llm`
  - `check_l5_eval_criteria(feature_dir)` — verifies eval_criteria.yaml has at least one `deepeval_*` or `promptfoo_*` eval_class when mode is `llm`
  - `check_l5_preflight_sections(feature_dir)` — verifies architecture_preflight.md has L5 sections (10-14)
- Add L5 branch in `run_validation()`: all L4 checks (6) + 3 new L5 checks = 9 checks
- Add level label: `"L5 GenAI Operations"`

---

## Increment 11: Tests --- COMPLETED

**Dependencies:** All previous increments

### Modified files

**`tests/test_govkit.py`:**
- `test_level_5_override` — verifies `level_5` sub-key files used when level="5"
- `test_level_5_includes_l5_additions` — verifies L5 files include L4 content plus L5 rules/skills
- `test_level_5_multiple_dimensions` — L5 across type+ci dimensions
- `test_write_level_5_marker` — .govkit with level "5"
- `test_init_l5_starter` — correct L5 starter selected

**`tests/test_validate.py`:**
- `make_l5_feature()` helper — creates valid L5 feature with LLM NFRs, deepeval criteria, L5 preflight sections
- `test_l5_passes_with_all_checks` — full valid L5 feature passes
- `test_l5_missing_llm_nfrs_fails` — nfrs.md without LLM categories when mode=llm
- `test_l5_missing_deepeval_criteria_fails` — eval_criteria.yaml without deepeval/promptfoo eval_class
- `test_l5_missing_preflight_sections_fails` — architecture_preflight.md without sections 10-14
- `test_l5_backward_compatible_with_l4` — L4 features still validate at L4
- `test_level_5_from_govkit_marker` — auto-detection

---

## Increment 12: Documentation --- COMPLETED

**Dependencies:** All previous increments

### Modified files

| File | Changes |
|------|---------|
| `README.md` | Add L5 to maturity model table, describe 8 tools, update usage examples with `--level 5` |
| `CHANGELOG.md` | Add 0.4.0 entry |
| `IMPROVEMENT_PLAN.md` | Update section 5.2 from TBD to completed checklist |
| `ci/README.md` | Add L5 CI gates (deepeval-gate, promptfoo-gate, guardrails-check) |

---

## File Count Summary

| Category | New | Modified |
|----------|-----|----------|
| Architecture contracts | 4 | 3 |
| Guides | 8 | 0 |
| Governance schemas | 1 | 2 |
| Feature starters (2 dirs x 5 + 2 templates) | 12 | 0 |
| Agent rules (Claude + Copilot) | 8 | 0 |
| Agent skills + prompts | 4 | 0 |
| CI templates (GitHub + Azure) | 6 | 0 |
| CLAUDE.md / instruction variants | 4 | 0 |
| Manifests + schema | 0 | 3 |
| CLI | 0 | 2 |
| Tests | 0 | 2 |
| Documentation | 0 | 4 |
| **Total** | **~47** | **~16** |

---

## Verification

1. **Unit tests:** `python -m pytest tests/ -v` — all existing + new tests pass
2. **L5 smoke test:**
   ```
   mkdir /tmp/test-l5
   python -m cli.govkit apply --agent claude-code --level 5 --type api --ui none --ci github --target /tmp/test-l5
   # Verify: L5 CLAUDE.md, L4+L5 rules, L5 skills, L5 starters, L5 CI gates, all 4 contracts, guides
   python -m cli.govkit init my-feature --target /tmp/test-l5
   # Verify: 5 artifacts with L5 sections (LLM NFRs, deepeval criteria, L5 preflight sections)
   python -m cli.govkit validate --target /tmp/test-l5
   # Verify: 9 checks run (L4 checks + 3 L5 checks)
   ```
3. **L4 regression:**
   ```
   python -m cli.govkit apply --agent claude-code --level 4 --type api --ui react --ci github --target /tmp/test-l4
   # Verify: identical to pre-L5 behavior
   ```
4. **L3 regression:**
   ```
   python -m cli.govkit apply --agent claude-code --level 3 --type api --ui none --ci github --target /tmp/test-l3
   # Verify: unaffected by L5 changes
   ```

---

## Risk Notes

- **Manifest size** — L5 `level_5` blocks enumerate all L4 files plus additions. Verbose but explicit and auditable.
- **Backward compatibility** — L3/L4 completely unaffected. `resolve_variant_files()` only activates level overrides for non-"4" levels.
- **Schema evolution** — New `eval_class` values are additive to enum. Existing eval_criteria.yaml files remain valid.
- **L5 validation is opt-in** — L5 checks only run when level="5". L4 features validated at L4 are never affected.
- **Guide maintenance** — The 8 guide files are practical reference subject to tool version changes. They reference contracts (not the other way around), so they can evolve independently.
