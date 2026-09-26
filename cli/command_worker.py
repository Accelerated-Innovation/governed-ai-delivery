# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Opt-in Docker snapshot worker; not yet a conformance execution adapter.

The caller owns the Docker executable, local daemon and reviewed image pin.
Only explicit regular-file bytes cross into the worker. No host checkout,
credentials, policy, engine installation or Docker socket is mounted there.
"""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .observation_limits import MAX_FILE_BYTES, MAX_FILES, MAX_TOTAL_BYTES
from .pack_loading import safe_relative
from .schema_validation import canonical_json, content_digest

MAX_OUTPUT_BYTES = 64 * 1024
MAX_TIMEOUT_SECONDS = 600
CONTROL_TIMEOUT_SECONDS = 10
MAX_ARGUMENT_BYTES = 64 * 1024
MAX_ARGUMENTS = 256
MAX_PATH_BYTES = 4096

# This bootstrap is trusted runtime code, passed as an argument, never imported
# from the supplied snapshot. exec replaces it before any project code runs.
_BOOTSTRAP = """import base64,json,os,sys
from pathlib import Path
try:
    request=json.load(sys.stdin)
    for entry in request['files']:
        path=Path('/work')/entry['path']
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(base64.b64decode(entry['content'],validate=True))
        path.chmod(0o755 if entry['executable'] else 0o644)
    argv=[sys.executable if arg=='{python}' else arg for arg in request['argv']]
    os.chdir('/work')
    fd=os.open('/dev/null',os.O_RDONLY)
    os.dup2(fd,0)
    os.close(fd)
    env={'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':'/tmp','TMPDIR':'/tmp',
         'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1','LC_ALL':'C.UTF-8'}
    os.execvpe(argv[0],argv,env)
except Exception:
    sys.exit(125)
