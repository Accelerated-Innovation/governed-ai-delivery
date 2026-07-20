# Skill-Oriented Agent Architecture

## Contract status

| Field | Value |
|---|---|
| Profile | GovKit SOAA implementation guidance |
| Source architecture | Skill-Oriented Agent Architecture v0.2 |
| Source status | Approved 2026-07-18 |
| Decision scope | SOAA-001 through SOAA-020 |
| Invariant scope | SOAA-INV-001 through SOAA-INV-206 |
| Conformance claim | None |

## Purpose

This contract defines the architecture boundary for applications in which an agent run selects and applies governed procedural skills.

It replaces framework-specific agent guidance with a provider-neutral model. Language, model provider, orchestration library, database, transport, and deployment topology remain implementation choices.

## Architecture rule

A governed skill-oriented agent system uses an accountable agent run to interpret an accepted task, select eligible procedural skills, activate exact skill releases, invoke bounded tools, incorporate authorized resources, adapt from observations, evaluate outcomes, and preserve evidence.

Trusted deterministic components retain control over:

- Task identity and ownership
- Policy and effective authority
- Skill admission and activation
- Authoritative state
- External side effects
- Execution budgets
- Evaluation and completion
- Evidence and lifecycle state

Model output is a proposal. A trusted controller validates and commits each consequential transition.

## Defining properties

Every design in scope must preserve:

1. A human or organization accountable for each consequential task.
2. Exactly one runtime owner for each active task.
3. Adaptive choice inside deterministic control boundaries.
4. Passive skills without task ownership or authority.
5. Progressive context disclosure.
6. Fresh authorization before each external operation.
7. Evaluation before consequential completion.
8. Durable evidence for state, action, outcome, and learning.

## Responsibility classification

Classify components by runtime responsibility, not file type, prompt shape, protocol, or deployment unit.

| Primitive | Owns | Must not own |
|---|---|---|
| Principal | Accountability for intent and consequences | Runtime execution state |
| Agent run | One bounded adaptive observation-action loop | Policy, authority, or authoritative business state |
| Skill | Reusable procedure and contract metadata | Task, grant, persistent adaptive loop, or completion |
| Tool | One typed bounded operation | Task or adaptive loop |
| Resource | Contextual data | Instruction precedence, authority, or truth by declaration |
| Workflow | Predetermined transitions and gates | Undeclared adaptive choice |
| Policy | Permissions, denials, limits, and transition rules | Model-discretionary enforcement |
| Evaluator | Measurement against explicit criteria | Authoritative gate decision |
| Memory | Governed retained information | Task state, policy, skill release, authority, or evidence |

## Skill versus application code

| Belongs in a skill | Belongs in trusted application code |
|---|---|
| Applicability and exclusions | Task acceptance and ownership |
| Procedure and heuristics | Permission and policy enforcement |
| References and examples | Authoritative state transitions |
| Input and output contracts | Transactions and concurrency control |
| Declared dependencies | Input and output validation |
| Required authority and approval points | Effective-authority calculation |
| Success, failure, stop, and escalation conditions | Tool authorization and side-effect execution |
| Evaluation and evidence obligations | Operation identity and idempotency |
| Release identity and provenance references | Budgets, revocation, reconciliation, and recovery |
| Progressive instruction content | Evaluation commits and completion gates |

A prompt, model response, `SKILL.md`, tool annotation, Agent Card, or MCP descriptor never replaces application enforcement.

## Required logical roles

The implementation must assign all eighteen SOAA logical roles. Several roles may share one process or class. Shared deployment never removes distinct responsibilities, ports, state ownership, or trust boundaries.

| Plane | Logical roles |
|---|---|
| Interaction and task | Interaction Adapter, Task Controller |
| Adaptive decision | Agent Decision Runtime, Model Gateway |
| Capability and context | Capability Controller, Context Controller, Skill Registry, Resource Gateway, Memory Gateway |
| Control and action | Policy and Authority Controller, Workflow and Composition Controller, Tool Gateway, Skill Asset Runner, Delegation and Handoff Controller, Evaluation Controller |
| Records and discovery | State Repository, Evidence Recorder, Agent Directory |

Architecture preflight must map each role to:

- Implementation owner
- Inbound and outbound ports
- Authoritative state
- Trust boundary
- Deployment location
- Required verification

## Proposal and commit boundary

| Adaptive proposal | Trusted commit owner |
|---|---|
| Task interpretation or plan | Task Controller or Workflow and Composition Controller |
| Skill ranking | Capability Controller |
| Tool request | Policy and Authority Controller plus Tool Gateway |
| Resource or memory request | Context Controller plus the relevant gateway |
| Delegation or handoff | Delegation and Handoff Controller |
| Completion claim | Evaluation Controller plus Task Controller |
| Recovery choice | Owning controller under policy |

Models must not write task, ownership, authority, activation, operation, evaluation, evidence, memory, release, or lifecycle records directly.

## Ports and adapters

Technology-neutral ports must cover:

- Task offer, acceptance, transition, ownership, and completion
- Candidate retrieval, deterministic admission, ranking, and activation
- Authority calculation, approval, denial, and revocation
- Context assembly, resource access, and memory access
- Model invocation
- Tool and skill-asset execution
- Composition, amendment, and joins
- Delegation, handoff, cancellation, and reconciliation
- Evaluation execution and gate decisions
- Evidence append and query
- Skill release, compatibility, lifecycle, and dependency resolution
- Agent discovery and protocol mapping

Provider SDKs, model APIs, MCP clients, A2A clients, databases, message brokers, and external integrations remain adapters.

## Required preflight decisions

For every feature in scope, `architecture_preflight.md` must identify:

- Accountable principal
- Task offer and acceptance boundary
- Task owner type and owner-epoch handling
- Applicable primitives and logical roles
- Adaptive proposals and trusted commit points
- Authoritative aggregates and writers
- Skill binding mode
- External side effects and authority route
- Context, memory, and resource trust needs
- Failure, budget, and recovery policy
- Evaluation and completion evidence
- Applicable SOAA contract set

## Prohibited patterns

- A model or skill owning a task
- Prompt text enforcing a permission or state transition
- A skill declaration granting authority
- External mutation without a trusted gateway
- Durable state existing only in model context
- Resource content promoting itself to instruction
- Skill success or model confidence completing a task
- Framework-specific types crossing domain ports
- Hidden recursion, hidden dependencies, or unbounded loops
- A conformance claim without the named profile, suite, target, environment, and evidence package

## Minimum verification

Verification must include:

- Schema and port contract tests
- State-transition and concurrency property tests
- Authority, denial, and revocation tests
- Selection and activation evaluation
- Injection and untrusted-content tests
- Side-effect, idempotency, and reconciliation tests
- Failure, retry, cancellation, checkpoint, and recovery tests
- Context, memory, and compaction tests
- Delegation and handoff fault tests
- Completion and evidence gates
- Lifecycle and supply-chain tests

The feature plan must link each affected control boundary to at least one verification family.
