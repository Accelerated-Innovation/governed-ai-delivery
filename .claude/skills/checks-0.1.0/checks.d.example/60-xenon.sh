#!/usr/bin/env bash
# Example check: cyclomatic-complexity ratchet via xenon. Thresholds are
# this project's own baseline, not a harness default -- see scenter's
# GUIDELINES.md/README.md for the rationale. See 10-ruff-lint.sh for notes
# on what "example" means here.
cmd_xenon() {
  uv run xenon --max-absolute C --max-average A --max-modules B src
}

summarize_xenon() {
  if [ -z "$1" ]; then
    echo "complexity within thresholds (absolute<=C, average<=A, per-module<=B)"
  else
    printf '%s' "$1" | tail -1
  fi
}

register_check "xenon" summarize_xenon cmd_xenon true
