# SOAA Applicability

Advisory GovKit guidance. It does not change any contract in this extension.
The contracts remain authoritative.

## Purpose

Select SOAA controls by what a feature actually does and what its actions can
cause. Agent count, binding mode, memory, data sensitivity and external effects
are independent dimensions. One fixed skill can carry more consequence than a
large read-only catalog. No single level or score decides which controls apply.

Record the decision in `architecture_preflight.md` Section 15a with the
`templates/preflight-soaa.md` block.

## Three layers

| Layer | Applies when the feature… | Guidance |
|---|---|---|
| LLM application | calls language models (`mode: llm`) | `llm-application` contracts |
| SOAA | uses governed runtime skills, an adaptive agent loop or their control boundaries, including one agent with fixed skills | This extension |
| Multi-agent topology | coordinates multiple agents through delegation, handoff or adaptive parallel work | `agent_topology.md`, only when `eval_criteria.yaml` declares `multi_agent: true` |

A feature may need any combination. A fixed sequence of model calls is a
workflow, not automatically an adaptive agent.

## Applicability matrix

Each row is a condition ID used by the preflight block and by
`catalog/gk-soaa-cases.yaml`.

| Condition | Behavior or boundary | Required control focus | Safe omission condition |
|---|---|---|---|
| `adaptive-run` | Every adaptive agent run | Accepted task and principal, one current owner, trusted writers, bounds and a completion gate | No adaptive loop: describe a workflow instead |
| `skill-activation` | Every activation, including fixed binding | Exact release, admission, compatibility, atomic activation, current authority, context and revocation behavior | No skill activation |
| `untrusted-input` | Any untrusted input or model context | Source labels, controlled assembly, authorization and data/instruction separation | Not omittable merely because there is no retrieval or persistent memory |
| `external-read` | External reads | Scope and data controls, deadlines, current authorization and evidence | No external access |
| `external-mutation` | External mutation | Durable operation identity, idempotency or reconciliation, bounded retries, cancellation and unknown-effect handling | Interface and credentials make mutation unavailable |
| `multi-tenant-data` | Multiple tenants or classified data | Isolation, purpose and classification checks, credential and evidence separation | Single declared trust domain that rejects other domains |
| `model-selection` | Model choice among skills | Admission before ranking, null selection, confusability tests and catalog bounds | Trusted code selects one exact release without model ranking |
| `workflow-switching` | Workflow or sequential skill switching | Versioned transitions, binding and context replacement, stale-call fencing and restart | Only one activation; no workflow transitions |
| `persistent-memory` | Persistent memory or retrieval | Authorized access, provenance, freshness, poisoning tests and retention | Interfaces absent; ordinary context controls still apply |
| `human-takeover` | Human takeover and handback | Quiescence, atomic transfer, owner epoch and stale-owner rejection | No transfer interface; approval alone is not takeover |
| `delegation` | Delegation, adaptive parallelism or remote agents | Child acceptance, authority attenuation, joins, handoff and local verification | Interfaces absent; parallel bounded tools alone do not imply multiple agents |
| `executable-assets` | Executable package assets | Explicit invocation, constrained runner, declared dependencies and untrusted outputs | No assets; loading stays passive in either case |

## Omission rule

A condition is `applies`, `not-applicable` or `unknown`.

- `not-applicable` needs a reason, a verified absent or disabled interface
  (evidence, not intent), an owner and a change trigger that reopens the
  decision.
- Unknown applicability stays unresolved. It never becomes not applicable
  automatically, and it cannot satisfy a required control.
- An omitted condition whose interface is reachable is a failure
  (`GK-SOAA-16`), not a narrower scope.

## Single-agent path

One agent run that uses 2–3 fixed or model-selected skills typically applies
`adaptive-run`, `skill-activation` and `untrusted-input`. It applies
`model-selection` only when the model chooses among the skills; a person or
trusted workflow naming one exact release does not. Effects, memory, tenants,
takeover and delegation are decided on their own rows. Topology does not apply
unless several agents coordinate.

## System-level role and writer map

Map the eighteen logical roles once at system level. Logical roles need not be
separate services, classes or products; one process and one transactional store
may implement a first experiment.

Keep a system-level writer map with one row per authoritative aggregate:

| Aggregate | Trusted writer | Authorization rule | Version or fencing check | Durable commit | Evidence path |
|---|---|---|---|---|---|
| Task | Task Controller | Accepted offer within principal scope | Owner epoch | State and evidence in one transaction | Task transition record |

Each feature preflight reviews only the per-feature changed rows of the role
and writer maps, and states that the other rows are unchanged.
