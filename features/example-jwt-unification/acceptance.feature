Feature: Unified JWT authentication across services

  As a platform operator
  I want all services to use a centralized JWT issued by Auth Service
  So that user identity is consistent across the platform and client-side validation reduces latency

  Background:
    Given Auth Service is running and healthy
    And Client SDK is available and integrated
    And API Gateway is running
    And each service has access to the JWKS endpoint

  Scenario: Client obtains JWT from Auth Service
    Given a user "alice@example.com" exists in Auth Service
    When Client calls Auth Service `POST /auth/login` with email and password
    Then Auth Service returns HTTP 200
    And response contains a signed JWT
    And JWT is in RS256 format (RSA with SHA-256)
    And JWT contains claims: `sub`, `email`, `iat`, `exp`

  Scenario: Client caches and reuses JWKS
    Given Client has not yet loaded JWKS
    When Client makes first request to validate a JWT
    Then Client fetches JWKS from Auth Service `GET /jwks`
    And Client caches JWKS with TTL of 24 hours
    And Client validates the JWT locally against cached JWKS
    And JWT validation succeeds

  Scenario: Client reuses cached JWKS for subsequent tokens
    Given Client has cached JWKS from Auth Service
    When Client receives a new JWT from Auth Service
    Then Client validates the new JWT against cached JWKS
    And Client does NOT fetch JWKS again
    And validation succeeds

  Scenario: Client refreshes JWKS on cache expiry
    Given Client's cached JWKS is older than 24 hours
    When Client receives a JWT and attempts validation
    Then Client fetches fresh JWKS from Auth Service
    And Client updates its cache
    And Client validates the JWT against the new JWKS
    And validation succeeds

  Scenario: API Gateway validates token and relays request
    Given Client has a valid JWT from Auth Service
    When Client calls API Gateway `GET /api/data` with Bearer token in Authorization header
    Then API Gateway receives the token
    And API Gateway validates the token against JWKS (or delegates to Client SDK)
    And API Gateway forwards the request to the downstream service
    And Authorization header is preserved in the forwarded request
    And downstream service receives the request with the JWT

  Scenario: Expired token is rejected
    Given a JWT that expired 1 hour ago
    When Client attempts to validate it
    Then validation fails with error "token_expired"
    And Client should request a new token from Auth Service

  Scenario: Invalid JWT signature is detected
    Given a forged JWT (signed with a different key)
    When Client attempts to validate it against the real JWKS
    Then validation fails with error "invalid_signature"
    And Client rejects the token

  Scenario: JWKS key rotation is transparent to clients
    Given Auth Service has rotated its signing keys
    And new key is published at `GET /jwks` with `kid` (key ID)
    And Client has cached the old JWKS
    When Client receives a JWT signed with the new key
    And validation against cached JWKS fails
    Then Client fetches fresh JWKS
    And Client finds the new key by `kid`
    And Client validates the JWT successfully with the new key
