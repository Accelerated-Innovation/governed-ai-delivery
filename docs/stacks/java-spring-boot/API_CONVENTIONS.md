# Spring Web MVC API Design Instructions

Applies to all inbound adapter files under `/api/**`. Route handlers are responsible for HTTP concerns only. All domain logic must be delegated to inbound ports.

---

## 0. Interaction with Domain

* Handlers must call **inbound ports** (interfaces) from `ports/inbound/`
* Do **not** call service implementations or business logic directly
* Use constructor injection (`@RequiredArgsConstructor` or explicit constructor) to bind ports
* Inputs (e.g., request records, auth) must be mapped to domain objects before calling ports
* Ports return results or throw domain exceptions; handlers translate those into HTTP responses

---

## 1. Routing

* Use path-style: `/v1/<resource>/<action>` (e.g. `/v1/users/reset-password`)
* Use `@RestController` with `@RequestMapping` at class level for prefix:

```java
@RestController
@RequestMapping("/v1/users")
public class UserController {
    ...
}
```

* Avoid scattering route declarations — one controller per resource

---

## 2. HTTP Verbs & Status Codes

* Use `@GetMapping`, `@PostMapping`, `@PutMapping`, `@DeleteMapping`
* Return `ResponseEntity<T>` to control status codes explicitly:

  * `200`: Successful GET — `ResponseEntity.ok(body)`
  * `201`: Resource created — `ResponseEntity.created(location).body(body)`
  * `204`: No content on DELETE — `ResponseEntity.noContent().build()`
  * `400`: Validation failure — resolved via `@ExceptionHandler` / `@ControllerAdvice`
  * `401`: Authentication required — Spring Security handles automatically
  * `403`: Unauthorized access — Spring Security handles automatically
  * `404`: Not found — `ResponseEntity.notFound().build()`
  * `500`: Unexpected server exceptions only — global handler

---

## 3. Request & Response Format

* Define request DTOs as Java records:

```java
public record ActivateUserRequest(@NotBlank String userId) {}
```

* Map request DTOs to domain inputs before calling a port
* Wrap all responses in a standard envelope:

```java
public record ApiResponse<T>(T data, ErrorInfo error) {
    public static <T> ApiResponse<T> ok(T data) {
        return new ApiResponse<>(data, null);
    }
}

public record ErrorInfo(String code, String message) {}
```

* Return `ResponseEntity<ApiResponse<T>>` — avoid returning raw `Map` or `Object`

---

## 4. Error Handling

* Ports may throw domain exceptions
* Use `@ControllerAdvice` to convert domain errors to `ProblemDetail` (RFC 9457):

```java
@ControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(UserNotFoundException.class)
    public ResponseEntity<ProblemDetail> handleNotFound(UserNotFoundException ex) {
        var problem = ProblemDetail.forStatusAndDetail(
            HttpStatus.NOT_FOUND, ex.getMessage());
        problem.setTitle("User Not Found");
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(problem);
    }

    @ExceptionHandler(InvalidInputException.class)
    public ResponseEntity<ProblemDetail> handleInvalidInput(InvalidInputException ex) {
        var problem = ProblemDetail.forStatusAndDetail(
            HttpStatus.BAD_REQUEST, ex.getMessage());
        problem.setTitle("Invalid Input");
        return ResponseEntity.badRequest().body(problem);
    }
}
```

* Centralize exception logging in the advice
* Never expose stack traces or internal error details in HTTP responses

---

## 5. Authentication & Authorization

* Use Spring Security to protect all endpoints:

```java
@Bean
public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
    return http
        .authorizeHttpRequests(auth -> auth
            .requestMatchers("/v1/public/**").permitAll()
            .anyRequest().authenticated())
        .oauth2ResourceServer(oauth2 -> oauth2.jwt(Customizer.withDefaults()))
        .build();
}
```

* Auth must be enforced before calling any port
* Extract a structured identity context from `Authentication` and pass into the port:

```java
@PostMapping("/{userId}/activate")
public ResponseEntity<ApiResponse<UserDto>> activateUser(
        @PathVariable String userId,
        @AuthenticationPrincipal Jwt jwt) {
    var identity = UserContext.fromJwt(jwt);
    var user = userService.activateUser(userId, identity);
    return ResponseEntity.ok(ApiResponse.ok(UserDto.from(user)));
}
```

* Do not let domain logic depend on Spring Security types
* Include `userId` in all logs and telemetry via MDC

---

## 6. Observability

* Use SLF4J with Logback (JSON encoder) for structured logging:

```java
private static final Logger log = LoggerFactory.getLogger(UserController.class);

log.atInfo()
   .addKeyValue("event", "user_activate_requested")
   .addKeyValue("userId", userId)
   .addKeyValue("durationMs", duration)
   .log("User activation requested");
```

* Include `requestId` and `userId` via MDC:

```java
MDC.put("requestId", request.getHeader("X-Request-ID"));
MDC.put("userId", identity.userId());
```

* Expose metrics via `/actuator/prometheus` using Micrometer

---

## 7. OpenAPI Spec

* Every endpoint must include `@Operation` and `@ApiResponse` annotations from `springdoc-openapi`:

```java
@Operation(
    summary = "Activate a user account",
    description = "Transitions a user from pending to active state."
)
@ApiResponse(responseCode = "200", description = "User activated")
@ApiResponse(responseCode = "404", description = "User not found")
@PostMapping("/{userId}/activate")
public ResponseEntity<ApiResponse<UserDto>> activateUser(...) { ... }
```

* Use `springdoc-openapi-starter-webmvc-ui` for automatic spec generation
* Validate OpenAPI schema in CI

---

## 8. Testing

* Use `@SpringBootTest` with `MockMvc` for route tests:

```java
@SpringBootTest
@AutoConfigureMockMvc
class UserControllerTest {

    @Autowired MockMvc mockMvc;
    @MockBean IUserServicePort userService;

    @Test
    void activateUser_returns200_whenUserExists() throws Exception {
        when(userService.activateUser(eq("abc123"), any()))
            .thenReturn(new User("abc123", "test@example.com", Status.ACTIVE));

        mockMvc.perform(post("/v1/users/abc123/activate")
                .with(jwt()))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.data.id").value("abc123"));
    }
}
```

* Every route must have:

  * Input validation tests
  * Auth tests (unauthenticated, unauthorized)
  * Response shape tests
  * Port mock assertions (using Mockito)

---

## 9. Adapter Boundaries

The API layer is an inbound adapter located under:
```
src/main/java/.../api/
```

It must not import from `services/`, `adapters/`, or any infrastructure library except what is needed for DI. All business logic goes through ports.
