# Non-Functional Requirements: Unified JWT Authentication

## Repository Scope

**Scope:** `multi-repo`

This feature spans multiple repositories:

| Repository | Owner Team | Modules/Services | Contracts to Implement |
|---|---|---|---|
| auth-service | Identity Team | JWT generation, JWKS endpoint, key rotation | JWKS HTTP endpoint at `GET /jwks` (RFC 7517 format), JWT in RS256 format |
| client-sdk | SDK Team | Token validation, JWKS caching, key rotation handling | Client-side JWT validation against JWKS, 24-hour cache with refresh logic |
| api-gateway | Platform Team | Token relay, validation delegation | Accept Bearer token, validate/relay to downstream services, preserve Authorization header |

**Primary Owner:** auth-service (orchestrates JWT issuance and JWKS publication)

**Key Cross-Repo Contracts:**
- Auth Service publishes JWKS endpoint at `GET /jwks` (JSON Web Key Set per RFC 7517)
- Auth Service issues JWTs in RS256 format with `kid` (key ID) header
- Client SDK loads JWKS on first use and caches for 24 hours with refresh on validation failure
- API Gateway validates tokens using Client SDK or its own JWKS cache
- Key rotation: new keys appear in JWKS; old keys are deprecated (not removed immediately)

---

## Out of scope

- Token revocation / blocklist (CRL/OCSP) — separate feature
- Refresh-token rotation and session management — future increment
- OAuth2 / OIDC authorization-code flows — out of scope (this feature covers JWT issuance and validation only)

---

## Performance

- **JWT generation latency:** p95 < 100ms (Auth Service)
- **JWKS fetch latency:** p95 < 50ms (Auth Service `GET /jwks`)
- **Token validation latency:** < 10ms (Client SDK, in-memory JWKS cache)
- **Cache hit rate:** >= 99% for Client SDK (refresh only on expiry or validation failure)

## Availability

- **JWKS endpoint uptime:** 99.95% (Auth Service)
- **Graceful degradation:** Client SDK falls back to fetching fresh JWKS if cached version fails validation
- **API Gateway:** Token relay succeeds if Client SDK or gateway-local JWKS validation passes
- **Key rotation:** Old keys remain valid for 24 hours after rotation (allows in-flight token acceptance)

## Security

- **JWT signing algorithm:** RS256 (RSA 2048-bit, SHA-256)
- **Key rotation:** New signing key generated monthly; old key deprecated but valid for 24 hours
- **Token expiration:** All tokens expire within 1 hour (configurable per service)
- **JWKS validation:** Client SDK verifies `alg: RS256` and rejects other algorithms
- **No token logging:** Auth Service, Client SDK, and API Gateway never log full JWT values (only `kid` and `exp`)

## Compliance

- **Token data:** No PII in JWT claims unless explicitly required and encrypted
- **JWKS caching:** Client SDK caches without storing to disk (memory only, not persistent)
- **Audit trail:** Auth Service logs token issuance events with user ID, issue time, expiration

## Scalability

- **Concurrent validations:** Client SDK supports concurrent token validations (thread-safe)
- **JWKS caching:** No per-service connection pooling required (stateless HTTP GET)
- **Auth Service throughput:** Support 10,000+ JWT issuance requests per second

## Observability

- **Structured logging:** Log token issuance, validation success, validation failure with `kid`, `exp`, outcome
- **Metrics:** 
  - `jwt.issued_total` — JWT count by service
  - `jwt.validation_success_total` — Successful validations
  - `jwt.validation_failure_total` — Failed validations (signature, expiry, algorithm)
  - `jwks.cache_hit_ratio` — Client SDK cache hit percentage
- **Tracing:** Token validation includes trace ID correlation

## Dependencies

- **Auth Service:** Depends on key management system (KMS) for signing key storage and rotation
- **Client SDK:** Depends on HTTP client library (e.g., `requests`, `httpx` for Python)
- **Client SDK:** Depends on JWT library (e.g., `PyJWT`) for RS256 validation
- **API Gateway:** Depends on Client SDK or embedded JWT validation library
- **No circular dependencies:** Client SDK does not depend on Auth Service or API Gateway

## Testing Requirements

- **Auth Service:**
  - Unit tests for JWT generation, signing, claims population
  - Contract tests for `GET /jwks` endpoint (verifies RFC 7517 format)
  - Tests for key rotation (old key still valid, new key in JWKS)
  - Tests for token expiration (tokens expire at specified `exp` time)

- **Client SDK:**
  - Unit tests for JWT validation against JWKS (mocked JWKS)
  - Unit tests for JWKS caching (24-hour TTL, refresh on failure)
  - Unit tests for key rotation handling (validation finds key by `kid`)
  - Contract tests for `GET /jwks` endpoint (real Auth Service)

- **API Gateway:**
  - Unit tests for token relay and Authorization header preservation
  - Contract tests for downstream service integration
  - Integration tests with real Auth Service and Client SDK

- **End-to-end tests:**
  - Client obtains JWT from Auth Service
  - Client validates token locally against cached JWKS
  - Client calls API Gateway with valid token
  - API Gateway relays request to downstream service
  - Downstream service receives the token and can parse claims
