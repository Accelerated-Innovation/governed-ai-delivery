# Security and Authentication — Adapter Layer

**Your project's security patterns:** `docs/backend/architecture/SECURITY_AUTH_PATTERNS.md`

Read this document before implementing authentication or authorization. It defines your project's auth model, token strategy, and credential handling.

**Universal constraints (apply to any language):**
- All inbound routes must authenticate before calling any port
- Pass a validated `UserContext` or `Claims` object to the domain, never raw tokens
- Verify token signatures and validate claims (`exp`, `iat`, `sub`) before use
- Reject unsigned, malformed, or expired tokens — never skip signature verification
- Use Role-Based Access Control (RBAC) for authorization; roles/scopes come from validated tokens
- Never hardcode credentials — load all secrets from environment or secure vaults
- Never log raw credentials, tokens, or sensitive user data
- Return `401 Unauthorized` for failed authentication, `403 Forbidden` for insufficient authorization
- Hash passwords using strong algorithms (bcrypt, scrypt, argon2 equivalent)
- Use secure transport for all credential exchanges (HTTPS-only, secure cookies for tokens)
- Domain services must not depend on auth libraries or token types

**Error handling:**
- Ensure stack traces are never exposed to HTTP clients
- Include `request_id` and (masked) `user_id` in all security-related logs
