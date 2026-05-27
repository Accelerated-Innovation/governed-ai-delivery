# Security and Authentication Patterns

This document defines allowed authentication and authorization models. All API access and secure workflows must follow these patterns. Deviations require an ADR.

---

## 1. Authentication Model

### JWT Bearer Token

* Authentication is enforced at the **adapter layer** (`internal/api`) using `Authorization: Bearer <access_token>`

```
Authorization: Bearer <access_token>
```

* Tokens must:

  * Be signed with `HS256` or `RS256`
  * Include `sub`, `iat`, `exp`, and `scope` claims
  * Be validated using `golang-jwt/jwt/v5`

* Implement auth as Gin middleware:

```go
// internal/api/middleware/auth.go
func AuthMiddleware(secret []byte) gin.HandlerFunc {
    return func(c *gin.Context) {
        authHeader := c.GetHeader("Authorization")
        if !strings.HasPrefix(authHeader, "Bearer ") {
            c.AbortWithStatusJSON(http.StatusUnauthorized,
                ProblemDetail{Status: 401, Title: "Unauthorized"})
            return
        }
        tokenString := strings.TrimPrefix(authHeader, "Bearer ")

        token, err := jwt.ParseWithClaims(tokenString, &Claims{},
            func(t *jwt.Token) (any, error) {
                if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
                    return nil, fmt.Errorf("unexpected signing method: %v", t.Header["alg"])
                }
                return secret, nil
            })
        if err != nil || !token.Valid {
            c.AbortWithStatusJSON(http.StatusUnauthorized,
                ProblemDetail{Status: 401, Title: "Invalid Token"})
            return
        }

        claims := token.Claims.(*Claims)
        c.Set("identity", UserContextFromClaims(claims))
        c.Next()
    }
}
```

* The resulting `UserContext` struct is stored in `c.Set("identity", ...)` and passed into ports. **Domain code must never validate tokens directly.**

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
* Implement an `RequireRole` middleware:

```go
func RequireRole(role string) gin.HandlerFunc {
    return func(c *gin.Context) {
        identity := c.MustGet("identity").(domain.UserContext)
        if identity.Role != role {
            c.AbortWithStatusJSON(http.StatusForbidden,
                ProblemDetail{Status: 403, Title: "Forbidden"})
            return
        }
        c.Next()
    }
}
```

### Route enforcement pattern:

```go
admin := v1.Group("/admin")
admin.Use(RequireRole("admin"))
admin.GET("/stats", handler.GetAdminStats)
```

* Never hardcode roles in route handlers
* Domain ports should receive a typed `UserContext` without JWT details

---

## 3. Cross-Cutting Security Rules

* All protected routes must go through `AuthMiddleware`
* Public routes must be registered before applying `AuthMiddleware` to the group
* Never decode tokens manually — always use `golang-jwt/jwt`

---

## 4. Identity Propagation

* Log `user_id` and `request_id` at all adapter boundaries:

```go
logger := zap.L().With(
    zap.String("user_id", identity.UserID),
    zap.String("request_id", c.GetString("RequestID")),
)
logger.Info("processing_request")
```

* Pass downstream service headers:

  * `Authorization: Bearer <access_token>`
  * `X-Request-ID`

---

## 5. Account State Enforcement

* Block requests for suspended or expired accounts in the handler:

```go
identity := c.MustGet("identity").(domain.UserContext)
if identity.IsSuspended {
    c.AbortWithStatusJSON(http.StatusForbidden,
        ProblemDetail{Status: 403, Title: "Account Suspended"})
    return
}
```

* The `UserContext` struct must include state flags:

```go
type UserContext struct {
    UserID      string
    Role        string
    IsActive    bool
    IsVerified  bool
    IsSuspended bool
}

type Claims struct {
    jwt.RegisteredClaims
    Role        string `json:"role"`
    IsActive    bool   `json:"is_active"`
    IsVerified  bool   `json:"is_verified"`
    IsSuspended bool   `json:"is_suspended"`
}

func UserContextFromClaims(claims *Claims) UserContext {
    return UserContext{
        UserID:      claims.Subject,
        Role:        claims.Role,
        IsActive:    claims.IsActive,
        IsVerified:  claims.IsVerified,
        IsSuspended: claims.IsSuspended,
    }
}
```

* Ports must receive a validated `UserContext` with state flags already checked

---

## 6. Password Hashing

* Use `golang.org/x/crypto/bcrypt` for password hashing:

```go
import "golang.org/x/crypto/bcrypt"

hash, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost) // cost 10
err = bcrypt.CompareHashAndPassword(hash, []byte(password))
```

* Never store plain-text passwords
* Never use MD5 or SHA-1 for password storage

---

## 7. Common Violations

🚫 Skipping token validation
🚫 Extracting `user_id` from raw tokens without `golang-jwt` parsing
🚫 Inline role checks like `if claims["role"] == "admin"`
🚫 Logging token contents or passwords
🚫 Accepting passwords in query params or GET requests
🚫 Hardcoding secrets in source code — use environment variables or a secrets manager

---

## 8. Related Files

* `internal/api/middleware/auth.go` — `AuthMiddleware`, `RequireRole`, `UserContextFromClaims`
* `internal/domain/models/user_context.go` — `UserContext` struct and flags
* `internal/api/middleware/request_id.go` — injects `RequestID` into context and logs

---

## 9. Domain Constraints

* Domain ports must never depend on:

  * `golang-jwt/jwt` or any JWT library
  * Gin `*gin.Context`
  * Header or cookie parsing

* Security and identity enforcement is the responsibility of the inbound adapter (API layer)

* All domain-facing methods receive a validated `UserContext` or fail early
