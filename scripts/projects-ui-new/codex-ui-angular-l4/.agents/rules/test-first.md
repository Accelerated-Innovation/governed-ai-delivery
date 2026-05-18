# Test-First Development

These rules apply to all files in the project.

See: `docs/backend/architecture/TESTING.md` for complete testing standards.

---

## Discipline (Red → Green → Refactor)

1. Write the test first (Red)
2. Confirm the test fails
3. Implement minimal code to pass the test (Green)
4. Refactor while tests remain passing

**Key principle:** Tests define the specification. Code conforms to tests, not vice versa.

Each increment in `plan.md` lists tests before implementation — follow that order. Do not mark an increment complete until all listed tests pass.

---

## If a Test Fails

**Fix the implementation.** Do not rewrite the test.

Tests may ONLY be changed when:
- The specification actually changed
- The Gherkin scenario was incorrect
- The original test was fundamentally flawed

See TESTING.md section 5 for anti-patterns to avoid.

---

## Test Quality Requirements

From TESTING.md, all unit tests must satisfy **FIRST**:
- **Fast** — no real I/O, external services, or long sleeps
- **Isolated** — no shared state, no order dependencies
- **Repeatable** — deterministic in any environment
- **Self-Verifying** — explicit assertions, no manual inspection
- **Timely** — write tests before or alongside implementation

Test names must describe behavior being verified, not method names.
