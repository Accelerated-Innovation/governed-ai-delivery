#!/usr/bin/env bash
# Example check: Python formatting via ruff. See 10-ruff-lint.sh for notes
# on what "example" means here.
cmd_ruff_format() { uv run ruff format --color never --check .; }

summarize_ruff_format() {
  printf '%s' "$1" | tail -1
}

register_check "ruff-format-check" summarize_ruff_format cmd_ruff_format true
