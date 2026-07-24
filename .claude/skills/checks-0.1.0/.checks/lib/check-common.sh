#!/usr/bin/env bash
# Harness core for the checks tool. Sourced by ./check and ./check-llm.
#
# Portability contract: this file assumes only bash (tested against bash
# 3.2, the stock /bin/bash on macOS, as well as bash 4/5 on Linux) plus
# POSIX `tr` (used only to strip stray control bytes/ANSI color codes
# before JSON-encoding captured output). It must never assume any specific
# checking tool, language runtime, package manager, or utility (including
# jq) is installed on the host -- those belong to individual check
# definitions in checks.d/, which are owned by whatever project installs
# this tool, not by the harness. A clean Linux container or an unfamiliar
# Mac must be able to run this with nothing more than bash + tr and
# whatever checks.d/ declares for itself.

CHECKS_NAMES=()
CHECKS_SUMMARIZERS=()
CHECKS_COMMANDS=()
CHECKS_BLOCKING=()

# register_check <name> <summarizer-func> <command-func> [blocking:true|false]
#
# Called by each file in checks.d/ after it defines its own command and
# summarizer functions. <command-func> must be a function name (not a
# string to eval) that runs the check and returns its exit code; it may
# print any raw output. <summarizer-func> must be a function name that
# takes the raw output as $1 and prints a short, information-bearing
# summary -- including on success (a passing check should still say how
# much it verified, not just that it passed). blocking defaults to true;
# an advisory (blocking=false) check is reported but never fails the run.
register_check() {
  CHECKS_NAMES+=("$1")
  CHECKS_SUMMARIZERS+=("$2")
  CHECKS_COMMANDS+=("$3")
  CHECKS_BLOCKING+=("${4:-true}")
}

# load_checks <checks.d-directory>
#
# Sources every *.sh file in the given directory, in lexical order, so
# check definitions can be ordered by filename prefix (e.g. 10-, 20-, ...)
# when order matters (cheap/fast checks before slow ones).
load_checks() {
  local dir="$1" f
  for f in "$dir"/*.sh; do
    [ -e "$f" ] || continue
    # shellcheck source=/dev/null
    source "$f"
  done
}

# run_check_capture <command-func-name>
# Runs a registered check's command function, capturing combined
# stdout+stderr into CHECK_OUTPUT and its exit code into CHECK_EXIT.
run_check_capture() {
  CHECK_OUTPUT="$("$1" 2>&1)"
  CHECK_EXIT=$?
}

# json_escape <string>
# Minimal, dependency-free JSON string escaping (bash builtins only --
# no jq, no sed/awk). Handles the characters that actually occur in check
# output: backslashes, double quotes, tabs, carriage returns, newlines.
json_escape() {
  local s="$1"
  # Defense in depth, not the primary fix: each check.d/ definition should
  # ask its own tool for plain output at the source (--color=never,
  # --no-ansi, --progress-spinner off, etc. -- see checks.d.example/ for
  # worked cases) rather than relying on this stripping. This still
  # removes anything that slips through -- e.g. a tool with no such flag,
  # or one that mis-detects a non-tty pipe as a terminal -- since a single
  # stray control byte would otherwise break JSON encoding. Strips
  # everything below 0x20 except tab/CR/LF, which are escaped below
  # instead of stripped. tr is assumed present: unlike jq, it ships with
  # every POSIX system this tool targets.
  s="$(printf '%s' "$s" | tr -d '\000-\010\013\014\016-\037')"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\t'/\\t}"
  s="${s//$'\r'/\\r}"
  s="${s//$'\n'/\\n}"
  printf '%s' "$s"
}
