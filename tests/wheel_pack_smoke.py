"""Run with a clean wheel Python and -I; never import this checkout's CLI."""

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from cli import pack_loading, paths
from cli.agent_layout import AGENT_LAYOUTS
from cli.pack_resolution import resolve_packs
from cli.pack_store import verify_lock
from cli.profiles import load_profile, parse_profile
from cli.version import GOVKIT_VERSION

assert Path(pack_loading.__file__).is_relative_to(sys.prefix)
catalog = pack_loading.bundled_catalog()
assert {p.id for p in catalog} == {
    "application-governance",
    "gherkin-delivery",
    "llm-evaluation",
    "llm-application",
    "otter-skills",
    "skill-oriented-agent-architecture",
    "vision-inference",
}
command = [sys.executable, "-I", "-m", "cli.govkit", "pack"]
listed = subprocess.run(command + ["list", "--json"], check=True, capture_output=True, text=True)
assert len(json.loads(listed.stdout)["available"]) == len(catalog)
examples = sorted((paths.GOVERNANCE_DIR / "examples/packs").glob("*.yaml"))
assert len(examples) == 2
for example in examples:
    resolution = resolve_packs(load_profile(example), catalog, govkit_version=GOVKIT_VERSION)
    assert resolution.ready, resolution.decisions
    assert not {"gherkin-delivery", "llm-evaluation"} <= {p.id for p in resolution.packs}

frontmatter = {}
installs = 0
for agent, layout in AGENT_LAYOUTS.items():
    for pack in catalog:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "consumer"
            (target / ".govkit").mkdir(parents=True)
            profile = parse_profile(
                {
                    "schema_version": 1,
                    "source": {"reference": "policy.md", "authority": "accepted"},
                    "repository": {"id": "wheel-fixture", "project_type": "api"},
                    "integrations": {"agent": agent},
                    "capabilities": [{"id": pack.id}],
                    "policy": {"source": {"reference": "policy.md", "authority": "accepted"}},
                }
            )
            (target / ".govkit/profile.yaml").write_text(json.dumps(profile.document))
            options = ["--target", str(target), "--json"]
            result = subprocess.run(
                command + ["preview"] + options, check=True, capture_output=True, text=True
            )
            preview = json.loads(result.stdout)
            assert preview["resolution"]["execution"] == "not-run"
            assert not (target / ".govkit/pack-lock.json").exists()
            subprocess.run(
                command + ["apply"] + options, check=True, capture_output=True, text=True
            )
            assert verify_lock(target).ready
            assert not (target / ".govkit/marker.json").exists()
            assert not (target / "features").exists()
            before = {
                p.relative_to(target): (p.read_bytes(), p.stat().st_mtime_ns)
                for p in target.rglob("*")
                if p.is_file()
            }
            subprocess.run(
                command + ["apply"] + options, check=True, capture_output=True, text=True
            )
            assert before == {
                p.relative_to(target): (p.read_bytes(), p.stat().st_mtime_ns)
                for p in target.rglob("*")
                if p.is_file()
            }
            for skill in (target / layout.skills_dir).glob("*/SKILL.md"):
                content = skill.read_text()
                assert "{{pack_root}}" not in content
                header = content.split("---")[1]
                assert frontmatter.setdefault(skill.parent.name, header) == header
                for reference in re.findall(r"\]\((references/[^)]+)\)", content):
                    assert (skill.parent / reference).is_file(), reference
            moved = Path(directory) / "relocated"
            shutil.move(target, moved)
            assert verify_lock(moved).ready
            if pack.id == "llm-evaluation":
                shutil.rmtree(moved / layout.skills_dir)
                record = moved / "results.json"
                record.write_text('{"cases":[{"id":"hello","expected":"hello","actual":"hello"}]}')
                check = command + [
                    "check",
                    "--target",
                    str(moved),
                    "llm-exact-match",
                    "--",
                    "--results",
                    "results.json",
                ]
                subprocess.run(check, check=True, capture_output=True, text=True)
                record.write_text('{"cases":[{"id":"hello","expected":"hello","actual":"wrong"}]}')
                failed = subprocess.run(check, capture_output=True, text=True)
                assert failed.returncode == 1 and json.loads(failed.stdout)["failed"] == ["hello"]
            installs += 1
print(
    f"Pack wheel smoke passed: {len(catalog)} packs, {installs} installs across 3 agents, 2 profiles, portable references and independent checks"
)
