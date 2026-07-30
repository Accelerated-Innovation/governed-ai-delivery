---
applyTo: "**"
---
# API and Database Boundary

All business logic and persistence are behind backend APIs. Do not add
database drivers/clients, ORMs, SQL, migrations, schemas, connection strings,
or direct LLM provider SDKs. Next.js server code may only be a thin session,
token, protocol, or aggregation adapter.
