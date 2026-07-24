#!/usr/bin/env bash
# Example check: Python lint via ruff. This is a worked reference for a
# Python/uv project (scenter, specifically) -- it is NOT part of the
# checks harness and is not a "Python profile" the tool ships with. A
# project adopting this tool writes its own checks.d/ from scratch (or by
# copying/adapting files like this one), choosing whatever tools it
# already uses.
cmd_ruff_lint() { uv run ruff check --color never .; }

summarize_ruff_lint() {
  local last_line
  last_line="$(printf '%s' "$1" | tail -1)"
  if [ -z "$1" ]; then
    echo "0 violation(s) found by ruff"
  else
    echo "ruff: $last_line"
  fi
}

register_check "ruff-lint" summarize_ruff_lint cmd_ruff_lint true
