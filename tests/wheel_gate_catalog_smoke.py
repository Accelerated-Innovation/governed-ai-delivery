"""Runtime-only gate catalog and frozen legacy selection verification."""

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import cli
from cli import paths
from cli.gate_catalog import compose_catalog, parse_catalog
from cli.manifest import load_manifest, resolve_variant_files
from cli.pack_loading import bundled_catalog
from cli.profiles import parse_profile
from cli.version import GOVKIT_VERSION


def run_pilot(root, agent):
    root.mkdir(parents=True, exist_ok=True)
    source = root / "profile.json"
    example = json.loads((paths.GOVERNANCE_DIR / "examples/pipeline/profile.json").read_text())
    example["integrations"]["agent"] = agent
    for capabilities in (
        ["application-governance"],
        ["application-governance", "llm-evaluation"],
        ["gherkin-delivery"],
    ):
        profile = {**example, "capabilities": [{"id": c} for c in capabilities]}
        profile["policy"] = {
            **example["policy"],
            "required_capabilities": [capabilities[0]],
            "required_checks": (
                [{"id": "llm-exact-match", "capability_id": "llm-evaluation"}]
                if "llm-evaluation" in capabilities
                else []
            ),
        }
        previous_gates = None
        for provider in ("github", "azure"):
            profile["integrations"]["ci"] = provider
            source.write_text(json.dumps(profile))
            before = {
                p.relative_to(root).as_posix(): p.read_bytes()
                for p in root.rglob("*")
                if p.is_file()
            }
            result = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-m",
                    "cli.govkit",
                    "pipeline",
                    "catalog",
                    "--profile",
                    str(source),
                    "--json",
                ],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0, result.stderr + result.stdout
            record = json.loads(result.stdout)
            expected = compose_catalog(
                parse_profile(profile), bundled_catalog(), govkit_version=GOVKIT_VERSION
            )
            assert record == expected.document
            assert parse_catalog(record).to_json() == expected.to_json()
            assert record["execution"] == "not-run" and record["enforcement"] == "unknown"
            assert record["capability_requirements"] == [
                {"id": capabilities[0], "source": profile["policy"]["source"]["reference"]}
            ]
            ids = {g["id"] for g in record["gates"]}
            assert ("llm-exact-match" in ids) == ("llm-evaluation" in capabilities)
            if "llm-evaluation" in capabilities:
                gate = next(g for g in record["gates"] if g["id"] == "llm-exact-match")
                assert any(
                    r["kind"] == "repository" and r["capability_id"] == "llm-evaluation"
                    for r in gate["requirements"]
                )
            if previous_gates is not None:
                assert record["gates"] == previous_gates
            previous_gates = record["gates"]
            assert before == {
                p.relative_to(root).as_posix(): p.read_bytes()
                for p in root.rglob("*")
                if p.is_file()
            }
    profile["capabilities"] = [{"id": "unavailable-capability"}]
    source.write_text(json.dumps(profile))
    failed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-m",
            "cli.govkit",
            "pipeline",
            "catalog",
            "--profile",
            str(source),
            "--json",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert failed.returncode == 1, failed.stderr
    assert json.loads(failed.stdout)["decisions"]


def verify_legacy(baseline):
    cases = json.loads(baseline.read_text())["cases"]
    for case, expected in cases.items():
        agent, kind, level, provider, stack = case.split("|")
        options = {"level": level, "type": kind, "ci": provider}
        if stack != "-":
            options["stack"] = stack
        selection = resolve_variant_files(load_manifest(agent), options)
        actual = hashlib.sha256(
            json.dumps(selection, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        assert actual == expected, case
    return len(cases)


if __name__ == "__main__":
    assert Path(cli.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()), cli.__file__
    count = verify_legacy(Path(__file__).parent / "fixtures/legacy-resolution-baseline.json")
    with tempfile.TemporaryDirectory(prefix="govkit-wheel-gates-") as directory:
        for agent in ("codex", "claude-code", "copilot"):
            run_pilot(Path(directory) / agent, agent)
    print(
        f"{count} frozen legacy selections and three-agent catalog pilots passed across both providers and independent capabilities."
    )
