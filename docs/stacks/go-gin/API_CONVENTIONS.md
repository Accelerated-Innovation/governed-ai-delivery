# Gin API Design Instructions

Applies to all inbound adapter files under `/api/**`. Route handlers are responsible for HTTP concerns only. All domain logic must be delegated to inbound ports.

---

## 0. Interaction with Domain

* Handlers must call **inbound ports** (Go interfaces) from `ports/inbound/`
* Do **not** call service implementations or business logic directly
* Use constructor injection or `wire` to bind ports to handler structs
* Inputs (e.g., request structs, auth) must be mapped to domain objects before calling ports
* Ports return results or errors; handlers translate those into HTTP responses

---

## 1. Routing

* Use path-style: `/v1/<resource>/<action>` (e.g. `/v1/users/reset-password`)
* Group related routes using `router.Group()`:

```go
v1 := router.Group("/v1")
v1.Use(AuthMiddleware())
{
    users := v1.Group("/users")
    users.POST("/:userId/activate", handler.ActivateUser)
}
```

* Avoid scattering route declarations — register all routes in a single wiring function

---

## 2. HTTP Verbs & Status Codes

* Use `router.GET`, `router.POST`, `router.PUT`, `router.DELETE`
* Required status codes:

  * `200`: Successful GET — `c.JSON(http.StatusOK, body)`
  * `201`: Resource created — `c.JSON(http.StatusCreated, body)`
  * `204`: No content on DELETE — `c.Status(http.StatusNoContent)`
  * `400`: Validation failure — `c.JSON(http.StatusBadRequest, problemDetail(...))`
  * `401`: Authentication required — `c.JSON(http.StatusUnauthorized, ...)`
  * `403`: Unauthorized access — `c.JSON(http.StatusForbidden, ...)`
  * `404`: Not found — `c.JSON(http.StatusNotFound, problemDetail(...))`
  * `500`: Unexpected server exceptions only — global recovery middleware

---

## 3. Request & Response Format

* Define request structs with validation tags:

```go
type ActivateUserRequest struct {
    UserID string `uri:"userId" binding:"required,uuid"`
}
```

* Map request structs to domain inputs before calling a port
* Wrap all responses in a standard envelope:

```go
type APIResponse[T any] struct {
    Data  *T          `json:"data,omitempty"`
    Error *ErrorInfo  `json:"error,omitempty"`
}

type ErrorInfo struct {
    Code    string `json:"code"`
    Message string `json:"message"`
}
```

* Avoid returning raw `map[string]any` or `gin.H` for typed responses

---

## 4. Error Handling

* Ports may return domain errors
* Use a ProblemDetail helper for RFC 9457 error responses:

```go
type ProblemDetail struct {
    Type   string `json:"type"`
    Title  string `json:"title"`
    Status int    `json:"status"`
    Detail string `json:"detail"`
}

func problemDetail(status int, title, detail string) ProblemDetail {
    return ProblemDetail{
        Type:   fmt.Sprintf("https://example.com/errors/%d", status),
        Title:  title,
        Status: status,
        Detail: detail,
    }
}
```

* Use a global recovery middleware to catch panics and convert to 500 responses
* Use `errors.Is` to identify domain errors and map to status codes:

```go
if errors.Is(err, domain.ErrUserNotFound) {
    c.JSON(http.StatusNotFound, problemDetail(404, "User Not Found", err.Error()))
    return
}
```

* Centralize exception logging in the error handler middleware
* Never expose stack traces or internal error details in HTTP responses

---

## 5. Authentication & Authorization

* Use a JWT middleware based on `golang-jwt/jwt`:

```go
func AuthMiddleware(secret []byte) gin.HandlerFunc {
    return func(c *gin.Context) {
        authHeader := c.GetHeader("Authorization")
        tokenString := strings.TrimPrefix(authHeader, "Bearer ")
        token, err := jwt.ParseWithClaims(tokenString, &Claims{},
            func(t *jwt.Token) (any, error) {
                return secret, nil
            })
        if err != nil || !token.Valid {
            c.AbortWithStatusJSON(http.StatusUnauthorized,
                problemDetail(401, "Unauthorized", "invalid token"))
            return
        }
        c.Set("identity", UserContextFromClaims(token.Claims.(*Claims)))
        c.Next()
    }
}
```

* Extract `UserContext` from `c.MustGet("identity")` and pass into the port
* Do not let domain logic depend on JWT types or Gin's `Context`
* Include `user_id` in all logs and telemetry via the `zap.Logger`

---

## 6. Observability

* Use a request-scoped `*zap.Logger` child with structured fields:

```go
logger := zap.L().With(
    zap.String("request_id", c.GetString("RequestID")),
    zap.String("user_id", identity.UserID),
    zap.String("path", c.FullPath()),
)
logger.Info("activate_user_requested")
```

* Expose metrics via `/metrics` using `prometheus/client_golang`
* Add `otelgin.Middleware("your-service")` for automatic trace propagation

---

## 7. OpenAPI Spec

* Every handler must include `swaggo/swag` doc comments:

```go
// ActivateUser godoc
// @Summary      Activate a user account
// @Description  Transitions a user from pending to active state
// @Tags         users
// @Accept       json
// @Produce      json
// @Param        userId  path      string              true  "User ID"
// @Success      200     {object}  APIResponse[UserDTO]
// @Failure      404     {object}  ProblemDetail
// @Router       /v1/users/{userId}/activate [post]
// @Security     BearerAuth
func (h *UserHandler) ActivateUser(c *gin.Context) { ... }
```

* Run `swag init` to regenerate the OpenAPI spec
* Validate OpenAPI schema in CI

---

## 8. Testing

* Use `net/http/httptest` with Gin's `ServeHTTP` for route tests:

```go
func TestActivateUser_Returns200(t *testing.T) {
    mockService := new(MockUserService)
    mockService.On("ActivateUser", "abc123", mock.Anything).Return(&domain.User{ID: "abc123"}, nil)

    handler := NewUserHandler(mockService)
    router := gin.New()
    router.POST("/v1/users/:userId/activate", handler.ActivateUser)

    w := httptest.NewRecorder()
    req, _ := http.NewRequest("POST", "/v1/users/abc123/activate", nil)
    req.Header.Set("Authorization", "Bearer "+validToken)

    router.ServeHTTP(w, req)

    assert.Equal(t, http.StatusOK, w.Code)
    mockService.AssertExpectations(t)
}
```

* Every route must have:

  * Input validation tests
  * Auth tests (unauthenticated, unauthorized)
  * Response shape tests
  * Port mock assertions (using testify/mock)

---

## 9. Adapter Boundaries

The API layer is an inbound adapter located under:
```
internal/api/
```

It must not import from `internal/services/`, `internal/adapters/`, or any infrastructure package except what is needed to wire up handlers. All business logic goes through ports.