"""


@dataclass(frozen=True, slots=True)
class SnapshotFile:
    path: str
    content: bytes
    executable: bool = False

    def __post_init__(self):
        safe_relative(self.path)
        try:
            encoded = self.path.encode("utf-8")
        except UnicodeError as exc:
            raise ValueError("Snapshot path must be UTF-8") from exc
        if (
            len(encoded) > MAX_PATH_BYTES
            or "\x00" in self.path
            or any(part.casefold() == ".git" for part in self.path.split("/"))
            or type(self.content) is not bytes
            or len(self.content) > MAX_FILE_BYTES
            or type(self.executable) is not bool
        ):
            raise ValueError("Invalid snapshot file or file bound exceeded")


@dataclass(frozen=True, slots=True)
class CommandRequest:
    argv: tuple[str, ...]
    files: tuple[SnapshotFile, ...]
    timeout_seconds: int

    def __post_init__(self):
        if (
            type(self.argv) is not tuple
            or not self.argv
            or not self.argv[0]
            or len(self.argv) > MAX_ARGUMENTS
            or any(not isinstance(a, str) or "\x00" in a for a in self.argv)
            or type(self.files) is not tuple
            or len(self.files) > MAX_FILES
            or any(type(f) is not SnapshotFile for f in self.files)
            or type(self.timeout_seconds) is not int
            or not 1 <= self.timeout_seconds <= MAX_TIMEOUT_SECONDS
        ):
            raise ValueError("Invalid worker request")
        try:
            argument_bytes = sum(len(a.encode("utf-8")) for a in self.argv)
        except UnicodeError as exc:
            raise ValueError("Command arguments must be UTF-8") from exc
        if (
            argument_bytes > MAX_ARGUMENT_BYTES
            or sum(len(f.content) for f in self.files) > MAX_TOTAL_BYTES
        ):
            raise ValueError("Worker request exceeds input limits")
        paths = {f.path for f in self.files}
        if len(paths) != len(self.files):
            raise ValueError("Duplicate snapshot destination")
        for path in paths:
            parts = path.split("/")
            if any("/".join(parts[:i]) in paths for i in range(1, len(parts))):
                raise ValueError("Conflicting snapshot destinations")

    @property
    def payload(self) -> bytes:
        return canonical_json(
            {
                "argv": self.argv,
                "timeout_seconds": self.timeout_seconds,
                "files": [
                    {
                        "path": f.path,
                        "content": base64.b64encode(f.content).decode("ascii"),
                        "executable": f.executable,
                    }
                    for f in sorted(self.files, key=lambda f: f.path)
                ],
            }
        ).encode()

    @property
    def digest(self) -> str:
        return content_digest(self.payload)


@dataclass(frozen=True, slots=True)
class DockerRuntime:
    executable: Path
    socket: Path
    image: str

    def __post_init__(self):
        if (
            not isinstance(self.executable, Path)
            or not self.executable.is_absolute()
            or not isinstance(self.socket, Path)
            or not self.socket.is_absolute()
            or not isinstance(self.image, str)
            or not re.fullmatch(r"[a-z0-9][a-z0-9./_:-]*@sha256:[a-f0-9]{64}", self.image)
        ):
            raise ValueError("Worker needs absolute local Docker paths and a digest-pinned image")


class WorkerState(str, Enum):
    COMPLETED = "completed"
    UNAVAILABLE = "unavailable"
    TIMED_OUT = "timed-out"
    OUTPUT_LIMIT = "output-limit"
    CLEANUP_FAILED = "cleanup-failed"


@dataclass(frozen=True, slots=True)
class WorkerResult:
    state: WorkerState
    exit_code: int | None
    stdout: bytes
    stderr: bytes
    image: str
    request_digest: str
    bootstrap_digest: str


@dataclass(frozen=True, slots=True)
class _ProcessResult:
    state: WorkerState
    returncode: int | None = None
    stdout: bytes = b""
    stderr: bytes = b""


def _run(argv, env, *, timeout, data=b"") -> _ProcessResult:
    """Drain both pipes with a fixed memory ceiling and kill on overflow/deadline."""
    try:
        process = subprocess.Popen(
            argv, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    except OSError:
        return _ProcessResult(WorkerState.UNAVAILABLE)
    output = [bytearray(), bytearray()]
    overflow, io_error = threading.Event(), threading.Event()

    def drain(stream, destination):
        try:
            while chunk := stream.read(4096):
                remaining = MAX_OUTPUT_BYTES - len(destination)
                destination.extend(chunk[:remaining])
                if len(chunk) > remaining:
                    overflow.set()
        except OSError:
            io_error.set()

    def send():
        try:
            process.stdin.write(data)
            process.stdin.close()
        except BrokenPipeError:
            pass
        except OSError:
            io_error.set()

    threads = [
        threading.Thread(target=drain, args=(stream, destination), daemon=True)
        for stream, destination in zip((process.stdout, process.stderr), output, strict=True)
    ]
    threads.append(threading.Thread(target=send, daemon=True))
    for thread in threads:
        thread.start()
    deadline = time.monotonic() + timeout
    state = WorkerState.COMPLETED
    try:
        while process.poll() is None or any(t.is_alive() for t in threads):
            if overflow.is_set():
                state = WorkerState.OUTPUT_LIMIT
                break
            if io_error.is_set():
                state = WorkerState.UNAVAILABLE
                break
            if time.monotonic() >= deadline:
                state = WorkerState.TIMED_OUT
                break
            overflow.wait(0.01)
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
        for thread in threads:
            thread.join(timeout=1)
        for stream in (process.stdin, process.stdout, process.stderr):
            stream.close()
    if overflow.is_set():
        state = WorkerState.OUTPUT_LIMIT
    elif io_error.is_set():
        state = WorkerState.UNAVAILABLE
    return _ProcessResult(state, process.returncode, bytes(output[0]), bytes(output[1]))


def _successful(result):
    return result.state is WorkerState.COMPLETED and result.returncode == 0


def execute(runtime: DockerRuntime, request: CommandRequest) -> WorkerResult:
    """Run one snapshot, remove only its container, never fall back to host execution.

    A completed result measures a command, not conformance or provider authority.
    Failures discard transport output. Cleanup failure invalidates the result.
    """
    if type(runtime) is not DockerRuntime or type(request) is not CommandRequest:
        raise ValueError("Worker requires validated runtime and request values")
    payload = request.payload
    provenance = (runtime.image, content_digest(payload), content_digest(_BOOTSTRAP.encode()))
    state, measured, container = WorkerState.UNAVAILABLE, None, None
    with tempfile.TemporaryDirectory(prefix="govkit-worker-") as directory:
        config = Path(directory)
        cidfile = config / "container-id"
        prefix = [
            str(runtime.executable),
            "--host",
            "unix://" + str(runtime.socket),
            "--config",
            directory,
        ]
        env = {"PATH": os.defpath, "HOME": directory}

        def control(*args):
            return _run([*prefix, *args], env, timeout=CONTROL_TIMEOUT_SECONDS)

        try:
            created = control(
                "create",
                "--cidfile",
                str(cidfile),
                "--pull",
                "never",
                "--interactive",
                "--network",
                "none",
                "--read-only",
                "--user",
                "65534:65534",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--memory",
                "256m",
                "--memory-swap",
                "256m",
                "--cpus",
                "1",
                "--pids-limit",
                "64",
                "--ipc",
                "none",
                "--log-driver",
                "none",
                "--no-healthcheck",
                "--tmpfs",
                "/work:rw,nosuid,nodev,size=64m,mode=0700,uid=65534,gid=65534",
                "--tmpfs",
                "/tmp:rw,nosuid,nodev,noexec,size=16m,mode=0700,uid=65534,gid=65534",
                "--workdir",
                "/work",
                "--entrypoint",
                "/usr/local/bin/python",
                runtime.image,
                "-I",
                "-c",
                _BOOTSTRAP,
            )
            # Docker writes this on create, including when later CLI work fails.
            # Never infer a cleanup target from project-controlled stdout.
            if cidfile.exists():
                with cidfile.open("rb") as stream:
                    identifier = stream.read(65).decode("ascii")
                if re.fullmatch(r"[a-f0-9]{64}", identifier):
                    container = identifier
            if _successful(created) and container:
                mounts = control("inspect", "--format", "{{json .Mounts}}", container)
                # Reject automatic image VOLUMEs; no persistent/host mounts are allowed.
                if _successful(mounts) and json.loads(mounts.stdout) == []:
                    measured = _run(
                        [*prefix, "start", "--attach", "--interactive", container],
                        env,
                        timeout=request.timeout_seconds,
                        data=payload,
                    )
                    state = measured.state
                    if state is WorkerState.COMPLETED:
                        inspected = control("inspect", "--format", "{{json .State}}", container)
                        status = json.loads(inspected.stdout) if _successful(inspected) else {}
                        if not (
                            isinstance(status, dict)
                            and status.get("Running") is False
                            and status.get("Dead") is False
                            and status.get("OOMKilled") is False
                            and status.get("Error") == ""
                            and type(status.get("ExitCode")) is int
                            and status["ExitCode"] == measured.returncode
                            and 0 <= measured.returncode < 125
                        ):
                            state = WorkerState.UNAVAILABLE
        except (OSError, ValueError, RecursionError):
            state = WorkerState.UNAVAILABLE
        finally:
            if container and not _successful(control("rm", "--force", "--volumes", container)):
                state = WorkerState.CLEANUP_FAILED
    if state is not WorkerState.COMPLETED or measured is None:
        return WorkerResult(state, None, b"", b"", *provenance)
    return WorkerResult(state, measured.returncode, measured.stdout, measured.stderr, *provenance)
