"""Tests for the shipped otter-skills extension pack (third-party, vendored).

The pack vendors seven software-craft skills from tottinge/otter-skills at a
pinned upstream commit. These tests keep the vendoring honest: the pack must
validate, declare every on-disk skill (and nothing else), carry the upstream
license/notice, record the exact pin, and stay inert to govkit's skill
templating ({{...}} tokens) so doctor D015 never fires on it.
"""

import json
import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from cli.extensions import discover_extensions, validate_extension

REPO_ROOT = Path(__file__).resolve().parent.parent
EXT_DIR = REPO_ROOT / "extensions" / "otter-skills"
MANIFEST_PATH = EXT_DIR / "manifest.yaml"
SCHEMA_PATH = REPO_ROOT / "governance" / "schemas" / "extension-manifest.schema.json"

EXPECTED_SKILLS = {
    "atomic-commit",
    "code-object-naming",
    "legacy-code-safety",
    "representation-refactor-review",
    "story-splitting-for-delivery",
    "unit-testing",
    "user-pov-sliced-stories",
}


def _manifest() -> dict:
    yaml = pytest.importorskip("yaml")
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_extension_discovered():
    exts = discover_extensions(REPO_ROOT)
    assert any(e.id == "otter-skills" for e in exts), "otter-skills not discovered"


def test_extension_validates_cleanly_against_repo():
    ext = next((e for e in discover_extensions(REPO_ROOT) if e.id == "otter-skills"), None)
    assert ext is not None
    assert validate_extension(ext, REPO_ROOT) == []


def test_manifest_matches_extension_schema():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(_manifest())) == []


def test_core_fields():
    m = _manifest()
    assert m["id"] == "otter-skills"
    assert m["extension_type"] == "skills"
    assert m["contract_sets"] == []


def test_provenance_is_pinned():
    """A vendored copy without an exact pin cannot be audited or re-vendored.
    The full SHA is the single source of truth (NOTICE.md points here)."""
    origin = _manifest()["origin"]
    assert origin["upstream_url"] == "https://github.com/tottinge/otter-skills"
    assert re.fullmatch(r"[0-9a-f]{40}", origin["upstream_ref"])
    assert origin["license"] == "Apache-2.0"
    assert origin["upstream_version"]


def test_all_skills_declared_and_no_orphans():
    """Every on-disk skill is declared and every declaration exists — a dir
    the manifest misses would silently not install; a stale declaration
    would fail at add time."""
    declared = {Path(s["path"]).name: s["install_as"] for s in _manifest()["skills"]}
    on_disk = {p.name for p in (EXT_DIR / "skills").iterdir() if p.is_dir()}
    assert set(declared) == on_disk == EXPECTED_SKILLS
    for name, install_as in declared.items():
        assert install_as == f"otter-{name}"
        assert (EXT_DIR / "skills" / name / "SKILL.md").is_file()


def test_skill_frontmatter_is_open_skills_only():
    """Same standard govkit's own skills hold: name + description, nothing
    else — the lowest common denominator across all three agents."""
    yaml = pytest.importorskip("yaml")
    for skill_md in sorted(EXT_DIR.glob("skills/*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8")
        assert text.startswith("---\n"), skill_md
        frontmatter = yaml.safe_load(text.split("---", 2)[1])
        assert set(frontmatter) == {"name", "description"}, skill_md


def test_upstream_agents_subdirs_not_vendored():
    """Each upstream skill carries agents/openai.yaml (OpenAI agent-builder
    config no govkit-supported agent consumes); the sync script drops it."""
    assert not list(EXT_DIR.glob("skills/*/agents"))


def test_no_template_tokens_in_vendored_content():
    """Third-party content must stay inert to template_installed_skills and
    doctor D015 — a stray {{token}} would be flagged (or rewritten) in every
    consuming project."""
    offenders = [
        p
        for p in EXT_DIR.rglob("*.md")
        if re.search(r"\{\{[a-z_.]+\}\}", p.read_text(encoding="utf-8"))
    ]
    assert not offenders, offenders


def test_upstream_license_and_notice_ship_with_the_pack():
    assert (EXT_DIR / "LICENSE").is_file()
    notice = (EXT_DIR / "NOTICE").read_text(encoding="utf-8")
    assert "otter-skills" in notice


def test_root_notice_attributes_the_vendored_pack():
    notice = (REPO_ROOT / "NOTICE.md").read_text(encoding="utf-8")
    assert "otter-skills" in notice
    assert "https://github.com/tottinge/otter-skills" in notice
