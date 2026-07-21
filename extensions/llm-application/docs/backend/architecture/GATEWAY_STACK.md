# Gateway Stack

This document defines the **default product bindings** for the LLM application
ports. It is an *implementation profile*: it maps the provider-neutral concerns
that this extension's contracts define — model access, guardrails, observability,
evaluation — to concrete products a team can adopt as a starting point and then
customize.

**Authority: advisory (`defaults`).** The contracts remain authoritative:
`LLM_GATEWAY_CONTRACT.md`, `MODEL_GUARDRAILS_CONTRACT.md`,
`LLM_OBSERVABILITY_CONTRACT.md`, and `LLM_EVALUATION_CONTRACT.md`. Where this
profile and a contract disagree, the contract wins. Selecting a product never
grants its SDK permission to cross an application boundary — every product below
sits inside an outbound adapter behind a typed application port. Deviating from a
default binding requires an **ADR** in the consuming project.

The contracts define the *what* (an application-owned `ModelGatewayPort`, logical
model routing, fail-closed guardrails, immutable provenance). This document
defines a default *how*.

> **No blocking CI conformance gate ships with this profile.** The products below
> are guidance. Bundled setup guides under `docs/backend/guides/` show concrete
> configuration; the evaluation row is governed by the core `EVAL_STACK.md`.

---

## 1. Concern → port → default binding

| Concern (contract) | Application port | Default binding | Setup guide |
|---|---|---|---|
| Model access · logical routing · resilience · budgets (`LLM_GATEWAY_CONTRACT`) | **`ModelGatewayPort`** | **LiteLLM** proxy (model aliases, fallback chains) | `docs/backend/guides/litellm-setup.md` |
| Providers behind the gateway | `ModelGatewayPort` adapters | **OpenAI · Anthropic · Azure OpenAI** (logical identities, not hard-coded model ids) | — |
| Model telemetry · trace correlation · provenance (`LLM_OBSERVABILITY_CONTRACT`) | **`ObservabilityPort`** | **OpenLLMetry** (instrumentation) → **Langfuse** (traces, prompt versions, dashboards) | `docs/backend/guides/openllmetry-setup.md`, `langfuse-integration.md` |
| Input · context · tool-call · output controls (`MODEL_GUARDRAILS_CONTRACT`) | guardrail adapter | **NeMo Guardrails** (dialog/behavioral) + **Guardrails AI** (structured-output validation) | `docs/backend/guides/nemo-guardrails-setup.md`, `guardrails-ai-setup.md` |
| Quality · adversarial · retrieval · regression evaluation (`LLM_EVALUATION_CONTRACT`) | evaluation port | **DeepEval** (quality) · **Promptfoo** (adversarial) · **RAGAS** (retrieval) | governed by core `EVAL_STACK.md` |

The evaluation row is **not duplicated here** — the core `docs/backend/evaluation/EVAL_STACK.md`
already owns the evaluator product mapping and its CI gates. This profile points
to it so the gateway and evaluation stories stay consistent.

Keep every vendor SDK inside `adapters/`; domain and application services depend
only on the typed ports (per `ARCH_CONTRACT.md` / `BOUNDARIES.md`). Model output is
a proposal — deterministic validation, authorization, and side-effect commit paths
stay separate from the model call.

## 2. Defaults by environment

| Environment | Gateway | Observability | Guardrails | Evaluation |
|---|---|---|---|---|
| Local dev | LiteLLM optional (direct provider ok) | optional | optional | per `EVAL_STACK.md` |
| CI | LiteLLM (recorded/replayed) | disabled | **enforced for untrusted-input features** | per `EVAL_STACK.md` |
| Staging | LiteLLM | Langfuse enabled | enforced | per `EVAL_STACK.md` |
| Production | **LiteLLM (required)** | **Langfuse (required)** | **enforced, fail-closed** | per `EVAL_STACK.md` |

## 3. Relationship to the agent runtime

This profile governs **model calls**. When those calls happen inside a
skill-oriented agent runtime, the runtime itself is governed by the
`skill-oriented-agent-architecture` extension and its `AGENT_RUNTIME_STACK.md`
profile. The two are complementary: the runtime profile owns the graph, task
ownership, and evidence; this profile owns the gateway, guardrails, telemetry, and
evaluation of the model calls the runtime makes.

## 4. Customization for new projects

Review, in order:

- **Gateway** — LiteLLM by default; a hosted gateway or direct provider adapters
  are legitimate, but the application-owned `ModelGatewayPort` boundary is not
  optional. Swapping the gateway product requires an ADR.
- **Providers** — declare logical model identities; never hard-code provider model
  ids in domain code.
- **Observability** — OpenLLMetry → Langfuse by default; confirm redaction of raw
  prompts/responses per the observability contract.
- **Guardrails** — enable the input/output controls the feature's trust boundary
  requires; guardrails are fail-closed.
- **Evaluation** — follow `EVAL_STACK.md`; do not re-specify evaluators here.

## 5. When an ADR is required

An ADR must be created when:

- Selecting or replacing the gateway product or a provider.
- Replacing the observability or guardrail products named above.
- Bypassing the `ModelGatewayPort` boundary for any model call.
- Any material change to routing, safety, evaluation, or telemetry policy.

Record the selected products and every deviation from this profile in an ADR
(`docs/backend/architecture/ADR/`), and reflect the standing choice wherever your
project records its approved stack (e.g. `TECH_STACK.md`).
