"""Run real native alias installs and historical lock upgrades from a wheel."""

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

from cli import native_skills, paths
from cli.agent_layout import AGENT_LAYOUTS

assert Path(native_skills.__file__).is_relative_to(sys.prefix)
command = [sys.executable, "-I", "-m", "cli.govkit"]


def run(*args):
    return subprocess.run(command + list(args), check=True, capture_output=True, text=True)


def snapshot(target):
    return {
        p.relative_to(target): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in target.rglob("*")
        if p.is_file()
    }


pack = paths.EXTENSION_PACKS_DIR / "otter-skills"
manifest = yaml.safe_load((pack / "manifest.yaml").read_text())
for agent, layout in AGENT_LAYOUTS.items():
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory)
        run(
            "apply",
            "--target",
            directory,
            "--agent",
            agent,
            "--level",
            "3",
            "--type",
            "api",
            "--ci",
            "github",
            "--stack",
            "python-fastapi",
        )
        run("extension", "add", "otter-skills", "--target", directory)
        for entry in manifest["skills"]:
            native = target / layout.skills_dir / entry["install_as"] / "SKILL.md"
            text = native.read_text()
            assert yaml.safe_load(text.split("---", 2)[1])["name"] == entry["install_as"]
            for sibling in manifest["skills"]:
                bare = Path(sibling["path"]).name
                assert not re.search(rf"(?<![\w/-]){re.escape(bare)}(?![\w/-])", text)
            source = pack / entry["path"] / "SKILL.md"
            copied = target / "extensions/otter-skills" / entry["path"] / "SKILL.md"
            assert source.read_bytes() == copied.read_bytes()
        customized = target / layout.skills_dir / "otter-unit-testing/SKILL.md"
        customized.write_text("User skill instructions\n")
        refused = subprocess.run(
            command + ["extension", "add", "otter-skills", "--target", directory],
            capture_output=True,
            text=True,
        )
        assert refused.returncode == 1 and "--force" in refused.stderr + refused.stdout
        assert customized.read_text() == "User skill instructions\n"
        run("extension", "add", "otter-skills", "--target", directory, "--force")
        assert "name: otter-unit-testing\n" in customized.read_text()

with tempfile.TemporaryDirectory() as directory:
    target = Path(directory) / "consumer"
    fixture = Path(__file__).parent / "fixtures/native-skill-lock-v1"
    shutil.copytree(fixture, target)
    before = snapshot(target)
    run("pack", "verify", "--target", str(target))
    assert snapshot(target) == before
    source = next((target / ".govkit/packs/sample").iterdir())
    options = ["--target", str(target), "--source", str(source), "--json"]
    preview = json.loads(run("pack", "preview", *options).stdout)
    assert snapshot(target) == before
    assert any(
        op["action"] == "update" and op["path"].endswith("SKILL.md") for op in preview["operations"]
    )
    run("pack", "apply", *options)
    assert "name: sample-help\n" in (target / ".agents/skills/sample-help/SKILL.md").read_text()
    run("pack", "verify", "--target", str(target))
    after = snapshot(target)
    run("pack", "apply", *options)
    assert snapshot(target) == after
    for relative, original in before.items():
        if relative.as_posix().startswith(".govkit/packs/"):
            assert after[relative] == original

print(
    "Native skill wheel smoke passed: 3 legacy agents, upstream preservation, protected refresh and historical lock upgrade"
)
