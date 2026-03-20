---
applyTo: "**/*.component.ts,**/*.component.html"
---

Follow the component conventions defined in `docs/ui/architecture/angular/COMPONENT_CONVENTIONS.md`.

All Angular components must:

- Be standalone — no NgModule declarations
- Use `ChangeDetectionStrategy.OnPush` — always, no exceptions
- Not inject `HttpClient` or API services directly
- Contain no business logic or data transformation in class or template
- Not import from another feature's internals
- Use `@if`, `@for`, `@switch` control flow (Angular 17+) — not `*ngIf`, `*ngFor`
- Always provide `track` by a unique identifier in `@for` — never by `$index` for mutable lists
- Use signal-based `input()` and `output()` for new code

All components are views. They render. They do not fetch, transform, or decide.
