#!/usr/bin/env python3
"""Explicit, synthetic Docker pilot; run with an independently installed wheel.

This creates and removes bounded temporary containers using an existing image.
It never installs an image, mounts host files or enables protected governance.
"""

import argparse
import json
import os
import tempfile
from pathlib import Path

from cli import command_worker
from cli.command_worker import CommandRequest, DockerRuntime, SnapshotFile, WorkerState, execute


def pilot(runtime):
    records = {}
    with tempfile.TemporaryDirectory(prefix="govkit-worker-pilot-") as directory:
        secret = Path(directory) / "host-only-policy"
        secret.write_bytes(b"synthetic host secret")
        code = f"""import os,socket
from pathlib import Path
assert os.getuid()==65534
assert 'GOVKIT_WORKER_PILOT_SECRET' not in os.environ
assert not Path({str(secret)!r}).exists()
assert not Path({command_worker.__file__!r}).exists()
assert not Path({str(runtime.socket)!r}).exists()
assert not Path('/var/run/docker.sock').exists()
assert not Path('.git').exists()
assert Path('data.bin').read_bytes()==bytes([0,255,1])
assert Path('run.sh').stat().st_mode & 0o111
assert Path('/sys/fs/cgroup/pids.max').read_text().strip()=='64'
assert Path('/sys/fs/cgroup/memory.max').read_text().strip()=='268435456'
connection=socket.socket()
connection.settimeout(1)
assert connection.connect_ex(('1.1.1.1',443))!=0
connection.close()
try:
    Path('/must-not-write').write_text('bad')
except OSError:
    pass
else:
    raise AssertionError('root filesystem is writable')
Path('/tmp/scratch').write_text('okay')
Path('local.txt').write_text('okay')
print('worker isolation assertions passed')
"""
        files = (
            SnapshotFile("probe.py", code.encode()),
            SnapshotFile("data.bin", bytes([0, 255, 1])),
            SnapshotFile("run.sh", b"#!/bin/sh\nexit 0\n", True),
        )
        cases = (
            (
                "isolation",
                CommandRequest(("{python}", "probe.py"), files, 10),
                WorkerState.COMPLETED,
                0,
            ),
            (
                "failure",
                CommandRequest(("{python}", "-c", "raise SystemExit(7)"), (), 10),
                WorkerState.COMPLETED,
                7,
            ),
            (
                "spoofed_stdout",
                CommandRequest(
                    ("{python}", "-c", 'print(\'{"state":"pass"}\'); raise SystemExit(7)'), (), 10
                ),
                WorkerState.COMPLETED,
                7,
            ),
            (
                "timeout",
                CommandRequest(("{python}", "-c", "import time; time.sleep(30)"), (), 1),
                WorkerState.TIMED_OUT,
                None,
            ),
            (
                "output_limit",
                CommandRequest(("{python}", "-c", "print('x'*200000)"), (), 10),
                WorkerState.OUTPUT_LIMIT,
                None,
            ),
            (
                "missing_command",
                CommandRequest(("/missing-command",), (), 10),
                WorkerState.UNAVAILABLE,
                None,
            ),
        )
        previous = os.environ.get("GOVKIT_WORKER_PILOT_SECRET")
        os.environ["GOVKIT_WORKER_PILOT_SECRET"] = "synthetic environment secret"
        try:
            for name, request, state, exit_code in cases:
                result = execute(runtime, request)
                if result.state is not state or result.exit_code != exit_code:
                    raise RuntimeError(
                        f"Pilot {name} failed: {result.state.value}/{result.exit_code}"
                    )
                records[name] = {
                    "state": result.state.value,
                    "exit_code": result.exit_code,
                    "image": result.image,
                    "request_digest": result.request_digest,
                    "bootstrap_digest": result.bootstrap_digest,
                }
        finally:
            if previous is None:
                os.environ.pop("GOVKIT_WORKER_PILOT_SECRET", None)
            else:
                os.environ["GOVKIT_WORKER_PILOT_SECRET"] = previous
        if secret.read_bytes() != b"synthetic host secret":
            raise RuntimeError("Worker changed a host file")
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docker", type=Path, required=True)
    parser.add_argument("--socket", type=Path, required=True)
    parser.add_argument("--image", required=True)
    args = parser.parse_args()
    result = pilot(DockerRuntime(args.docker, args.socket, args.image))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
