# Human Approval Matrix

## Purpose

Define which actions require human approval, who can approve them, and what evidence is required.

## Risk Levels

| Risk Level | Description | Default Approval Requirement |
|---|---|---|
| Low | Reversible or internal-only change | Optional or policy-based |
| Medium | Client-visible or externally synced change | Authorized client or engagement role |
| High | Official artifact, methodology, security, integration, or broad client impact | Explicit qualified approval |

## Approval Matrix

| Action Type | Risk Level | Required Approver Roles | Optional Reviewers | Evidence Required |
|---|---|---|---|---|
| | | | | |

## Approval Statuses

Use these statuses unless the feature preflight documents an approved exception:

```text
draft
pending_review
approved
rejected
changes_requested
expired
published
cancelled
```

## Audit Requirements

Every approval decision must capture:

- Subject ID
- Subject type
- Approver user ID
- Role or group used for approval
- Decision
- Timestamp
- Prior state
- Approved state
- Comment or rationale when provided

## Exceptions

Document any feature-specific exceptions and link to the approving ADR.

