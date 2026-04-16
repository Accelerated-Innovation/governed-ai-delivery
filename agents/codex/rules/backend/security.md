# Security and Authentication Rules

Align with architectural patterns in `docs/backend/architecture/SECURITY_AUTH_PATTERNS.md`.

## Authentication

- Use OAuth2 password or client credentials flow
- Enforce bearer token validation using `Depends(get_current_user)`
- Token parsing must verify signature, check `exp`/`iat`/`sub` claims, and validate scopes
- Reject unsigned, malformed, or expired tokens — never decode JWTs without verifying signature

## Authorization

- Use Role-Based Access Control (RBAC) with roles in JWT (`role` or `scope` claim)
- Use `Depends(check_scope("admin"))` to guard protected endpoints
- Centralize role checks — do not hardcode inline logic

## Secrets and Config

- Never hardcode credentials — load from environment via `BaseSettings`
- Never commit `.env`, `.pem`, `.key`, or credential files

## Secure Storage

- Hash passwords using `bcrypt` or `argon2` via `passlib`
- Never log raw credentials, tokens, or user PII

## Error Handling

- Return `401 Unauthorized` for unauthenticated, `403 Forbidden` for unauthorized
- Never expose stack traces or debug output to clients
- All logs must include `request_id` and `user_id` with masked identifiers

## Input Validation

- Use strict `pydantic` models for auth inputs
- Validate emails via `EmailStr`, passwords with length and format constraints

## Security Headers

Set via middleware: `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`, `Content-Security-Policy`.

## Domain Alignment

Authentication and authorization are handled only in the API and auth adapter layer. Domain services receive a validated `UserContext` — no business logic depends on raw tokens.

## Forbidden

- Decoding JWT without verification
- Storing tokens in plaintext
- Using weak hash functions (MD5, SHA1)
- Using `eval()` or `exec()`
