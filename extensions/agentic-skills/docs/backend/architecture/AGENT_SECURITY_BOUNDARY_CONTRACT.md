# Agent Security Boundary Contract

## Purpose

This contract governs security, authorization, privacy, and tenant isolation for agentic systems.

## Architectural Rule

Agents operate inside the same security model as the application. They must never expand access, infer permissions, or expose data beyond the authorized user, trigger, client, tenant, or engagement scope.

## Authorization Context

Every agent run must receive an explicit authorization context.

Recommended fields:

- User ID or system trigger ID
- Tenant ID
- Client/workspace ID
- Engagement ID
- Roles
- Groups
- Object scopes
- Allowed actions
- Denied actions

## Tenant and Engagement Isolation

Agent context retrieval must be tenant and engagement scoped.

The system must prevent:

- Cross-client data leakage
- Cross-engagement data leakage
- Trace leakage
- Prompt/context leakage
- External task creation in the wrong workspace
- SharePoint publishing to the wrong site or folder

## Data Minimization

Agents should receive only the context needed for the task.

Context retrieval should prefer:

- Structured state over broad document dumps
- Relevant snippets over entire files
- Redacted metadata where possible
- Role-filtered recommendations and actions

## External System Authorization

External integrations must use service-controlled authorization.

Agents must not receive raw external credentials. They may request integration actions through application services that enforce policy.

## Prompt Injection and Tool Misuse

Systems must treat retrieved documents, external content, and user inputs as untrusted.

Agent instructions must not be overridden by:

- Document text
- Miro/SharePoint/ClickUp content
- User-entered free text
- External website content
- Prompt fragments inside uploaded files

## Secrets

Secrets must not be passed to models, stored in prompts, or written into traces.

Examples:

- API keys
- OAuth tokens
- Refresh tokens
- Client secrets
- Database credentials
- Signing keys

## Prohibited Patterns

The system must not:

- Use agent output as proof of authorization.
- Let agents choose their own data scope.
- Allow prompt text to grant tool permissions.
- Log sensitive client data without controls.
- Expose hidden reviewer notes to unauthorized users.

## Feature Preflight Requirements

Feature `architecture_preflight.md` must identify:

- Authorization context
- Data scopes
- External systems touched
- Sensitive data classes
- Prompt injection risks
- Audit requirements
- Security tests

