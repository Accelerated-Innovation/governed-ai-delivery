# Security and Authentication Patterns

This document defines allowed authentication and authorization models. All API access and secure workflows must follow these patterns. Deviations require an ADR.

---

## 1. Authentication Model

### JWT Bearer Token (OAuth2 Resource Server)

* Authentication is enforced at the **adapter layer** (`/api`) using `Authorization: Bearer <access_token>`

```
Authorization: Bearer <access_token>
```

* Tokens must:

  * Be signed with `HS256` or `RS256`
  * Include `sub`, `iat`, `exp`, and `scope` claims
  * Be validated using Spring Security's OAuth2 Resource Server

* Configure JWT validation in `SecurityConfig.java`:

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        return http
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/v1/public/**", "/actuator/health").permitAll()
                .anyRequest().authenticated())
            .oauth2ResourceServer(oauth2 -> oauth2
                .jwt(jwt -> jwt.jwtAuthenticationConverter(jwtAuthenticationConverter())))
            .sessionManagement(session ->
                session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .build();
    }

    @Bean
    JwtAuthenticationConverter jwtAuthenticationConverter() {
        var converter = new JwtGrantedAuthoritiesConverter();
        converter.setAuthoritiesClaimName("scope");
        var jwtConverter = new JwtAuthenticationConverter();
        jwtConverter.setJwtGrantedAuthoritiesConverter(converter);
        return jwtConverter;
    }
}
```

* The resulting `UserContext` record is resolved from the `Jwt` principal and passed into ports. **Domain code must never validate tokens directly.**

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
* Define authorization rules in `SecurityConfig` or via `@PreAuthorize`:

```java
@PreAuthorize("hasAuthority('SCOPE_admin')")
@GetMapping("/admin/stats")
public ResponseEntity<AdminStatsDto> getAdminStats(...) { ... }
```

* Never hardcode roles in controllers
* Domain ports should receive a typed `UserContext` without JWT details:

```java
public record UserContext(
    String userId,
    String role,
    boolean isActive,
    boolean isVerified,
    boolean isSuspended) {

    public static UserContext fromJwt(Jwt jwt) {
        return new UserContext(
            jwt.getSubject(),
            jwt.getClaimAsString("role"),
            Boolean.parseBoolean(jwt.getClaimAsString("is_active")),
            Boolean.parseBoolean(jwt.getClaimAsString("is_verified")),
            Boolean.parseBoolean(jwt.getClaimAsString("is_suspended"))
        );
    }
}
```

---

## 3. Cross-Cutting Security Rules

* All protected endpoints must go through Spring Security's filter chain
* Public endpoints must be explicitly allowed via `requestMatchers(...).permitAll()`
* Never decode tokens manually with a JWT library outside the security config

---

## 4. Identity Propagation

* Log `userId` and `requestId` at all adapter boundaries via MDC:

```java
MDC.put("userId", identity.userId());
MDC.put("requestId", request.getHeader("X-Request-ID"));
```

* Pass downstream service headers:

  * `Authorization: Bearer <access_token>`
  * `X-Request-ID`

---

## 5. Account State Enforcement

* Block requests for suspended or expired accounts in the inbound adapter:

```java
if (identity.isSuspended()) {
    throw new AccountSuspendedException(identity.userId());
}
```

* Ports must receive a validated `UserContext` with state flags already checked

---

## 6. Password Hashing

* Use `BCryptPasswordEncoder` from Spring Security:

```java
@Bean
public PasswordEncoder passwordEncoder() {
    return new BCryptPasswordEncoder(12);  // cost factor 12
}
```

* Never store plain-text passwords
* Never use MD5 or SHA-1 for password storage

---

## 7. Common Violations

🚫 Skipping token validation
🚫 Extracting `userId` from raw tokens without Spring Security validation
🚫 Inline role checks like `if (jwt.getClaim("role").equals("admin"))`
🚫 Logging token contents or passwords
🚫 Accepting passwords in query params or GET requests
🚫 Storing secrets in `application.yml` — use environment variables or Vault

---

## 8. Related Files

* `api/security/SecurityConfig.java` — filter chain, JWT converter
* `api/security/UserContext.java` — `fromJwt()` factory, roles, and flags
* `api/middleware/RequestEnrichmentFilter.java` — injects MDC identity and trace headers

---

## 9. Domain Constraints

* Domain ports must never depend on:

  * `org.springframework.security.*` types
  * `com.nimbusds.*` JWT parsing
  * HTTP request/response types

* Security and identity enforcement is the responsibility of the inbound adapter (API layer)

* All domain-facing methods receive a validated `UserContext` or fail early
