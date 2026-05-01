# Cross-Repository Features

This guide explains how to structure, plan, and implement features that span multiple repositories.

---

## When to Use Multi-Repo Features

Multi-repo features are needed when a single capability requires coordinated changes across several repositories:

**Examples:**

- **Authentication Enhancement:** Auth Service publishes JWKS endpoint → Client SDK validates tokens locally → API Gateway relays tokens
- **New API Contract:** Backend API adds new endpoint → Frontend UI calls the endpoint → Mobile SDK wraps it with offline caching
- **Database Migration:** Primary database schema changes → Read replica syncs schema → Microservices adapt queries
- **Message Protocol Upgrade:** Message producer changes schema version → Consumer library updates parsing → Subscriber system validates messages

**Not multi-repo if:**
- Work is entirely contained to one codebase (monorepo counts as one repository)
- External dependency is already released and stable (e.g., upgrading to a published library)
- Changes are purely internal refactors with no external interface changes

---

## The Three Stages of Multi-Repo Features

### 1. Planning Stage (Sequential)

**Shared Specification Phase:**
- All repo owners meet to define the feature and its contracts
- One "primary owner" repo is chosen (the orchestrator)
- Contracts are explicitly documented in the primary repo's `nfrs.md`
- No implementation begins until all owners approve the specification

**Output:**
- Single feature entry in primary repo: `features/<feature_name>/`
- `nfrs.md` includes "Repository Scope" table listing all repos and owners
- `acceptance.feature` describes end-to-end behavior (may reference external systems)
- Contracts (API schemas, message formats, protobuf, etc.) documented in the feature

**Why sequential:** Prevents repos from implementing incompatible versions of the same interface.

### 2. Implementation Stage (Parallel)

**Each Repository Works Independently:**
- Repo A implements its portion using its own `acceptance.feature` / `plan.md` / `architecture_preflight.md`
- Repo B implements its portion in parallel
- Repo C implements its portion in parallel
- Each repo creates its own feature branch, PR, tests, CI validation

**Each repo:
- Implements against the shared contract (not tight coupling)
- May mock external contracts for unit tests (using test doubles)
- Has its own `architecture_preflight.md` validating repo scope
- Runs its own CI gates (quality, evaluation, security)
- Creates its own PR with its own reviewers

**No repo:**
- Waits for another repo to finish (parallel development)
- Implements code for another repo (violates ownership)
- Assumes the contract will change (use the agreed-upon spec)

**Output:**
- Repo A merged PR + commit to main
- Repo B merged PR + commit to main
- Repo C merged PR + commit to main

### 3. Integration Stage (Sequential)

**Cross-Repo Testing:**
- After all repos are merged to main, integration tests verify contracts
- Contract tests (e.g., "Auth Service JWKS endpoint returns expected schema") run against real services
- End-to-end tests (e.g., "Client successfully validates a token from Auth Service") run across repos
- If contracts diverge, root cause is identified and fixed

**Deployment Coordination:**
- If repos have deployment dependencies (e.g., "Client can't deploy until Auth Service is live"), coordinate timing
- Or design contracts to be backward-compatible so deployment order is flexible

**Output:**
- Integration test suite passes
- Feature works end-to-end across all repos
- Contracts verified against real implementations

---

## Repository Ownership Table

Every multi-repo feature must document ownership clearly in its primary repo's `nfrs.md`. The `**Scope:**` declaration is required — the CI check (`repo-scope-check.yml`) reads this value to determine whether to validate cross-repo ownership.

```markdown
## Repository Scope

**Scope:** `multi-repo`

### Multi-Repository Details

*Complete only if scope is `multi-repo`.*

| Repository | Owner Team | Modules/Services | Contracts to Implement |
|---|---|---|---|
| auth-service | Identity Team | JWT generation, JWKS endpoint | JWKS HTTP endpoint at `/jwks` |
| client-sdk | SDK Team | Token validation, caching | Client-side validation of JWKS-issued tokens |
| api-gateway | Platform Team | Token relay middleware | Accept Bearer token, forward to downstream services |

**Primary Owner:** auth-service (orchestrates the feature)

**Key Cross-Repo Contracts:**
- Auth Service publishes JWKS endpoint at `GET /jwks` (JSON Web Key Set format)
- Client SDK loads JWKS on first use and caches for up to 24 hours
- API Gateway validates Bearer token against cached JWKS, or fetches fresh JWKS if validation fails
```

