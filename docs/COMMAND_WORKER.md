# Isolated command worker

`cli.command_worker` is an opt-in Python primitive for running one command in a
disposable Linux Docker container. It accepts a digest-pinned runtime, explicit
file bytes and an argument vector. It does not read a project directory, select
policy or return a GovKit conformance verdict.

**Current integration status:** conformance commands, defect red/green execution
and pack checks still use their existing trusted, unsandboxed paths. No CLI,
environment variable, profile field or generated workflow selects this worker.
Routing those paths through a trusted caller-selected boundary, preserving
mandatory checks and binding canonical evidence, is the next increment. See
[ADR 0019](https://github.com/Accelerated-Innovation/governed-ai-delivery/blob/ec22f910a52c044553e2dd742195b63a01fbb8f7/plans/decisions/0019-isolated-command-worker.md).

## Inputs and runtime authority

Construct `DockerRuntime` with an absolute reviewed Docker executable, an
absolute local Unix daemon socket and an image reference ending in
`@sha256:<64 lowercase hex characters>`. The daemon must run Linux containers;
the reviewed image must provide `/usr/local/bin/python`. Images must already
exist locally: the worker never pulls, builds, installs dependencies or falls
back to host execution. Image identity alone does not establish trustworthy
contents, publisher identity, build provenance or a safe daemon.

The caller supplies immutable `SnapshotFile` values and a `CommandRequest`.
Only regular-file bytes and a boolean executable bit are supported. Paths must
be relative, without traversal, duplicate/file-directory collisions or `.git`
components. A file cannot be a link, device or host mount. File count and byte
ceilings reuse the observer's limits: 2,048 files, 8 MiB per file and 16 MiB total.
These are transport ceilings, not authority to enlarge an accepted observation
budget or declare an incomplete snapshot complete. Arguments are bounded to 256
entries and 64 KiB of UTF-8; an empty argument after the executable is preserved.
The timeout is an integer from 1 through 600 seconds.

`{python}` as a complete argument resolves to the worker's Python, never the
engine's interpreter. No shell expands the argument vector. An explicitly
requested shell is project code inside the same container boundary.

```python
from pathlib import Path
from cli.command_worker import CommandRequest, DockerRuntime, SnapshotFile, execute

# These values come from the trusted operator, not the inspected repository.
runtime = DockerRuntime(docker_executable, daemon_socket, approved_image_digest)
request = CommandRequest(
    ("{python}", "test.py"),
    (SnapshotFile("test.py", b"assert 1 + 1 == 2\n"),),
    timeout_seconds=10,
)
result = execute(runtime, request)
```

No environment or host-path input is available to the project command. The
caller must also avoid deliberately including secrets in the supplied file
bytes or approved image. This primitive does not discover or classify secrets.

## Execution and failure behavior

The worker creates a fresh container with no network, a read-only root,
unprivileged UID/GID 65534, all capabilities dropped, no new privileges, no
healthcheck and no logging driver. It requests one CPU, 256 MiB memory without
additional swap and 64 processes. Separate bounded tmpfs directories provide
64 MiB workspace and 16 MiB scratch storage. It supplies no host bind mounts,
provider credentials, policy checkout, engine files or Docker socket. Images
that implicitly create persistent volumes are rejected before starting code.
Docker documents these [execution controls](https://docs.docker.com/reference/cli/docker/container/create/)
and the [daemon and shared-kernel trust boundary](https://docs.docker.com/engine/security/).

The host Docker client receives a temporary empty configuration and a minimal
environment, with the local endpoint passed explicitly. Ambient Docker contexts,
proxy configuration and provider environment variables cannot select execution
or cross into the worker. The trusted bootstrap materializes the supplied bytes,
replaces stdin with `/dev/null`, and replaces itself with the requested command
using a fixed environment. No trusted verdict process remains alongside it.

Both output pipes are continuously drained with a 64 KiB ceiling each. A deadline
or excess output terminates the client and forces removal of its container.
Each create, inspect and cleanup operation has its own ten-second control bound;
these overheads are additional to the project-command deadline. The worker
cleans up only the container ID written by its own Docker create operation,
including when creation fails after writing that ID. If the daemon becomes
unreachable or creation is interrupted before returning an ID, operator
reconciliation can still be needed; this is not a durable job/recovery service.
Failure to start a transport helper thread also reaps the client and attempts
removal of its known container; continued exhaustion during removal produces
`cleanup-failed` rather than a command verdict.

| Result state | Meaning |
| --- | --- |
| `completed` | Attached command exit agrees with stopped, non-OOM daemon state; exit 0 through 124 and bounded output are retained. A nonzero exit is a measured command failure. |
| `unavailable` | Startup, input setup, transport or daemon state is unavailable/malformed/contradictory, or the exit is ambiguous. No command verdict or raw output is returned. |
| `timed-out` / `output-limit` | Execution exceeded a fixed boundary. No command verdict or raw output is returned. |
| `cleanup-failed` | Removal of the known owned container failed. It invalidates any otherwise completed measurement. |

Docker reserves exits 125–127 for startup failures; exits 128 and above can
represent signals. This primitive conservatively withholds verdicts for all
those values. An asserted JSON success on stdout cannot override the measured
exit. Raw output is project-controlled, not structured authority for a publisher.

Results bind the image reference, canonical request digest (including argv,
timeout, file bytes and executable bits) and trusted bootstrap digest. They are
in-process observations, not authenticated remote evidence or a complete runtime
build lock. No serialized success artifact or hash authorizes publication.

## Validation and remaining integration

Tests exercise production orchestration through a controlled external Docker CLI
and validate malformed inputs, unavailable daemon results, limits and cleanup.
An explicit real-Docker pilot uses only synthetic files and an already present
image pin. It checks filesystem/environment/network separation, effective
resource limits, positive/negative exits, spoofed stdout, timeout, overflow and
startup failure. It does not run automatically in the default suite or infer
availability of Docker from a developer machine.

Obtain [the pilot script](https://github.com/Accelerated-Innovation/governed-ai-delivery/blob/ec22f910a52c044553e2dd742195b63a01fbb8f7/scripts/pilot_command_worker.py)
from the repository and run it with the fresh wheel's interpreter, Python
isolation and explicit runtime values. The script and ADR are repository
resources; they are not included in the wheel:

```text
/absolute/runtime/bin/python -I /absolute/source/scripts/pilot_command_worker.py \
  --docker /absolute/docker --socket /absolute/local-daemon.sock \
  --image python@sha256:<reviewed-local-image-digest>
```

It creates temporary containers and emits measurements only after every positive
and negative control passes. The image must use Linux cgroup v2 for the resource
limit probes. These synthetic files do not need a project checkout or credentials.

Before protected use, integrate complete accepted snapshots and all executable
provider paths, preserve red/green baseline semantics, withhold unsupported pack
execution, and bind worker/runtime provenance into canonical evidence. Review
daemon/runtime custody, reproducible image builds and dependency inputs. Complete
the independent controller, approved intent store, authenticated publisher and
live bypass trials before separately approving final external settings.
