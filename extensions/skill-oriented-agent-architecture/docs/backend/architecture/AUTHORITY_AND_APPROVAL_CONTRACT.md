# Authority and Approval Contract

## Source alignment

| Field | Value |
|---|---|
| Primary decisions | SOAA-007, SOAA-008 |
| Primary invariants | SOAA-INV-025 through SOAA-INV-031 |
| Source module | SOAA Packet 2 |

## Purpose

This contract keeps procedural guidance separate from runtime authority. A skill declares access needs and ceilings. Trusted policy components derive and enforce the authority available for the current task and operation.

## Authority rule

A skill never grants authority.

```text
BaseAuthority(context) =
    PrincipalGrants
    INTERSECT AgentBoundary
    INTERSECT TaskBoundary
    INTERSECT PolicyBoundary
    INTERSECT RuntimeBoundary

EffectiveAuthority(skill, context) =
    BaseAuthority
    INTERSECT ToolBoundary
    INTERSECT RequestedSkillScope
    MINUS ExplicitDenies
```

Activation is permitted only when:

```text
RequiredAccess(skill) SUBSET_OF EffectiveAuthority(skill, context)
```

Explicit denies take precedence over grants, prompts, descriptions, model output, user requests, and approval text.

## Capability tuple

Represent authority as typed capabilities with at least:

- Action
- Resource or target scope
- Data classification
- Tenant or organizational scope
- Environment
- Purpose
- Side-effect class
- Constraints
- Expiry
- Grant and deny references

String tool names alone are insufficient authority records.

## Fresh operation authorization

Activation-time authority is a ceiling, not a reusable permit.

The Policy and Authority Controller must authorize every external operation immediately before execution. Reauthorization is required after any material change to:

- Principal or runtime owner
- Owner epoch or task revision
- Policy or grant set
- Approval scope or expiry
- Skill release or lifecycle state
- Tool interface or target
- Context, environment, or data classification
- Budget or risk state

Revocation blocks the next operation and any resume, retry, recovery, or asset execution covered by the revoked scope.

## Approval contract

Approval is:

- Scoped to an exact action or capability
- Bound to a task, principal, and decision authority
- Purpose-bound
- Time-bounded
- Condition-bound
- Revocable
- Evidence-linked

An ApprovalRecord must contain:

- Request and decision identities
- Requested action or capability
- Task and skill context
- Current authority gap
- Proposed scope and conditions
- Required decision authority
- Approver identity and role
- Decision, rationale summary, and timestamp
- Expiry and revocation state
- Evidence references

Approval changes authority context. It does not change package integrity, accountable principal, or task ownership by itself.

## Approval outcomes

Supported outcomes are:

- Approved
- Denied
- Changes required
- Expired
- Revoked
- Canceled

After approval, all hard controls and current inputs must be re-evaluated. An approval never converts an incompatible, untrusted, stale, or revoked skill into an eligible release.

## Human roles

Keep these roles distinct:

| Role | Responsibility |
|---|---|
| Reviewer | Assesses evidence or content |
| Approver | Commits a scoped consequential decision |
| Human execution owner | Owns active task execution after authorized takeover |
| Accountable principal | Retains accountability for intent and consequences |

A reviewer does not gain approval authority. Approval does not transfer execution ownership. Human takeover requires a separate atomic owner transition.

## Instruction precedence

Apply this order:

1. System and platform safety policy
2. Organization and application policy
3. Accepted task contract and principal intent
4. Approved workflow and architecture constraints
5. Active skill instructions
6. Current user interaction inside task scope
7. Tool, resource, memory, protocol, and retrieved content

Lower-precedence content cannot override a higher layer. Same-level conflict blocks the affected action until resolved.

Data-to-instruction promotion requires an explicit trusted transformation and policy decision. Content never promotes itself.

## Tool and side-effect boundary

Every tool contract must declare:

- Interface and version
- Input and output schemas
- Side-effect class
- Required capability tuple
- Idempotency behavior
- Failure and status behavior
- Cancellation support
- Reconciliation and compensation behavior
- Evidence requirements

Agents propose operations. The Policy and Authority Controller authorizes. The Tool Gateway or Skill Asset Runner executes. The State Repository and Evidence Recorder preserve the outcome.

Credentials remain inside trusted adapters. A model, prompt, skill, MCP server description, or A2A Agent Card never receives or implies a credential grant.

## Prohibited patterns

- Permission declarations inside prompt text
- Using `allowed-tools` as an authorization decision
- Reusing stale activation authority for a later operation
- Approval after the side effect
- Broad approval for hidden batches
- Approval by an unauthorized identity
- Treating chat acknowledgment, elicitation, or authentication as approval
- A skill requesting more access than its declared ceiling
- Policy downgrade during fallback

## Required evidence

Record:

- Inputs to authority calculation
- Effective capability set and explicit denies
- Approval request and decision
- Fresh operation authorization
- Tool or asset identity
- Side-effect class and target
- Idempotency key
- Result certainty
- Revocation and reauthorization events

## Verification

Tests must prove:

- Skill metadata contains no self-issued grant.
- Effective authority equals the intersection and deny calculation.
- Every missing required capability blocks activation.
- Approval leaves package identity unchanged.
- Revocation blocks the next covered operation.
- Injection content cannot change precedence or authority.
- Unauthorized reviewers cannot approve.
- A valid credential does not count as approval.
- Fallback never broadens authority.