---

## Defining Contracts

Contracts are the interfaces between repositories. Be explicit:

### HTTP API Contract

```markdown
**Endpoint:** `GET /jwks`

**Response:**
- Status: 200 OK
- Content-Type: application/json
- Body: JSON Web Key Set (JWKS) format per RFC 7517
- Example:
  ```json
  {
    "keys": [
      {
        "kty": "RSA",
        "use": "sig",
        "kid": "key-2024-01",
        "n": "...",
        "e": "AQAB"
      }
    ]
  }
  ```

**Caching:** HTTP Cache-Control header: `public, max-age=86400`

**Rate Limiting:** None (public endpoint)
```

### Message Schema Contract (Async)

```markdown
**Topic:** `user.signup`

**Message Format:** CloudEvents v1.0 over Kafka

**Schema:**
```yaml
id: string (UUID)
source: "user-service"
type: "user.signup.v1"
time: RFC3339 timestamp
data:
  userId: string (UUID)
  email: string
  displayName: string
  plan: enum(free, pro, enterprise)
```

**Guarantees:**
- Exactly-once delivery (partition key = userId)
- Retention: 7 days
- Ordering: per partition
```

### Database Schema Contract (Shared DB)

```markdown
**Table:** `users`

**Required Columns:**
- `id` (UUID, primary key)
- `email` (string, unique)
- `created_at` (timestamp)

**Read-Only Columns (for other services):**
- `plan` (enum: free | pro | enterprise) — written by billing service only
- `last_login_at` (timestamp) — written by auth service only

**Never write to:**
- Columns marked "written by X service only"
- Use explicit owner for each column to prevent conflicts
```

---

## Gherkin: Single Feature, Multiple Repos

Write one `acceptance.feature` that describes the feature end-to-end:

```gherkin
Feature: Unified JWT authentication across services

  Background:
    Given Auth Service is running and healthy
    And Client SDK is integrated
    And API Gateway is running

  Scenario: Client obtains and validates JWT
    Given Client has not cached a JWKS
    When Client requests a new JWT from Auth Service
    Then Auth Service returns a signed JWT
    And Client fetches JWKS from `GET /jwks`
    And Client validates the JWT locally against the JWKS
    And validation succeeds

  Scenario: API Gateway relays JWT without re-validating
    Given Client has a valid JWT from Auth Service
    When Client calls API Gateway with Bearer token
    Then API Gateway validates the token against JWKS
    And API Gateway forwards the request to the downstream service
    And downstream service receives the JWT in the Authorization header

  Scenario: JWKS is cached and reused
    Given Client has cached JWKS from a previous request
    When Client obtains a new JWT from Auth Service
    Then Client does NOT fetch JWKS again (uses cached version)
    And Client validates the new JWT against cached JWKS
    And validation succeeds
```

**Mapping to repos:**

- `Given/When Auth Service returns a signed JWT` → auth-service implements
- `Given/When Client fetches JWKS and validates locally` → client-sdk implements
- `Given/When API Gateway validates and forwards` → api-gateway implements

Each repo implements the steps it owns and mocks external steps (e.g., client-sdk mocks Auth Service responses in unit tests).

---

## Testing Strategy

### Unit Tests (In Each Repo)

Each repo tests its portion in isolation:

```python
# client-sdk test
def test_client_validates_token_against_cached_jwks():
    # Arrange
    mock_jwks = { "keys": [...] }  # Mock from Auth Service
    client = TokenValidator(jwks_cache=mock_jwks)
    token = "eyJhbG..."
    
    # Act
    result = client.validate(token)
    
    # Assert
    assert result.is_valid == True
```

**No repo waits for another repo.** All external dependencies are mocked.

### Contract Tests (Per Repo)

Each repo verifies the contract it implements:

```python
# auth-service contract test
def test_jwks_endpoint_returns_valid_jwks():
    response = client.get("/jwks")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    
    jwks = response.json()
    assert "keys" in jwks
    assert all("kty" in key for key in jwks["keys"])
```

