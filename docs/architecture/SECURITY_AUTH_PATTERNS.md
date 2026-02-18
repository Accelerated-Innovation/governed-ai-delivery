# Security and Authentication Patterns

This document defines allowed authentication and authorization models. All API access and secure workflows must follow these patterns. Deviations require an ADR.

---

## 1. Authentication Model

### JWT Bearer Token (OAuth2 Password or Client Credentials)

* Authentication is enforced at the **adapter layer** (`/api`) using `Authorization: Bearer <access_token>`

```
Authorization: Bearer <access_token>
```

* Tokens must:

  * Be signed with `HS256` or `RS256`
  * Include `sub`, `iat`, `exp`, and `scope` claims
  * Be validated using the shared `SECRET_KEY` or a public key

* Token validation must use a shared function:

```python
def get_current_user(token: str = Depends(oauth2_scheme)) -> UserContext:
    ...
```

* The resulting `UserContext` object is passed into ports. **Domain code must never validate tokens directly.**

### Refresh Token Policy

* Access tokens expire after 1 hour
* If using refresh tokens:

  * Store in secure HTTP-only cookies
  * Validate server-side before issuing new access tokens

---

## 2. Authorization Model

### Role-Based Access Control (RBAC)

* Use `scope` or `role` claims in JWT
* Valid roles: `user`, `admin`, `service`
* Use central check logic:

```python
def check_scope(required: str):
    ...
```

### Route enforcement pattern:

```python
@router.get("/admin/stats")
def get_admin_stats(user: UserContext = Depends(check_scope("admin"))):
    ...
```

* Never hardcode roles in route handlers
* Domain ports should receive a typed identity context (e.g., `UserContext`) without JWT details

---

## 3. Cross-Cutting Security Rules

* All protected endpoints must:

  * Use `Depends(get_current_user)` for authentication
  * Use `Depends(check_scope(...))` for authorization
* Public endpoints must be declared in `ALLOWED_PUBLIC_PATHS`
* Never decode tokens manually using `jwt.decode()` without validation

---

## 4. Identity Propagation

* Log `user_id` and `request_id` at all adapter boundaries
* Pass downstream headers:

  * `Authorization: Bearer <access_token>`
  * `X-Request-ID`

---

## 5. Account State Enforcement

* Block requests for:

  * Suspended users
  * Expired accounts
* The `UserContext` object must include flags:

  * `is_active`, `is_verified`, `is_suspended`
* Ports must receive validated account state

---

## 6. Common Violations

🚫 Skipping token validation
🚫 Extracting `user_id` from raw tokens
🚫 Inline checks like `if user.role == "admin"`
🚫 Logging token contents or passwords
🚫 Accepting passwords in query params or GET requests

---

## 7. Related Files

* `security/auth.py` — `get_current_user()`, `check_scope()`, `validate_token()`
* `models/user.py` — defines `UserContext` with roles and flags
* `middleware/security.py` — injects identity, trace headers

---

## 8. Domain Constraints

* Domain ports must never depend on:

  * JWT libraries
  * FastAPI request/response models
  * Header or cookie parsing

* Security and identity enforcement is the responsibility of the inbound adapter (API layer)

* All domain-facing methods receive a validated `UserContext` or fail early
