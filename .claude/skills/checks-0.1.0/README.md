# checks

A portable bash harness for running quality checks and reporting results
as human-readable text or as JSON for an LLM.

## Layout

```
check                  entry point (only file with real logic)
check-llm               symlink to check
onboard                 maintainer setup/sanity check for this repo
install <target>        installs check/check-llm/.checks/lib/SKILL.md into <target>
package                 builds dist/checks-<version>.tar.gz
SKILL.md                procedure for configuring .checks/checks.d/ in a target repo
VERSION                 current version
checks.d.example/       worked reference config (Python/uv), not installed
.checks/
  lib/check-common.sh   registry + JSON escaping
  checks.d/              this repo's own checks
```

A project that installs this tool ends up with `check`/`check-llm` at its
root and its own checks under `.checks/checks.d/`.

## Requirements

bash (3.2+) and POSIX `tr`. No other dependency is assumed at runtime.
Individual checks may depend on whatever tools the installing project
already uses (see `checks.d.example/`).

## Usage

- `./check` — run all checks, human-readable output, exit 0/1.
- `./check-llm` — run all checks, one JSON object on stdout:
  ```json
  {"passed": true, "checks": [
    {"name": "...", "passed": true, "blocking": true, "exit_code": 0,
     "summary": "...", "output": "..."}
  ]}
  ```
- `./check --llm` / `./check-llm --human` — override the format explicitly.
- `./onboard` — for maintainers of this repo: checks prerequisites, runs
  `./check` as a smoke test.
- `./install <target-dir>` — copies `check`, the `check-llm` symlink,
  `.checks/lib/`, and `SKILL.md` into `<target-dir>`. Creates
  `<target-dir>/.checks/checks.d/` if it doesn't already exist; never touches
  it if it does. Records provenance in `<target-dir>/.checks/INSTALLED_FROM`.
- `./package` — runs `./check`, then builds a self-contained
  `dist/checks-<version>.tar.gz` (including `install` itself, so a recipient
  can run `install <target-dir>` from the extracted tarball without cloning
  this repo).

## Defining a check

Each file in `checks.d/` defines a command function, a summarizer
function, and registers itself:

```sh
#!/usr/bin/env bash
cmd_my_check() { my-tool --some-flag; }
summarize_my_check() { echo "short summary of $1, even on success"; }
register_check "my-check" summarize_my_check cmd_my_check true
#                                             ^^^^ blocking (default true)
```

`register_check <name> <summarizer-func> <command-func> [blocking]`. A
`blocking=false` check is run and reported but never fails the overall
run. Files load in lexical order (`10-`, `20-`, ...).

`CHECKS_DIR` overrides where `checks.d/` is loaded from.

Every `cmd_*` should ask its tool to disable color, spinners, and progress
bars via that tool's own flag (`--color never`, `--no-ansi`,
`--no-color-output`, `--progress-spinner off`, etc.). If a tool has no
such flag, write a small wrapper script under `.checks/wrappers/<tool>`
that execs the tool and conditions its output, and have `cmd_*` call the
wrapper instead.

## Skill

`SKILL.md` is a language-agnostic procedure for populating a target repo's
`.checks/checks.d/`: it inspects the repo, proposes a check configuration,
writes the check files, disables ornamentation at the source (or via a
`.checks/wrappers/` wrapper), and verifies with fault injection. It is
installed into every target by `./install`, so a target repo can be
re-onboarded or extended later without this source repo.

## Status

Not yet implemented: quick/full execution groups and a versioned release
workflow beyond the static `VERSION` file.