### Integration Tests (Cross-Repo, After All Merges)

Run after all repos are merged:

```python
# integration test (runs after auth-service, client-sdk, api-gateway all merged)
def test_end_to_end_jwt_flow():
    # Real Auth Service
    auth_service = AuthService()
    
    # Real Client SDK
    client = ClientSDK()
    
    # Real API Gateway
    gateway = APIGateway()
    
    # End-to-end test
    token = auth_service.issue_token(user_id="123")
    assert client.validate(token) == True
    
    response = gateway.forward_request(
        token=token,
        downstream_url="https://api.example.com/data"
    )
    assert response.status_code == 200
```

---

## Git Workflow: Multi-Repo Features

### Branching

```
auth-service:        feat/jwt-unification
client-sdk:          feat/jwt-unification
api-gateway:         feat/jwt-unification
```

All three repos use the same feature branch name for discoverability.

### Commits

Each repo commits its own work:

```
auth-service:
  feat(auth): implement JWKS endpoint at /jwks

client-sdk:
  feat(auth): add JWT validation against cached JWKS

api-gateway:
  feat(auth): add JWT relay middleware
```

### PRs

Three separate PRs:

| PR | Repo | What it does | Blockers |
|---|---|---|---|
| #42 | auth-service | Implements JWKS endpoint | None (specification is approved) |
| #99 | client-sdk | Implements JWT validation | Can merge anytime (mocks Auth Service) |
| #55 | api-gateway | Implements JWT relay | Can merge anytime (mocks upstream services) |

All three can be in review simultaneously. Merge order doesn't matter (each repo has its own contract tests).

### Integration

After all three are merged:

```bash
# In a shared integration test repo or CD pipeline
git clone auth-service && cd auth-service && git checkout main
git clone client-sdk && cd client-sdk && git checkout main
git clone api-gateway && cd api-gateway && git checkout main

pytest ./integration-tests/
```

Run end-to-end tests. If any fail, identify which repo has a contract violation and fix in a follow-up PR.

---

## Common Pitfalls

### ❌ "We'll figure out the contract during implementation"

**Why it fails:** Repos implement different expectations, leading to incompatible code.

**Fix:** Document contracts in the primary repo's `nfrs.md` BEFORE any repo starts coding.

### ❌ "Let's just have Repo A implement everything and Repo B can copy it later"

**Why it fails:** Code duplication, maintenance burden, violates ownership.

**Fix:** Each repo implements its own portion against the shared contract. No copy-paste.

### ❌ "One repo should wait for another to finish before starting"

**Why it fails:** Sequential development defeats the purpose of multi-repo. Blocks parallelism.

**Fix:** Each repo mocks external dependencies in unit tests. Parallel development. Integration tests after merge.

### ❌ "We'll skip contract tests, the integration tests will catch everything"

**Why it fails:** Late detection of contract issues, delayed feedback.

**Fix:** Each repo has contract tests that verify its implementation against the agreed-upon spec.

### ❌ "We don't need to document which repo owns which modules"

**Why it fails:** Agents and teams don't know who implements what. Cross-repo code written in wrong repo.

**Fix:** Use the Repository Scope table in `nfrs.md`. Be explicit.

---

## Checklist: Before Implementing a Multi-Repo Feature

- [ ] All repo owners have agreed on the feature and the contract
- [ ] One "primary owner" repo is designated
- [ ] "Repository Scope" table is complete in primary repo's `nfrs.md`
- [ ] Each contract is explicitly documented (API, messages, schema, etc.)
- [ ] Each repo's `acceptance.feature` maps steps to owners
- [ ] Each repo understands what it implements vs. what it mocks
- [ ] Each repo has contract tests for its portion
- [ ] Integration test plan exists (when and where to run cross-repo tests)
- [ ] All repo owners agree on git branch naming convention
- [ ] Feature branch created in all repos simultaneously (or as soon as ready)

---

## Example: Multi-Repo Auth Feature

See: `features/example-jwt-unification/` for a complete worked example with Gherkin, NFRs, plans, and contract definitions.
