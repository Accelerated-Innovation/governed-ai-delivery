"""An isolated worker receives bytes, never authority over the engine host."""

import json
import sys
from dataclasses import replace

import pytest

from cli import command_worker
from cli.command_worker import (
    MAX_OUTPUT_BYTES,
    CommandRequest,
    DockerRuntime,
    SnapshotFile,
    WorkerState,
    execute,
)
from cli.observation_limits import MAX_FILE_BYTES, MAX_FILES, MAX_TOTAL_BYTES

IMAGE = "python@sha256:" + "a" * 64
CONTAINER = "b" * 64


@pytest.fixture
def docker(tmp_path):
    """Controlled external CLI; production validation and orchestration stay real."""
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"exit": 0}))
    log = tmp_path / "calls.jsonl"
    cli = tmp_path / "docker"
    cli.write_text(
        f"#!{sys.executable}\n"
        "import json,os,sys,time\nfrom pathlib import Path\n"
        f"settings=json.loads(Path({str(settings)!r}).read_text())\n"
        f"log=Path({str(log)!r})\n"
        "args=sys.argv[1:]\n"
        "with log.open('a') as stream: stream.write(json.dumps({'argv':args,'env':dict(os.environ)})+'\\n')\n"
        "action=args[4]\n"
        "if action=='create':\n"
        " cid=args[args.index('--cidfile')+1]\n"
        f" Path(cid).write_text({CONTAINER!r})\n"
        " if settings.get('create_error'): sys.exit(125)\n"
        f" print({CONTAINER!r})\n"
        "elif action=='inspect':\n"
        " if 'Mounts' in args[6]: print(json.dumps(settings.get('mounts',[])))\n"
        " else:\n"
        "  state={'Running':False,'Dead':False,'OOMKilled':False,'Error':'','ExitCode':settings.get('exit',0)}\n"
        "  state.update(settings.get('state',{}))\n"
        "  print('bad json' if settings.get('bad_state') else json.dumps(state))\n"
        "elif action=='start':\n"
        " payload=sys.stdin.buffer.read()\n"
        f" Path({str(tmp_path / 'input.json')!r}).write_bytes(payload)\n"
        " if settings.get('flood'): sys.stdout.buffer.write(b'x'*200000)\n"
        " else: print('measured output')\n"
        " sys.exit(settings.get('exit',0))\n"
        "elif action=='rm': sys.exit(1 if settings.get('cleanup_error') else 0)\n"
        "else: sys.exit(125)\n"
    )
    cli.chmod(0o700)
    runtime = DockerRuntime(cli, tmp_path / "daemon.sock", IMAGE)
    return runtime, settings, log, tmp_path / "input.json"


def sample_request():
    return CommandRequest(("{python}", "test.py"), (SnapshotFile("test.py", b"print('ok')\n"),), 5)


@pytest.mark.parametrize(
    "path", ["/host", "../host", "a/../b", "a//b", "a\\b", ".git/config", "x/.GIT/config", "a\x00b"]
)
def test_snapshot_rejects_paths_that_escape_or_expose_git_metadata(path):
    with pytest.raises(ValueError):
        SnapshotFile(path, b"data")


@pytest.mark.parametrize("argv", [(), ("",), ("a\x00b",), ["python"], (1,)])
def test_command_arguments_are_an_immutable_nonempty_argument_vector(argv):
    with pytest.raises(ValueError):
        CommandRequest(argv, (), 5)


@pytest.mark.parametrize("timeout", [True, 0, -1, 601, 1.5])
def test_timeout_has_an_explicit_bounded_integer_contract(timeout):
    with pytest.raises(ValueError):
        CommandRequest(("true",), (), timeout)


@pytest.mark.parametrize("paths", [("a", "a"), ("a", "a/b"), ("a/b", "a")])
def test_snapshot_rejects_duplicate_or_conflicting_destinations(paths):
    with pytest.raises(ValueError):
        CommandRequest(("true",), tuple(SnapshotFile(p, b"x") for p in paths), 5)


