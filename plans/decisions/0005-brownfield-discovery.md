# ADR 0005: Bounded observations and explicit brownfield commitments

Status: accepted for I05 implementation, 2026-09-23. Refs #178, #142.

Existing repositories should adopt useful capabilities without replacing their
architecture documents or completing universal calibration. Inference must remain
separate from accepted policy, and repeat inspection must focus on changed evidence.

Add a read-only `govkit discover` command. `discovery_scan.py` owns bounded, local,
non-executing collection; `discovery.py` owns scoped proposals, baseline comparison,
I04-compatible maintenance facts and delegation to existing installer previews.
`cmd_discover.py` handles argument parsing and human/JSON views only.

Known filenames, dependency/import syntax and narrow architecture phrases yield
observations, never rules. Scopes derive from manifest boundaries or explicit
accepted contracts/transitions. Every proposed commitment remains pending; only a
validated explicit/existing accepted profile is given to the I02/I03 installers.
No new write path is introduced. Independent capability adoption therefore reuses
existing project documents without refactoring applications or installing a generic
architecture bundle. Installation readiness is separate from authorization and
from architecture/conformance evidence.

Versioned reports contain digest-bearing observations, coverage, pending/accepted
choices, changes and protected installation operations. A caller explicitly supplies
the last-reviewed report as a baseline; no clock/version event triggers mandatory
setup, and no new baseline is automatically accepted. Unchanged pending choices are
preserved without resurfacing every question. Incomplete or changed coverage cannot
prove deletion. Changed evidence prompts focused review, not a violation or policy
replacement. Accepted source labels and baselines are assertions, not authenticated
team decisions.

The bounded detector is intentionally not a semantic architecture engine. It does
not run code/tests, authenticate approvals, execute transitions, classify Git diffs,
resolve URLs, assess releases or judge source/resource freshness beyond supplied
local evidence. References with fragments are explicit unavailable inputs. Source
snapshots assume no concurrent filesystem mutation. I07 owns actual-diff and
transition enforcement; I09 owns integrated maintenance. These boundaries keep I05
useful without claiming those later controls exist.

The four shipped examples, failure cases, protected/idempotent adoption and a
runtime-only wheel smoke verify this contract. Existing legacy discovery/calibration
behavior and consumer CI/agent payloads remain unchanged.
