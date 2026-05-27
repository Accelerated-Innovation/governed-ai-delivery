# Security and Authentication Patterns

This document defines allowed authentication and authorization models. All API access and secure workflows must follow these patterns. Deviations require an ADR.

---

## 1. Authentication Model

### JWT Bearer Token (OAuth2 Password or Client Credentials)

* Authentication is enforced at the **adapter layer** (`/Api`) using `Authorization: Bearer <access_token>`

```
Authorization: Bearer <access_token>
```

* Tokens must:

  * Be signed with `HS256` or `RS256`
  * Include `sub`, `iat`, `exp`, and `scope` claims
  * Be validated using `Microsoft.AspNetCore.Authentication.JwtBearer`

* Configure bearer authentication in `Program.cs`:

```csharp
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true,
            ValidIssuer = builder.Configuration["Jwt:Issuer"],
            ValidAudience = builder.Configuration["Jwt:Audience"],
            IssuerSigningKey = new SymmetricSecurityKey(
                Encoding.UTF8.GetBytes(builder.Configuration["Jwt:Secret"]!))
        };
    });
```

* The resulting `UserContext` record is resolved from `HttpContext.User.Claims` and passed into ports. **Domain code must never validate tokens directly.**

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
* Define authorization policies in `Program.cs`:

```csharp
builder.Services.AddAuthorization(options =>
{
    options.AddPolicy("AdminOnly", policy =>
        policy.RequireClaim("role", "admin"));
});
```

### Route enforcement pattern:

```csharp
app.MapGet("/v1/admin/stats", GetAdminStats)
   .RequireAuthorization("AdminOnly");
```

* Never hardcode roles in route handlers
* Domain ports should receive a typed identity context (e.g., `UserContext`) without JWT details

---

## 3. Cross-Cutting Security Rules

* All protected endpoints must have `.RequireAuthorization()` applied
* Public endpoints must be explicitly marked with `.AllowAnonymous()`
* Never decode tokens manually — always use the ASP.NET Core auth middleware

---

## 4. Identity Propagation

* Log `UserId` and `RequestId` at all adapter boundaries using Serilog enrichers:

```csharp
Log.ForContext("UserId", identity.UserId)
   .ForContext("RequestId", ctx.TraceIdentifier)
   .Information("Processing {Action}", "ActivateUser");
```

* Pass downstream service headers:

  * `Authorization: Bearer <access_token>`
  * `X-Request-ID`

---

## 5. Account State Enforcement

* Block requests for:

  * Suspended users
  * Expired accounts
* The `UserContext` record must include flags:

```csharp
public record UserContext(
    string UserId,
    string Role,
    bool IsActive,
    bool IsVerified,
    bool IsSuspended)
{
    public static UserContext FromClaims(ClaimsPrincipal principal) => new(
        UserId: principal.FindFirstValue(ClaimTypes.NameIdentifier)!,
        Role: principal.FindFirstValue(ClaimTypes.Role) ?? "user",
        IsActive: bool.Parse(principal.FindFirstValue("is_active") ?? "true"),
        IsVerified: bool.Parse(principal.FindFirstValue("is_verified") ?? "false"),
        IsSuspended: bool.Parse(principal.FindFirstValue("is_suspended") ?? "false")
    );
}
```

* Ports must receive validated account state

---

## 6. Password Hashing

* Use `BCrypt.Net-Next` or `Microsoft.AspNetCore.Identity.IPasswordHasher<T>` for password hashing
* Never store plain-text passwords
* Never use MD5 or SHA-1 for password storage

---

## 7. Common Violations

🚫 Skipping token validation
🚫 Extracting `UserId` from raw tokens without validation
🚫 Inline checks like `if (user.Role == "admin")`
🚫 Logging token contents or passwords
🚫 Accepting passwords in query params or GET requests
🚫 Storing secrets in `appsettings.json` — use environment variables or Azure Key Vault

---

## 8. Related Files

* `Api/Security/UserContext.cs` — `FromClaims()` factory, roles, and flags
* `Api/Middleware/RequestEnrichmentMiddleware.cs` — injects identity and trace headers
* `Program.cs` — auth/authz service registration

---

## 9. Domain Constraints

* Domain ports must never depend on:

  * `System.IdentityModel.Tokens.Jwt` or any JWT library
  * ASP.NET Core request/response models
  * Header or cookie parsing

* Security and identity enforcement is the responsibility of the inbound adapter (API layer)

* All domain-facing methods receive a validated `UserContext` or fail early
