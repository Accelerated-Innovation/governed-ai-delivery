# Brownfield discovery and focused setup

`govkit discover` inspects an existing repository without installing, rewriting,
executing tests, migrating legacy markers, fetching metadata or accepting policy.
It works before GovKit is installed and alongside declarative or legacy installs.

```sh
govkit discover --target /path/to/project
govkit discover --target /path/to/project --capability llm-evaluation --json
```

The report separates observations (source, SHA-256, component, confidence and
syntactic indicators), pending decisions, and an explicitly accepted profile.
Existing accepted policy takes precedence. Detected architecture words, imports,
test files or CI definitions do not prove architectural correctness or execution.
Python/MCP indicators never select a FastAPI stack. Unknown architecture stays a
scoped question; it does not block an independent evaluation capability.

## Reuse the project's sources

Pass `--reference design/system.md` to prioritize a source outside conventional
locations; repeat it for additional files. Accepted profile references are
included automatically. Sources must be local repository-relative files, without
symlinks, parent traversal or URL resolution. Unsupported/missing/unreadable
references remain explicit. Reference fragments are not resolved; use a file
reference and record the section in that document or the team decision.

Architecture/ADR/guidance, manifests, bounded representative code, tests and CI
are inspected. Manifest directories define observed component boundaries.
A small set of known dependency/import names and architecture phrases provides
indicators, with sources. Different component conventions prompt a scoped review;
they do not require one architecture across a monorepo. These heuristics do not
understand arbitrary prose or prove two contracts are semantically compatible.

The default bounds are 2,048 directory entries, 128 files, 64 KiB per file, 1 MiB
of file content and six directory levels below the root. Reads use at most one
extra sentinel byte per file to detect overflow. `--max-entries`, `--max-files`,
`--max-bytes`, `--max-total-bytes` and `--max-depth` override these limits. Explicit
references are prioritized within the file/byte bounds. Git metadata, virtual
environments, build/vendor trees, `.govkit` and native skill directories are
excluded from automatic scanning. The accepted profile is read separately by the
existing profile loader; installer previews inspect their own selected resources.

`coverage.complete` means the configured sample was collected/interpreted without
reported limits/errors. It does not mean exhaustive repository understanding.
Over-budget directory samples depend on filesystem enumeration; they are always
reported incomplete. Filesystem edits during inspection are outside the snapshot
guarantee. Inspection is intended for a stable local working tree.

## Review a minimal installation

Without an accepted profile the report includes a `proposed_profile` with
`authority: proposed`. This is deliberately rejected by `govkit profile apply`.
Review only the decisions needed for the selected work, then author an accepted
[profile](DECLARATIVE_PROFILES.md) referencing the team's existing decision and
architecture files. There is no command that silently promotes observations to
accepted policy. The profile authority label is a project assertion, not an
authenticated approval.

```sh
govkit discover --target /path/to/project --profile /path/to/accepted-profile.yaml
govkit profile preview --target /path/to/project --profile /path/to/accepted-profile.yaml
govkit profile apply --target /path/to/project --profile /path/to/accepted-profile.yaml
govkit pack preview --target /path/to/project
govkit pack apply --target /path/to/project
```

Discovery delegates the operation preview to the existing profile/pack domain
modules. Metadata plus only selected pinned guidance/skills/controls are listed;
source documents are referenced, not copied into a generic architecture layout.
`install_ready` describes installer prerequisites and edit protection, not
conformance or authorization. Required context/provider gaps identify dependent
work; unrelated architecture questions remain optional. Changed observations do
not invalidate or revise accepted policy automatically. Protected customizations
block writes. Invalid installation metadata leaves discovery available with a
focused diagnostic; profile/pack preview provides the detailed installation error.
Apply commands recompute previews, enforce ownership/staleness, and are idempotent.
A legacy single-file `.govkit` marker requires separate migration before declarative
installation; discovery never migrates it.

Profile transitions can independently retain, improve or migrate components.
Their source, current/target contracts, new/new-and-changed/all applicability and
existing exception scopes stay intact. The monorepo example's target references
state verification and exit criteria. Discovery does not classify actual changes
as compliant/violating or execute those exit checks; I07 supplies that enforcement.

## Repeat only the relevant review

After explicitly reviewing a report, save it as the observation baseline. Supply
it on the next run; discovery never saves/replaces a baseline itself.

```sh
govkit discover --target /path/to/project --json > /tmp/project-reviewed.json
# Later, after repository changes:
govkit discover --target /path/to/project --baseline /tmp/project-reviewed.json
```

Use the same repository identity, accepted profile and relevant reference flags.
Unchanged evidence produces no new review ceremony; pending decisions remain in
`decisions` and are not silently accepted. Changed references reopen only their
associated commitments. Dependency/framework indicators, component moves,
model/tool imports, architecture sources, tests and CI produce scoped fit-review
facts even when the installed CLI version is current. Model indicators can
recommend `llm-evaluation`, but cannot select it. Incomplete scans or changed
coverage never establish that an unseen file was removed.

JSON uses [the versioned discovery schema](../governance/schemas/discovery.schema.json).
The loader validates shape and profile/digest consistency; it does not authenticate
baseline authors or replay installer authorization. Neither reports nor baselines
are input to an installer. The domain's `maintenance_outcome()` exposes I04-compatible
maintenance findings/evidence for later integrated assessment. These observations
return warning/unknown/not-applicable, never a conformance pass or policy failure.
`govkit discover` exits 0 when it produces a report (including pending/incomplete
findings), 1 on invalid input, and 2 on argument errors. It is not a CI gate.

The four [bundled examples](../governance/examples/discovery/) represent a documented
service, sparse repository, unfamiliar Python MCP server and monorepo. Each JSON
fixture contains repository files and, where explicitly accepted, a profile.
Tests materialize them in isolated directories; the wheel smoke exercises real
CLI adoption, source preservation and repeat discovery. No source text is included
in observation records or transmitted; paths, digests, indicators and explicitly
supplied profile references remain local. Hosted reporting/privacy aggregation
and release/resource maintenance are later increments.
