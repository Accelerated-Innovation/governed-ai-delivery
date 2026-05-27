# ASP.NET Core Minimal API Design Instructions

Applies to all inbound adapter files under `/Api/**`. Route handlers are responsible for HTTP concerns only. All domain logic must be delegated to inbound ports.

---

## 0. Interaction with Domain

* Handlers must call **inbound ports** (interfaces) from `Ports/Inbound/`
* Do **not** call service implementations or business logic directly
* Use constructor injection or `app.Services` to bind ports to adapter implementations
* Inputs (e.g., request records, auth) must be mapped to domain objects before calling ports
* Ports return results or raise domain exceptions; handlers translate those into HTTP responses

---

## 1. Routing

* Use path-style: `/v1/<resource>/<action>` (e.g. `/v1/users/reset-password`)
* Group related routes using `RouteGroupBuilder`:

```csharp
var users = app.MapGroup("/v1/users").RequireAuthorization();
users.MapPost("/{userId}/activate", ActivateUser);
```

* Avoid scattering route declarations across `Program.cs` — use extension methods per feature

---

## 2. HTTP Verbs & Status Codes

* Use `MapGet`, `MapPost`, `MapPut`, `MapDelete` on the route group
* Required status codes:

  * `200`: Successful GET
  * `201`: Resource created (`Results.Created(...)`)
  * `204`: No content on DELETE (`Results.NoContent()`)
  * `400`: Validation failure (`Results.ValidationProblem(...)`)
  * `401`: Authentication required (`Results.Unauthorized()`)
  * `403`: Unauthorized access (`Results.Forbid()`)
  * `404`: Not found (`Results.NotFound()`)
  * `500`: Unexpected server exceptions only (global handler)

---

## 3. Request & Response Format

* Define request DTOs as `record` types:

```csharp
public record ActivateUserRequest(string UserId);
```

* Map request DTOs to domain inputs before calling a port
* Wrap all responses in a standard envelope:

```csharp
public record ApiResponse<T>(T? Data, ErrorInfo? Error);
public record ErrorInfo(string Code, string Message);
```

* Return typed `IResult` — avoid returning raw `object` or anonymous types

---

## 4. Error Handling

* Ports may raise domain exceptions
* Use a global exception handler middleware to convert domain errors to `ProblemDetails`:

```csharp
app.UseExceptionHandler(exceptionHandlerApp =>
{
    exceptionHandlerApp.Run(async context =>
    {
        context.Response.StatusCode = StatusCodes.Status400BadRequest;
        await context.Response.WriteAsJsonAsync(new ProblemDetails
        {
            Title = "Invalid Input",
            Detail = "INVALID_EMAIL",
            Status = 400,
        });
    });
});
```

* Centralize exception logging in the middleware
* Never expose stack traces or internal error details in HTTP responses

---

## 5. Authentication & Authorization

* Apply `.RequireAuthorization()` to all protected route groups
* Auth must be enforced before calling any port
* Extract a structured identity context from `HttpContext.User` and pass it into the port:

```csharp
static async Task<IResult> ActivateUser(
    string userId,
    HttpContext ctx,
    IUserServicePort userService)
{
    var identity = UserContext.FromClaims(ctx.User);
    var user = await userService.ActivateUserAsync(userId, identity);
    return Results.Ok(new ApiResponse<UserDto>(user, null));
}
```

* Do not let domain logic depend on `ClaimsPrincipal` or auth libraries
* Include `UserId` in all logs and telemetry

---

## 6. Observability

* Use structured logging with Serilog, including:

  * `Event`, `Path`, `StatusCode`, `DurationMs`
* Include `RequestId` and `UserId` where available
* Time all requests with `app.UseMiddleware<RequestTimingMiddleware>()`
* Expose metrics via `/metrics` using `prometheus-net.AspNetCore`

---

## 7. OpenAPI Spec

* Every endpoint must include XML doc comments or `.WithSummary()` / `.WithDescription()`:

```csharp
users.MapPost("/{userId}/activate", ActivateUser)
    .WithName("ActivateUser")
    .WithSummary("Activate a user account")
    .WithDescription("Transitions a user from pending to active state.")
    .Produces<ApiResponse<UserDto>>(200)
    .ProducesProblem(400)
    .ProducesProblem(404);
```

* Use `app.MapOpenApi()` and Swashbuckle for automatic spec generation
* Validate OpenAPI schema in CI

---

## 8. Testing

* Use `Microsoft.AspNetCore.Mvc.Testing` with `WebApplicationFactory<Program>` for route tests:

```csharp
public class ActivateUserTests(WebApplicationFactory<Program> factory)
    : IClassFixture<WebApplicationFactory<Program>>
{
    [Fact]
    public async Task ActivateUser_Returns200_WhenUserExists()
    {
        var client = factory.CreateClient();
        var response = await client.PostAsync("/v1/users/abc123/activate", null);
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }
}
```

* Every route must have:

  * Input validation tests
  * Auth tests (unauthenticated, unauthorized)
  * Response shape tests
  * Port mock assertions (using NSubstitute)

---

## 9. Adapter Boundaries

The API layer is an inbound adapter located under:
```
src/Api/
```

It must not import from `Services/`, `Adapters/`, or any infrastructure library except what is needed to wire up DI. All business logic goes through ports.
