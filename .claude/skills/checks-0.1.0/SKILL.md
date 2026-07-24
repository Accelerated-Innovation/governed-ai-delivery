# Checks Configuration Skill

## Purpose

Given an arbitrary project, inspect it and produce a `.checks/checks.d/`
configuration so the project can run `./check` / `./check-llm`. This
skill does not assume any language, package manager, or toolchain, and it
does not install a pre-built "profile" — every check is derived from
evidence found in the target repo.

## Prerequisites

`check`, the `check-llm` symlink, and `.checks/lib/check-common.sh` must
already exist in the target repo. If they don't, install them first (from
the `checks` repo: `./install <target>`).

## Procedure

1. **Inspect the repository**: languages and versions in use; package/
   build/manifest files (`pyproject.toml`, `package.json`, `go.mod`,
   `Cargo.toml`, `Gemfile`, `pom.xml`, etc.); existing CI configuration
   (`.github/workflows/`, `.gitlab-ci.yml`, etc.) for checks already wired
   in; existing linters, formatters, type checkers, test runners,
   dependency-vulnerability scanners, and complexity/dead-code analyzers
   already available (as dev dependencies or referenced in scripts);
   generated, vendored, fixture, and migration code that should be
   excluded; framework entry points and dynamically referenced symbols a
   naive analyzer might flag as unused or dead.

2. **Identify**: checks already in use (wire these up first); checks
   available (already a dependency, or trivially installable) but not run
   anywhere yet; important evidence or enforcement gaps (no type checking,
   no dependency-vulnerability scan, no complexity ratchet, no dead-code
   check, etc.); likely false-positive sources (dynamic dispatch,
   generated code, framework magic) so exclusions can be scoped correctly
   from the start; each tool's native JSON/SARIF/XML/exit-code interface,
   since a summarizer needs a real count, not just pass/fail.

3. **Propose a configuration** to the developer before writing anything:
   exact deterministic commands; blocking vs. advisory for each (advisory
   for a tool that may not be installed on every host, or whose failure is
   a judgment call rather than a hard rule); a ratchet strategy for any
   check with a continuous severity score (complexity, coverage,
   duplication) — baseline today's measured value as the threshold, don't
   invent an aspirational number; exclusions and exceptions with a stated
   rationale; the tool dependencies this configuration requires and how
   they get installed.

4. **On confirmation, write one file per check** under
   `.checks/checks.d/`, numbered by prefix (`10-`, `20-`, ...) in run
   order (fast/cheap before slow), following the harness's contract:

   ```sh
   #!/usr/bin/env bash
   cmd_<name>() { <tool invocation, color/spinners/progress disabled> ; }
   summarize_<name>() { <parse $1 into a short summary, even on success> ; }
   register_check "<name>" summarize_<name> cmd_<name> <blocking:true|false>
   ```

5. **Disable ornamentation at the source**: pass the tool's own flag for
   plain output (`--color never`, `--no-ansi`, `--no-color-output`,
   `--progress-spinner off`, etc.). If no such flag exists, write
   `.checks/wrappers/<tool-name>` — a small script that execs the tool and
   conditions its output — and have `cmd_<name>` call the wrapper instead
   of the raw tool.

6. **Verify**: run `./check` and `./check-llm` on a clean tree; confirm
   both pass and produce an informative summary for every check (not
   `"[]"` or an empty string). Inject a deliberate fault for each new
   check (a lint violation, an over-complex function, an undeclared
   dependency, etc.), confirm it's caught with the correct blocking/
   advisory behavior, then revert the fault.

## Constraints

- Derive everything from evidence in the target repo; never assume a
  specific language, package manager, or toolchain.
- Prefer wiring up checks already present in the project's own CI/scripts
  before adding new ones.
- Ratchet thresholds are today's measured baseline, not an aspirational
  value.
- Present the proposed configuration (step 3) for confirmation before
  writing files.
- The harness has no quick/full execution grouping yet — every check runs
  every time `./check`/`./check-llm` is invoked.
