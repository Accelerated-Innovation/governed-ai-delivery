#!/usr/bin/env bash
# Example check: Python types via mypy. See 10-ruff-lint.sh for notes on
# what "example" means here.
cmd_mypy() { uv run mypy --no-color-output; }

summarize_mypy() {
  printf '%s' "$1" | tail -1
}

register_check "mypy" summarize_mypy cmd_mypy true