@pytest.mark.parametrize(
    "image", ["python:latest", "python:3.12", "--privileged", "python@sha256:abc"]
)
def test_runtime_requires_a_content_digest_not_a_mutable_image_tag(tmp_path, image):
    with pytest.raises(ValueError):
        DockerRuntime(tmp_path / "docker", tmp_path / "socket", image)


@pytest.mark.parametrize("exit_code", [0, 7])
def test_worker_returns_measured_exit_and_bounded_output(docker, exit_code):
    runtime, settings, _, payload = docker
    settings.write_text(json.dumps({"exit": exit_code}))
    request = sample_request()
    result = execute(runtime, request)
    assert result.state is WorkerState.COMPLETED
    assert result.exit_code == exit_code
    assert result.stdout == b"measured output\n"
    assert result.stderr == b""
    assert result.image == IMAGE
    assert result.request_digest == request.digest
    assert len(result.bootstrap_digest) == 64
    assert json.loads(payload.read_text())["argv"] == ["{python}", "test.py"]


def test_worker_never_forwards_host_secrets_or_ambient_docker_configuration(docker, monkeypatch):
    runtime, _, log, _ = docker
    monkeypatch.setenv("GOVKIT_PROVIDER_TOKEN", "must-not-leave-host")
    monkeypatch.setenv("DOCKER_HOST", "tcp://wrong.invalid:1234")
    monkeypatch.setenv("DOCKER_CONTEXT", "wrong")
    monkeypatch.setenv("PYTHONPATH", "/untrusted")
    result = execute(runtime, sample_request())
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assert result.state is WorkerState.COMPLETED
    for call in calls:
        assert (
            not {"GOVKIT_PROVIDER_TOKEN", "DOCKER_HOST", "DOCKER_CONTEXT", "PYTHONPATH"}
            & call["env"].keys()
        )
        assert call["argv"][:2] == ["--host", "unix://" + str(runtime.socket)]
        assert call["argv"][2] == "--config"


def test_worker_requests_resource_limits_without_host_mounts_or_privilege(docker):
    runtime, _, log, _ = docker
    result = execute(runtime, sample_request())
    calls = [json.loads(line)["argv"] for line in log.read_text().splitlines()]
    create = next(args for args in calls if args[4] == "create")
    assert result.state is WorkerState.COMPLETED
    for option, value in {
        "--pull": "never",
        "--network": "none",
        "--user": "65534:65534",
        "--cap-drop": "ALL",
        "--security-opt": "no-new-privileges",
        "--memory": "256m",
        "--memory-swap": "256m",
        "--cpus": "1",
        "--pids-limit": "64",
        "--log-driver": "none",
        "--ipc": "none",
    }.items():
        assert create[create.index(option) + 1] == value
    assert {"--read-only", "--no-healthcheck"} <= set(create)
    assert not {
        "--mount",
        "--volume",
        "--volumes-from",
        "--privileged",
        "--use-api-socket",
        "--env-file",
    } & set(create)
    assert calls[-1][4:] == ["rm", "--force", "--volumes", CONTAINER]


@pytest.mark.parametrize(
    "settings",
    [
        {"create_error": True},
        {"bad_state": True},
        {"state": {"OOMKilled": True}},
        {"state": {"Running": True}},
        {"state": {"ExitCode": True}},
        {"state": {"ExitCode": 3}},
        {"state": {"Error": "private runtime failure"}},
        {"exit": 125},
        {"exit": 126},
        {"exit": 127},
        {"exit": 137},
    ],
)
def test_unavailable_or_ambiguous_execution_never_becomes_a_command_verdict(docker, settings):
    runtime, config, log, _ = docker
    config.write_text(json.dumps(settings))
    result = execute(runtime, sample_request())
    assert result.state is WorkerState.UNAVAILABLE
    assert result.exit_code is None
    assert result.stdout == result.stderr == b""
    assert json.loads(log.read_text().splitlines()[-1])["argv"][4] == "rm"


