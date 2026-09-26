# ADR 0019: Bounded isolated command worker primitive

Status: Proposed for review with I10d8's implementation. Merging that PR accepts
this primitive's design; it does not activate a protected caller or approve a
production daemon/image, consumer policy change or external settings.

## Context

The common conformance engine currently runs opted-in project commands as
subprocesses with its own environment. Defect red/green tests reuse that command
path; pinned pack checks have another executable path. Sharing one container
between those commands and a trusted engine would still expose engine authority.
The consumer activation proposal therefore requires an independent execution
boundary before controller and publisher activation.

## Decision

Implement a small, opt-in Python worker primitive before changing those callers.
It accepts validated immutable file bytes, arguments and deadline plus a
caller-selected local Docker executable/socket and digest-pinned Linux image.
Use an already present image; do not fetch dependencies or mount the inspected
checkout, trusted policy, engine, secrets or daemon socket into the worker.
Materialize only regular-file bytes in bounded tmpfs and replace the trusted
bootstrap with unprivileged project execution. Keep the engine outside.

Apply fixed network, privilege, filesystem, CPU, memory, process and output
restrictions. Match the attached exit with the daemon's stopped/non-OOM state;
withhold verdicts for transport/setup failures, ambiguous exits, timeout,
overflow or failed cleanup. Treat stdout as untrusted bytes. Bind image,
request and bootstrap digests in the result without claiming authentication.
Detailed contracts and limitations live in the [worker guide](../../docs/COMMAND_WORKER.md).

Docker is the first bounded adapter, not a generic backend/plugin framework.
The local daemon, host kernel/VM, executable and image remain trusted operator
dependencies. Digest references constrain identity; they do not prove source or
build provenance. No isolation guarantee is made against compromise of those
dependencies. A dedicated production execution host and independently reviewed
runtime custody remain deployment prerequisites.

## Increment boundary and compatibility

I10d8 delivers and tests the primitive only. Existing local commands, provider
templates, conformance evidence and accepted policy retain their current
semantics. A later integration increment must route project commands and defect
snapshots through the same caller-selected execution boundary, explicitly
withhold unsupported pack execution, preserve required checks and bind worker
provenance into canonical reports. It must not let inspected files, ambient
environment variables or uploaded success reports select trusted execution.

An in-process adapter interface or a changed report label alone would not
establish isolation. Real Docker negative controls accompany the primitive, but
they do not establish an authenticated controller/publisher or live enforcement.
The user must separately authorize the complete, concrete activation payload.

## Validation

Start with failing boundary tests, then exercise production orchestration against
a deterministic CLI dependency. Control time for deadline tests and keep input
state explicit. Use a real, explicitly selected local daemon for the isolation
pilot: host-file/credential/socket/network access denial, resource limits,
byte/mode transfer, nonzero exits, spoofed stdout, timeout, overflow and startup
failure. Repeat from a freshly installed wheel outside the source checkout.
Passing synthetic checks cannot replace missing application governance controls.
