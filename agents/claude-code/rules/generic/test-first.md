# Test-First Development

These rules apply to all files in the project.

---

## Test-First Discipline

- Write failing tests before writing implementation code
- Each increment in `plan.md` lists tests before deliverables — follow that order
- Do not mark an increment as complete until all listed tests pass
- If you discover an untested edge case during implementation, write the test first, then fix the code

## Test Quality

- Tests must be fast — avoid unnecessary I/O, prefer mocks for external dependencies
- Tests must be isolated — no shared mutable state between tests, no order dependencies
- Tests must be repeatable — deterministic in all environments, no reliance on wall-clock time or network
- Tests must be self-verifying — explicit assertions, no manual log inspection
- Test names must describe the behavior being verified, not the method being called

## Prohibited Practices

- Do not write implementation code without a corresponding test
- Do not disable or skip tests to make a build pass
- Do not write tests that always pass regardless of implementation
- Do not use production data in tests — use fixtures or factories