def test_image_declared_volumes_are_rejected_before_project_execution(docker):
    runtime, settings, log, payload = docker
    settings.write_text(json.dumps({"mounts": [{"Type": "volume", "Destination": "/data"}]}))
    result = execute(runtime, sample_request())
    assert result.state is WorkerState.UNAVAILABLE
    assert not payload.exists()
    assert "start" not in [json.loads(line)["argv"][4] for line in log.read_text().splitlines()]


def test_excess_output_cannot_be_returned_as_a_successful_measurement(docker):
    runtime, settings, _, _ = docker
    settings.write_text(json.dumps({"flood": True}))
    result = execute(runtime, sample_request())
    assert result.state is WorkerState.OUTPUT_LIMIT
    assert result.exit_code is None
    assert len(result.stdout) <= MAX_OUTPUT_BYTES


def test_failed_container_cleanup_invalidates_an_otherwise_successful_run(docker):
    runtime, settings, _, _ = docker
    settings.write_text(json.dumps({"cleanup_error": True}))
    result = execute(runtime, sample_request())
    assert result.state is WorkerState.CLEANUP_FAILED
    assert result.exit_code is None
    assert result.stdout == result.stderr == b""


def test_missing_docker_does_not_fall_back_to_running_on_the_host(docker, tmp_path):
    runtime, _, _, _ = docker
    marker = tmp_path / "must-not-exist"
    request = CommandRequest(
        (sys.executable, "-c", f"open({str(marker)!r},'w').write('unsafe')"), (), 5
    )
    result = execute(replace(runtime, executable=tmp_path / "missing"), request)
    assert result.state is WorkerState.UNAVAILABLE
    assert not marker.exists()


@pytest.mark.parametrize("content", [bytearray(b"mutable"), "text", b"x" * (MAX_FILE_BYTES + 1)])
def test_file_input_is_immutable_bytes_with_a_fixed_size_ceiling(content):
    with pytest.raises(ValueError):
        SnapshotFile("file", content)


@pytest.mark.parametrize("mode", [1, "100755", None])
def test_file_executability_requires_a_boolean_without_special_permission_bits(mode):
    with pytest.raises(ValueError):
        SnapshotFile("file", b"x", mode)


def test_snapshot_cannot_exceed_the_observer_file_count_ceiling():
    files = tuple(SnapshotFile(str(i), b"") for i in range(MAX_FILES + 1))
    with pytest.raises(ValueError):
        CommandRequest(("true",), files, 5)


def test_snapshot_total_content_ceiling_cannot_be_bypassed_with_multiple_files():
    files = tuple(
        SnapshotFile(str(i), b"x" * MAX_FILE_BYTES)
        for i in range(MAX_TOTAL_BYTES // MAX_FILE_BYTES + 1)
    )
    with pytest.raises(ValueError):
        CommandRequest(("true",), files, 5)


def test_empty_non_executable_argument_is_preserved_as_an_argument(docker):
    runtime, _, _, payload = docker
    request = CommandRequest(("{python}", "-c", "", "with space", "$(no-shell)"), (), 5)
    result = execute(runtime, request)
    assert result.state is WorkerState.COMPLETED
    assert json.loads(payload.read_text())["argv"] == list(request.argv)


def test_argument_count_is_bounded_even_when_the_arguments_are_empty():
    with pytest.raises(ValueError):
        CommandRequest(("true",) + ("",) * 4096, (), 5)


def test_process_deadline_is_controlled_and_cannot_return_a_verdict(monkeypatch):
    clock = iter((0, 2))
    monkeypatch.setattr(command_worker.time, "monotonic", lambda: next(clock, 2))
    result = command_worker._run(
        [sys.executable, "-I", "-c", "import time; time.sleep(60)"], {}, timeout=1
    )
    assert result.state is WorkerState.TIMED_OUT
    assert result.returncode != 0


def test_missing_transport_executable_produces_no_output(tmp_path):
    result = command_worker._run([str(tmp_path / "missing")], {}, timeout=1)
    assert result.state is WorkerState.UNAVAILABLE
    assert result.returncode is None
    assert result.stdout == result.stderr == b""
