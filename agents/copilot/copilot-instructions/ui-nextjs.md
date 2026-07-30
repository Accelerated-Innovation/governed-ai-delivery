---
applyTo: "**"
---
# GitHub Copilot Instructions — Foundations (Level 3) — Next.js UI

This is a standalone governed Next.js UI project. Repository contracts are
authoritative.

> **Feature artifacts are not part of L3.** Adopt spec-driven delivery with
> `govkit apply --level 4 --type ui-nextjs --target <path>`.

## Architecture

Use server-first App Router composition with feature-local `application/`,
`api/`, `components/`, and `types/` folders under `src/features/`. Keep shared
code in `src/shared/`.

Before code, read `docs/ui/architecture/nextjs/`,
`docs/ui/architecture/ACCESSIBILITY_STANDARDS.md`, and
`docs/ui/design/BRAND.md`.

Server Components are the default. Add `"use client"` only for browser APIs
or interaction and keep that boundary small.

## Hard API Boundary

All business capability comes through a backend-owned API. Never generate SQL,
database clients/drivers, ORMs, migrations, schemas, or connection strings.
Never put domain rules in Route Handlers or Server Actions. A thin BFF may
only handle session, token protection, protocol adaptation, or limited
aggregation. An ADR cannot waive this boundary.

If an endpoint is missing, report the contract gap instead of creating direct
data access.

## Layer and Design Rules

`app/` composes, `application/` orchestrates UI use cases, `api/` performs
typed HTTP calls, and `components/` renders. Shared code cannot import feature
internals; features cannot import another feature's internals.

Use approved semantic Tailwind v4 tokens. Screens and mockups are advisory
unless an approved feature design promotes a named property. Accessibility and
accepted behavior take precedence.

## Testing

Require strict typecheck, lint, Vitest, Playwright for Server Components and
user-visible flows, and WCAG 2.1 AA with zero critical or serious axe
violations.

## ADR Required For

New shared libraries, material server/client boundary changes, new BFF
responsibilities, cross-feature coupling, or material auth/API-client changes.
Database access is not an ADR option.

## Upgrading to Spec-Driven Add-On (Level 4)

Run `govkit apply --level 4 --type ui-nextjs --target <path>`. Level 4 adds
six feature artifacts, planning skills, design review, and governance gates.
