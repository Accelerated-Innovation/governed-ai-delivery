"""Exercise bundled brownfield examples using only wheel runtime dependencies."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from cli import discovery, paths
from cli.discovery import load_baseline

assert Path(discovery.__file__).is_relative_to(sys.prefix)
examples = sorted((paths.GOVERNANCE_DIR / "examples/discovery").glob("*.json"))
assert len(examples) == 4
command = [sys.executable, "-I", "-m", "cli.govkit"]


def invoke(*args):
    result = subprocess.run(command + list(args), check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def snapshot(target):
    return {
        p.relative_to(target).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in target.rglob("*")
        if p.is_file()
    }


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    for example in examples:
        fixture = json.loads(example.read_text())
        target = root / example.stem
        target.mkdir()
        for relative, content in fixture["files"].items():
            path = target / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        options = ["--target", str(target), "--json"]
        if fixture.get("profile"):
            profile = root / f"{example.stem}-profile.json"
            profile.write_text(json.dumps(fixture["profile"]))
            options += ["--profile", str(profile)]
        before = snapshot(target)
        first = invoke("discover", *options)
        record = root / f"{example.stem}-reviewed.json"
        record.write_text(json.dumps(first))
        assert load_baseline(record) == first
        second = invoke("discover", *options, "--baseline", str(record))
        assert second["review"] == []
        assert snapshot(target) == before
        if example.stem == "unfamiliar-mcp":
            assert "fastapi" not in json.dumps(first).lower()
        if fixture.get("profile"):
            assert first["install_ready"]
            invoke("profile", "apply", "--target", str(target), "--profile", str(profile), "--json")
            invoke("pack", "apply", "--target", str(target), "--json")
            after = snapshot(target)
            assert all(after[p] == value for p, value in before.items())
            assert not (target / "features").exists()
            assert not (target / ".govkit/marker.json").exists()
            current = invoke("discover", "--target", str(target), "--json")
            assert current["install_ready"]
            assert all(op["action"] == "preserve" for op in current["operations"])
            invoke("pack", "apply", "--target", str(target), "--json")
            assert snapshot(target) == after
            lock = target / ".govkit/pack-lock.json"
            lock.write_text("{}")
            broken = snapshot(target)
            report = invoke("discover", "--target", str(target), "--json")
            assert not report["install_ready"]
            assert any(d["id"] == "install:preview-unavailable" for d in report["review"])
            assert report["observations"] and snapshot(target) == broken
        if example.stem == "sparse-repository":
            manifest = target / "package.json"
            manifest.write_text('{"dependencies":{"openai":"6"}}')
            changed = invoke("discover", *options, "--baseline", str(record))
            assert any(d["id"] == "capability:llm-evaluation" for d in changed["review"])
            assert changed["accepted_profile"] is None
            reference_args = [
                arg for index in range(10) for arg in ("--reference", f"ref-{index}.txt")
            ]
            bounded = invoke("discover", *options, "--max-files", "2", *reference_args)
            assert len(bounded["references"]) == 2
            assert "reference-limit" in bounded["coverage"]["limitations"]
    target = root / "incomplete-baseline"
    target.mkdir()
    old_source = target / "old.py"
    old_source.write_text("import mcp\n")
    oversized = target / "README.md"
    oversized.write_text("x" * 65)
    options = ["--target", str(target), "--max-bytes", "64", "--json"]
    prior = invoke("discover", *options)
    assert not prior["coverage"]["complete"]
    record = root / "incomplete-reviewed.json"
    record.write_text(json.dumps(prior))
    old_source.unlink()
    oversized.write_text("# Short\n")
    current = invoke("discover", *options, "--baseline", str(record))
    assert current["coverage"]["complete"]
    assert next(c for c in current["changes"] if c["source"] == "old.py")["kind"] == "unavailable"
print(
    "Discovery wheel smoke passed: four examples, explicit adoption, preservation, idempotence focused rediscovery and review regressions"
)
