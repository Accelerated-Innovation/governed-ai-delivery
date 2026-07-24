#!/usr/bin/env bash
# Example check: dependency-vulnerability scan via pip-audit. See
# 10-ruff-lint.sh for notes on what "example" means here.
#
# --progress-spinner off is passed explicitly (not left to pip-audit's own
# isatty auto-detection) so captured output is always clean, regardless of
# how this is invoked.
cmd_pip_audit() {
  local reqs
  reqs="$(mktemp)"
  uv export --no-emit-project --no-hashes -q -o "$reqs"
  uv run pip-audit --strict --progress-spinner off -r "$reqs"
  local rc=$?
  rm -f "$reqs"
  return "$rc"
}

summarize_pip_audit() {
  echo "$1" | tail -1
}

register_check "pip-audit" summarize_pip_audit cmd_pip_audit true
