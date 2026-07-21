# Agent Topology: <feature_name>

> Required when `multi_agent: true` is declared in `eval_criteria.yaml`.
> Run `/govkit-multi-agent-design <feature_name>` and apply the contract sets in
> `extensions/skill-oriented-agent-architecture/manifest.yaml`.

---

## Task Control

- **Accountable Principal:** TBD
- **Accepted Task Boundary:** TBD
- **Trusted Runtime Owner:** TBD — exactly one component
- **Task Controller:** TBD — owns authoritative lifecycle transitions
- **Authoritative State Writers:** TBD
- **Completion Authority:** TBD
- **Independent Verification Gate:** TBD
- **Budgets:** time, tokens, cost, tools, retries, loops, delegation depth

---

## Orchestrator

- **Classification:** agent run | workflow | trusted controller
- **Bounded Responsibility:** TBD
- **Accepted Inputs:** TBD — typed fields and provenance
- **Proposed Outputs:** TBD — never direct authoritative writes
- **Instruction/Prompt Reference:** TBD — immutable path, version, or digest
- **Logical Model Capability:** TBD or not applicable
- **Authority Ceiling:** TBD
- **Ports Invoked:** TBD
- **Routing Proposal:** TBD — identify the trusted component that validates and commits it

---

## Specialist Agents

### <specialist-1-name>

- **Classification:** agent run
- **Bounded Responsibility:** TBD — non-overlapping with every other agent run
- **Accepted Inputs:** TBD — typed fields and context provenance
- **Proposed Outputs:** TBD — typed proposal and evidence
- **Instruction/Prompt Reference:** TBD
- **Logical Model Capability:** TBD or not applicable
- **Authority Ceiling:** TBD
- **Ports Invoked:** TBD
- **Completion Evidence Produced:** TBD

### <specialist-2-name>

- **Classification:** agent run
- **Bounded Responsibility:** TBD
- **Accepted Inputs:** TBD
- **Proposed Outputs:** TBD
- **Instruction/Prompt Reference:** TBD
- **Logical Model Capability:** TBD or not applicable
- **Authority Ceiling:** TBD
- **Ports Invoked:** TBD
- **Completion Evidence Produced:** TBD

---

## Routing Logic

Declare every legal transition, its deterministic admission or validation rule,
authoritative writer, and terminal route. Framework-specific edges or message
types belong in the implementation plan, not this contract.

| From state | Proposal source | Validation/guard | Trusted writer | To state |
|---|---|---|---|---|
| accepted | orchestrator | TBD | task controller | TBD |
| TBD | specialist | TBD | task controller | verifying |
| verifying | evaluator | completion gate | task controller | completed or blocked |

No implicit recursion, unconditional loop, or unbounded delegation is permitted.

---

## Runtime State and Handoffs

- **State Schema Path and Version:** TBD
- **Checkpoint/Persistence Boundary:** TBD
- **Legal State Transitions:** TBD
- **Handoff Envelope:** task identity, authority, context snapshot, budgets, evidence
- **Context and Resource Trust:** TBD
- **Concurrency and Single-Writer Rules:** TBD

---

## Authority and External Operations

For each external operation, record:

- typed port and operation identity
- argument schema and semantic validation
- fresh authorization and approval requirements
- idempotency key and duplicate behavior
- timeout, retry, rate, and destination limits
- reconciliation or compensation route
- evidence record and authoritative writer

---

## Failure Modes

- **Per-operation and End-to-End Deadlines:** TBD
- **Retry Budgets and Retryable Categories:** TBD
- **Cancellation Behavior:** TBD
- **Checkpoint/Replay Rules:** TBD
- **Reconciliation and Compensation:** TBD
- **Degraded or Read-Only Behavior:** TBD
- **Escalation and Terminal Failure States:** TBD

---

## Completion

- **Evidence Required to Enter Verification:** TBD
- **Independent Oracle/Evaluator:** TBD
- **Blocked or Inconclusive Behavior:** TBD
- **Trusted Completion Transition:** TBD
- **Conformance Claim Boundary:** TBD
