# Security and Authentication Instructions

These rules apply to all files under `/security/**`, `/auth/**`, and any code handling login, tokens, identity, or protected routes. They align with the architectural patterns in `SECURITY_AUTH_PATTERNS.md`.

---

## 1. Authentication

- Use OAuth2 password or client credentials flow
- Enforce bearer token validation using `Depends(get_current_user)`
- Token parsing must:
  - Verify signature using `PyJWT` or `jose.jwt`
  - Check `exp`, `iat`, and `sub` claims
  - Validate required scopes or roles
- Reject unsigned, malformed, or expired tokens
- Never decode JWTs without verifying signature

Example:
```python
from fastapi import Depends, HTTPException
from jose import JWTError, jwt

def get_current_user(token: str = Depends(oauth2_scheme)) -> UserContext:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        ...
    except JWTError:
        raise credentials_exception
```

---

## 2. Authorization

- Use Role-Based Access Control (RBAC)
- Roles must be included in JWT (`role` or `scope` claim)
- Use `Depends(check_scope("admin"))` to guard protected endpoints
- Centralize role checks—do not hardcode inline logic

---

## 3. Secrets and Config

- Never hardcode credentials (e.g., `SECRET_KEY`, DB passwords)
- Load from environment via `BaseSettings`
- Never commit `.env`, `.pem`, `.key`, or credential files

---

## 4. Secure Storage

- Hash passwords using `bcrypt` or `argon2` via `passlib`
- Never log:
  - Raw credentials
  - Tokens
  - User PII
- Encrypt sensitive data at rest when required (e.g., for compliance)

---

## 5. Error Handling and Logging

- Return only:
  - `401 Unauthorized` for unauthenticated
  - `403 Forbidden` for unauthorized
- Never expose stack traces or debug output to clients
- All logs must include:
  - `request_id`, `user_id`
  - Masked identifiers (emails, tokens)
- Use Opentelemetry and structured logging
---

## 6. Input Validation

- Use strict `pydantic` models for auth inputs
- Validate:
  - Emails via `EmailStr`
  - Passwords with length and format constraints

Example:
```python
class LoginRequest(BaseModel):
    email: EmailStr
    password: constr(min_length=8, max_length=64)
```

---

## 7. Security Headers

Set the following headers via middleware:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Strict-Transport-Security: max-age=63072000; includeSubDomains`
- `Content-Security-Policy` (if applicable)

---

## 8. Testing Requirements

- Unit test all:
  - Token parsing
  - Role/scope enforcement
  - Auth failure paths
- Include security regression tests:
  - Token reuse
  - Brute-force login attempts
  - Role escalation attempts

---

## 9. Forbidden Practices

🚫 Decoding JWT without verification  
🚫 Storing tokens in plaintext  
🚫 Using weak hash functions (MD5, SHA1)  
🚫 Using `eval()` or `exec()`  
🚫 Skipping validation or HTTPS in deployment

---

## 10. Domain Alignment

- Authentication/authorization is handled only in the API and auth adapter layer
- Domain services receive a validated `UserContext`
- No business logic should depend on raw tokens or header access
