# Next.js Shared Code

- Shared code must be feature-neutral and cannot import feature internals.
- Prefer small accessible primitives over a catch-all component library.
- Map Tailwind utilities through approved semantic brand tokens.
- Shared API infrastructure may handle base URLs, headers, timeouts, and typed
  transport errors only.
- No domain rules, database access, credentials, or server secrets in shared
  client code.
