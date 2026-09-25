"""Review regressions for native skill ownership and the published quickstart."""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from cli.agent_layout import AGENT_LAYOUTS
from cli.pack_loading import PackError, bundled_catalog, load_pack
from cli.pack_store import apply_install, preview_install, verify_lock
from cli.version import GOVKIT_VERSION
from tests.test_capability_packs import profile
from tests.test_pack_store import snapshot, write_profile

FIRST_PARTY = {
    "application-governance": "1.1.0",
    "gherkin-delivery": "1.0.0",
    "llm-evaluation": "1.0.0",
}
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("agent", ["claude-code", "codex", "copilot"])
@pytest.mark.parametrize("capability", FIRST_PARTY)
def test_first_party_pack_uses_namespace_without_colliding_with_user_skill(
    tmp_path, agent, capability
):
    target = tmp_path / "project"
    source = write_profile(target, profile([capability], agent=agent))
    native = target / AGENT_LAYOUTS[agent].skills_dir
    user = native / capability / "SKILL.md"
    user.parent.mkdir(parents=True)
    user.write_text("Project-owned skill, not GovKit content.\n")
    before = snapshot(target)
    proposal = preview_install(source, target, bundled_catalog(), govkit_version=GOVKIT_VERSION)
    apply_install(proposal)
    assert verify_lock(target).ready
    assert (native / f"govkit-{capability}" / "SKILL.md").is_file()
    after = snapshot(target)
    assert {name: after[name] for name in before} == before
    assert all(
        skill.parent.name.startswith("govkit-")
        for skill in native.glob("*/SKILL.md")
        if skill != user
    )


def install_previous_layout(tmp_path, agent):
    """A real pinned install with the previous versions and unprefixed destinations."""
    target = tmp_path / "project"
    source = write_profile(target, profile(FIRST_PARTY, agent=agent))
    previous = []
    for pack in bundled_catalog():
        if pack.id not in FIRST_PARTY:
            continue
        root = tmp_path / "previous" / pack.id
        shutil.copytree(pack.root, root)
        manifest = yaml.safe_load((root / "manifest.yaml").read_text())
        manifest["version"] = FIRST_PARTY[pack.id]
        for skill in manifest["skills"]:
            if skill["path"] == f"skills/{pack.id}":
                skill["install_as"] = pack.id
        (root / "manifest.yaml").write_text(yaml.safe_dump(manifest))
        previous.append(load_pack(root, source_kind="bundled"))
    apply_install(preview_install(source, target, tuple(previous), govkit_version=GOVKIT_VERSION))
    return target, source


@pytest.mark.parametrize("agent", ["claude-code", "codex", "copilot"])
@pytest.mark.parametrize("conflict", [None, "old-edit", "new-collision"])
def test_reviewed_namespace_upgrade_preserves_ownership_and_refuses_conflicts(
    tmp_path, agent, conflict
):
    target, source = install_previous_layout(tmp_path, agent)
    assert verify_lock(target).ready, "Existing pinned layouts still verify before an update"
    native = target / AGENT_LAYOUTS[agent].skills_dir
    unrelated = native / "application-governance" / "user-notes.txt"
    unrelated.write_text("Unowned notes must survive a rename.\n")
    if conflict == "old-edit":
        (native / "llm-evaluation/SKILL.md").write_text("User edited the old owned copy.\n")
    elif conflict == "new-collision":
        collision = native / "govkit-llm-evaluation/SKILL.md"
        collision.parent.mkdir(parents=True)
        collision.write_text("Pre-existing user-owned namespaced skill.\n")
    before = snapshot(target)
    proposal = preview_install(source, target, bundled_catalog(), govkit_version=GOVKIT_VERSION)
    assert snapshot(target) == before, "Preview must not migrate installed skills"
    if conflict:
        with pytest.raises(PackError):
            apply_install(proposal)
        assert snapshot(target) == before
    else:
        apply_install(proposal)
        assert verify_lock(target).ready
        for capability in FIRST_PARTY:
            assert (native / f"govkit-{capability}/SKILL.md").is_file()
            assert not (native / capability / "SKILL.md").exists()
        assert (
            snapshot(target)[unrelated.relative_to(target).as_posix()]
            == before[unrelated.relative_to(target).as_posix()]
        )


def test_readme_first_commands_work_with_a_published_cli_without_discovery(tmp_path):
    """The package index and older installed executable are external dependencies."""
    command = re.findall(r"```bash\n(.*?)\n```", (ROOT / "README.md").read_text(), re.S)[0]
    events = tmp_path / "calls.txt"
    shim = """
pip() { test "$*" = "install govkit"; printf 'install\n' >> "$EVENTS"; }
govkit() {
    printf '%s\n' "$*" >> "$EVENTS"
    if test "$*" = "--help"; then printf 'usage: govkit {apply,upgrade,...}\n'; else return 2; fi
}
"""
    result = subprocess.run(
        ["bash", "-euc", shim + command],
        cwd=tmp_path,
        env={"PATH": os.defpath, "EVENTS": str(events)},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, (result.stdout, result.stderr, events.read_text())
    assert events.read_text().splitlines() == ["install", "--help"]
