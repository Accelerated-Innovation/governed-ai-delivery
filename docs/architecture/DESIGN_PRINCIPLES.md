# Design Principles

This document defines the design principles that govern all code in this repository.

These principles are binding for all implementations. Agents must reference this document during planning and implementation.

---

## 1. SOLID Principles

### Single Responsibility
A module, class, or function has one reason to change. If a component handles multiple concerns, split it.

### Open/Closed
Components are open for extension and closed for modification. Add behavior by extending, not by editing existing logic.

### Liskov Substitution
Subtypes must be substitutable for their base types without altering correctness. Implementations of a port interface must be interchangeable.

### Interface Segregation
Clients should not depend on interfaces they do not use. Prefer narrow, focused port interfaces over wide general-purpose ones.

### Dependency Inversion
High-level modules depend on abstractions (ports), not on concrete implementations (adapters). Dependency direction flows inward toward the domain.

---

## 2. Relationship to the 7 Code Virtues

SOLID compliance is evaluated through the 7 Code Virtues — no separate SOLID score is applied. The mapping is:

| SOLID Principle | Primary Virtue(s) |
|---|---|
| Single Responsibility | **Clear** (functions do one thing), **Simple** (minimal branching per unit) |
| Open/Closed | **Easy** (clear extension points) |
| Liskov Substitution | **Working** (correct behavior through abstractions) |
| Interface Segregation | **Easy** (high cohesion, loose coupling), **Brief** (no unnecessary interface surface) |
| Dependency Inversion | **Easy** (loose coupling, dependency injection), **Unique** (no leakage of adapter logic into domain) |

A codebase scoring 4.0+ on all Virtues is expected to satisfy SOLID. If a Virtue score is low, inspect the corresponding SOLID principle first.

---

## 3. Additional Principles

### DRY — Don't Repeat Yourself
Duplicate logic must be extracted. The **Unique** virtue enforces this directly.

### YAGNI — You Aren't Gonna Need It
Do not implement functionality until it is required. The **Brief** virtue enforces this — no speculative abstractions.

### KISS — Keep It Simple
Prefer the simplest design that satisfies requirements. The **Simple** virtue enforces this — minimal variables, branching, and execution paths.

---

## 4. Enforcement

Compliance is evaluated through the 7 Code Virtues (see Section 2). A codebase meeting Virtue thresholds is expected to satisfy these principles.

Architecture Preflight Section 3 (Boundary Analysis) verifies Dependency Inversion compliance via `BOUNDARIES.md`.
