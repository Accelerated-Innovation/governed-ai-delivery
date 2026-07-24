#!/usr/bin/env bash
# Example check: dependency hygiene (unused/missing/misplaced) via deptry.
# See 10-ruff-lint.sh for notes on what "example" means here.
cmd_deptry() { uv run deptry --no-ansi src; }

summarize_deptry() {
  printf '%s' "$1" | tail -1
}

register_check "deptry" summarize_deptry cmd_deptry true
