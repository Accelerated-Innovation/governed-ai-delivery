Follow the public API conventions defined in `docs/architecture/API_CONVENTIONS.md`.

All routes in `/api/**` must:

- Use versioned, resource-first paths (e.g., `/v1/users/login`)
- Follow HTTP verb and status code standards
- Define request and response models using `BaseModel`
- Wrap responses using the standard `ApiResponse` envelope
- Authenticate using `Depends(get_current_user)`
- Authorize using `Depends(check_scope(...))` if required
- Delegate all logic to inbound ports (`ports/inbound/**`)
- Never access domain services, repositories, or adapter logic directly
- Avoid leaking FastAPI types into service or port layers
- Include OpenAPI metadata: summary, description, status codes, response model

All FastAPI routes are inbound adapters. They must stay thin, authenticated, and port-driven.
