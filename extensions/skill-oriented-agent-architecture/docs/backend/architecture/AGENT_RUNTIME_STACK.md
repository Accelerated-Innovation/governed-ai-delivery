# Agent Runtime Stack

This document defines the **default product bindings** for the SOAA agent
runtime. It is an *implementation profile*: it maps the runtime responsibilities
that `RUNTIME_STATE_AND_EXECUTION_CONTRACT.md` defines to concrete products a
team can adopt as a starting point and then customize.

**Authority: advisory (`defaults`).** The neutral contracts in `soaa_core` —
above all `RUNTIME_STATE_AND_EXECUTION_CONTRACT.md` — remain authoritative. Where
this profile and a contract disagree on any specific point, the contract wins.
This profile never relaxes an invariant; it only names a default way to satisfy
one. Deviating from these defaults requires an **ADR** in the consuming project.

The contract defines the *what* (one runtime owner, durable operation records,
restart without a provider transcript, atomic state+evidence commit). This
document defines a default *how*.

> **No blocking CI gate ships with this profile.** SOAA runtime conformance
> (the invariant-to-assertion suite) is future work in the SOAA source set, so
> the products below are guidance, not an enforced gate. Treat the contract's
> verification list as the bar; wire your own tests to it.

---

## 1. The runtime is more than a graph library

The single most common mistake is "our runtime is LangGraph." A graph/orchestration
library supplies the adaptive decision loop and composition — roughly **two** of
the responsibilities the runtime contract enumerates. The trusted controllers,
durable operation records, evidence, and completion gate are things you build
*around* the library. Naming one product as "the runtime" implies a conformance
the library alone cannot deliver.

So the default set is a **responsibility → default implementation** table, not a
single product.

## 2. Responsibility → default binding

| SOAA responsibility (see contract) | Default binding | Notes |
|---|---|---|
| Agent Decision Runtime · adaptive loop · composition plan | **LangGraph** (`StateGraph`) | The part a graph library actually owns. Alternatives by ADR: Temporal, a homegrown state machine. |
| Durable task/activation state · restart reconstruction | **LangGraph checkpointer on PostgreSQL** | An in-memory checkpointer **fails** the restart rule — it cannot reconstruct active work without a provider transcript. Durable checkpointer is mandatory outside local dev. |
| Task Controller · one-owner rule · `owner_epoch` fencing | **Application-owned (build)** | Not a library feature. Enforces exactly one runtime owner and fences former-owner commands after transfer. |
| Policy & Authority Controller · approvals · revocation | **Application-owned (build)** + model guardrails from `llm-application` | Fresh authorization before each external operation; approvals are durable records, not prompt state. |
| Operation boundary · `OperationRecord` · Tool Gateway | **Application-owned adapter (build)** | Every mutating external operation gets a durable record with an idempotency key and side-effect class *before* invocation. Unknown effect is a distinct result. |
| Evidence Recorder | **Append-only store** (PostgreSQL or object storage) | Immutable; historical evidence is never overwritten on retry or recovery. |
| Evaluation Controller · completion gate | **`llm-application` evaluation** + the govkit evaluation gates | Only an Evaluation Controller pass permits `COMPLETED`; skill success never completes a task. |

LangGraph is the default for two rows. The controller, operation, and evidence
rows are "you build this, behind ports, regardless of graph library." Keep the
graph library and all vendor SDKs inside `adapters/`; domain and services depend
only on typed ports (per `ARCH_CONTRACT.md` / `BOUNDARIES.md`).

## 3. Durability by environment

The restart rule (contract §"Restart rule") is the load-bearing constraint. State
durability is therefore not uniform across environments:

| Environment | Checkpointer | Evidence store | Rationale |
|---|---|---|---|
| Local dev | in-memory acceptable | local file/db | fast iteration; restart not exercised |
| CI | in-memory or ephemeral pg | ephemeral | deterministic test runs |
| Staging | **durable (PostgreSQL)** | **append-only** | restart, fencing, and evidence paths must be real |
| Production | **durable (PostgreSQL)** | **append-only, retained** | full restart-without-transcript guarantee |

Shipping an in-memory checkpointer to staging or production is a profile
violation and, because it breaks a contract invariant, a contract violation —
not merely a default swap.

## 4. Relationship to model calls

This profile governs the **runtime**. When a decision-loop node calls a language
model, that call goes through the `llm-application` extension's `ModelGatewayPort`
and its `GATEWAY_STACK.md` profile — not through anything defined here. Install
`llm-application` alongside SOAA for model-backed agents. Model output entering
the loop is a **proposal**; a trusted controller decision, not the model, commits
any transition.

## 5. Customization for new projects

Review, in order:

- **Graph library** — LangGraph by default. Temporal or a homegrown state machine
  are legitimate; swapping requires an ADR because it is "altering agent
  orchestration strategy."
- **Durable state backend** — PostgreSQL checkpointer by default; confirm it is
  active in staging and production.
- **Evidence store** — append-only Postgres or object storage; confirm immutability.
- **Which controllers you build vs. adopt** — the Task, Authority, and Evaluation
  controllers are application-owned here; if you adopt a framework that provides
  any of them, record how it satisfies the contract's authoritative-writer table.

The controller/evidence rows are not optional defaults you can drop — they are the
contract's requirements with a default implementation strategy attached.

## 6. When an ADR is required

An ADR must be created when:

- Replacing LangGraph with a different orchestration runtime (Temporal, homegrown, …).
- Running any environment above local dev on a non-durable checkpointer.
- Delegating any authoritative-writer responsibility (Task, Authority, Operation,
  Evidence, Evaluation) to a third-party product instead of application-owned code.
- Introducing a runtime pattern the contract's "Prohibited patterns" list forbids.

Record the selected runtime and every deviation from this profile in an ADR
(`docs/backend/architecture/ADR/`), and reflect the standing choice wherever your
project records its approved stack (e.g. `TECH_STACK.md`).
