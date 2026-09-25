"""GovKit-owned skill identities agree in source, manifests and real installs."""

import shutil
from pathlib import Path

import pytest
import yaml
from packaging.version import Version

from cli import paths
from cli.agent_layout import AGENT_LAYOUTS
from cli.manifest import load_manifest, resolve_variant_files
from cli.pack_loading import PackError, bundled_catalog, load_pack
from cli.pack_store import apply_install, preview_install, verify_lock
from cli.version import GOVKIT_VERSION
from tests.test_capability_packs import profile
from tests.test_pack_store import snapshot, write_profile

PREVIOUS_VERSIONS = {
    "application-governance": "1.1.1",
    "gherkin-delivery": "1.0.1",
    "llm-evaluation": "1.0.1",
}


def skill_name(path):
    return yaml.safe_load(path.read_text().split("---", 2)[1])["name"]


@pytest.mark.parametrize("agent", AGENT_LAYOUTS)
def test_legacy_skill_sources_and_destinations_match_metadata(agent):
    manifest = load_manifest(agent)
    selected = set()
    for kind in manifest["variants"]["type"]:
        for level in ("3", "4", "5"):
            files, _, _ = resolve_variant_files(
                manifest, {"type": kind, "level": level, "ci": "github"}
            )
            for entry in files:
                source = paths.AGENTS_DIR / agent / entry["src"] / "SKILL.md"
                if source.is_file():
                    selected.add(source)
                    assert source.parent.name == skill_name(source) == Path(entry["dest"]).name
    assert selected == set((paths.AGENTS_DIR / agent / "skills").rglob("SKILL.md"))
    assert selected, "Every agent must ship native skills"


@pytest.mark.parametrize("capability", PREVIOUS_VERSIONS)
def test_first_party_pack_sources_match_declared_install_names(capability):
    pack = next(pack for pack in bundled_catalog() if pack.id == capability)
    assert pack.skills
    for skill in pack.skills:
        source = pack.root / skill.path / "SKILL.md"
        assert source.parent.name == skill_name(source) == skill.install_as
        assert skill.install_as.startswith("govkit-")


@pytest.mark.parametrize("agent", AGENT_LAYOUTS)
@pytest.mark.parametrize("capability", PREVIOUS_VERSIONS)
def test_installed_first_party_skill_names_match_native_directories(tmp_path, agent, capability):
    target = tmp_path / "consumer"
    source = write_profile(target, profile([capability], agent=agent))
    proposal = preview_install(source, target, bundled_catalog(), govkit_version=GOVKIT_VERSION)

    apply_install(proposal)

    assert verify_lock(target).ready
    native = target / AGENT_LAYOUTS[agent].skills_dir
    installed = list(native.glob("*/SKILL.md"))
    assert installed
    for skill in installed:
        assert skill_name(skill) == skill.parent.name
        assert skill.parent.name.startswith("govkit-")


def install_previous_metadata(tmp_path, agent):
    """Recreate PR 199's prefixed destinations with unprefixed source metadata."""
    previous = []
    for pack in bundled_catalog():
        if pack.id not in PREVIOUS_VERSIONS:
            continue
        root = tmp_path / "previous" / pack.id
        shutil.copytree(pack.root, root)
        manifest = yaml.safe_load((root / "manifest.yaml").read_text())
        manifest["version"] = PREVIOUS_VERSIONS[pack.id]
        for skill in manifest["skills"]:
            old_name = skill["install_as"].removeprefix("govkit-")
            current = root / skill["path"]
            old = root / "skills" / old_name
            if current != old:
                current.rename(old)
            skill["path"] = f"skills/{old_name}"
            metadata = old / "SKILL.md"
            metadata.write_text(
                metadata.read_text().replace(
                    f"name: {skill['install_as']}\n", f"name: {old_name}\n"
                )
            )
        (root / "manifest.yaml").write_text(yaml.safe_dump(manifest))
        previous.append(load_pack(root, source_kind="bundled"))
    target = tmp_path / "consumer"
    source = write_profile(target, profile(PREVIOUS_VERSIONS, agent=agent))
    apply_install(preview_install(source, target, tuple(previous), govkit_version=GOVKIT_VERSION))
    return target, source


@pytest.mark.parametrize("agent", AGENT_LAYOUTS)
@pytest.mark.parametrize("edited", [False, True], ids=["unchanged", "user-edited"])
def test_metadata_upgrade_preserves_notes_and_protects_user_edits(tmp_path, agent, edited):
    target, source = install_previous_metadata(tmp_path, agent)
    assert verify_lock(target).ready, "Existing locks remain valid before a reviewed update"
    native = target / AGENT_LAYOUTS[agent].skills_dir
    skill = native / "govkit-application-governance/SKILL.md"
    assert skill_name(skill) == "application-governance"
    notes = skill.parent / "notes.md"
    notes.write_text("Team-owned notes\n")
    if edited:
        skill.write_text(skill.read_text() + "\nTeam-owned customization\n")
    before = snapshot(target)
    proposal = preview_install(source, target, bundled_catalog(), govkit_version=GOVKIT_VERSION)
    assert snapshot(target) == before, "Preview is read-only"

    if edited:
        with pytest.raises(PackError):
            apply_install(proposal)
        assert snapshot(target) == before
    else:
        apply_install(proposal)
        assert verify_lock(target).ready
        for installed in native.glob("*/SKILL.md"):
            assert skill_name(installed) == installed.parent.name
        relative = notes.relative_to(target).as_posix()
        assert snapshot(target)[relative] == before[relative]
        for pack in proposal.resolution.packs:
            assert Version(pack.version) > Version(PREVIOUS_VERSIONS[pack.id])
