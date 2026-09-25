"""Verify source and installed legacy skill identities from a clean wheel."""

import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

from cli import paths
from cli.agent_layout import AGENT_LAYOUTS

assert Path(paths.__file__).is_relative_to(sys.prefix)
for agent, layout in AGENT_LAYOUTS.items():
    sources = list((paths.AGENTS_DIR / agent / "skills").rglob("SKILL.md"))
    assert sources
    for source in sources:
        name = yaml.safe_load(source.read_text().split("---", 2)[1])["name"]
        assert name == source.parent.name, source
    for kind in ("api", "ui-react"):
        with tempfile.TemporaryDirectory() as directory:
            command = [
                sys.executable,
                "-I",
                "-m",
                "cli.govkit",
                "apply",
                "--target",
                directory,
                "--agent",
                agent,
                "--level",
                "5",
                "--type",
                kind,
                "--ci",
                "github",
            ]
            if kind == "api":
                command += ["--stack", "python-fastapi"]
            result = subprocess.run(command, capture_output=True, text=True)
            assert result.returncode == 0, result.stdout + result.stderr
            installed = list((Path(directory) / layout.skills_dir).glob("*/SKILL.md"))
            assert installed
            for skill in installed:
                name = yaml.safe_load(skill.read_text().split("---", 2)[1])["name"]
                assert name == skill.parent.name, skill
                assert name.startswith("govkit-"), skill

print("Skill name wheel smoke passed: all legacy sources and 6 installs across 3 agents/2 types")
