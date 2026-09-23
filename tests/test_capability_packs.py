"""Composition and explicit pins, exercised before copying or executing packs."""

import builtins
import socket
from pathlib import Path

import pytest
import yaml

from cli.pack_loading import PackError, bundled_catalog, load_pack
from cli.pack_resolution import resolve_packs
from cli.profiles import parse_profile


def profile(capabilities, *, agent="codex", checks=(), pins=()):
    return parse_profile(
        {
            "schema_version": 1,
            "source": {"reference": "policy.md", "authority": "accepted"},
            "repository": {"id": "service", "project_type": "api", "stack": None},
            "integrations": {"agent": agent, "ci": "github"},
            "capabilities": [{"id": value} for value in capabilities],
            "policy": {
                "source": {"reference": "policy.md", "authority": "accepted"},
                "required_checks": [{"id": value} for value in checks],
            },
            **({"packs": list(pins)} if pins else {}),
        }
    )


def make_pack(
    root,
    identifier="sample",
    *,
    provides=None,
    requires=(),
    conflicts=(),
    version="1.0.0",
    minimum="0.0.0",
    skills=False,
    checks=(),
):
    root.mkdir(parents=True)
    manifest = {
        "id": identifier,
        "name": identifier,
        "version": version,
        "govkit_min_version": minimum,
        "extension_type": "skills",
        "contract_sets": [],
        "capability_pack": {
            "schema_version": 1,
            "provides": provides or [identifier],
            "requires": list(requires),
            "conflicts": list(conflicts),
            "checks": list(checks),
            "resources": [{"path": "guide.md", "kind": "advisory"}],
        },
    }
    (root / "guide.md").write_text("# Advisory guidance\n")
    if skills:
        manifest["skills"] = [{"path": "skills/help", "install_as": f"{identifier}-help"}]
        (root / "skills/help/references").mkdir(parents=True)
        (root / "skills/help/SKILL.md").write_text(
            "---\nname: help\ndescription: Help with this capability.\n---\nRead [guide](references/guide.md). Pack: {{pack_root}}\n"
        )
        (root / "skills/help/references/guide.md").write_text("Useful reference\n")
    for check in checks:
        path = root / check["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("import sys\nsys.exit(0)\n")
    (root / "manifest.yaml").write_text(yaml.safe_dump(manifest))
    return root


def test_skill_only_and_control_packs_share_one_contract(tmp_path):
    first = load_pack(make_pack(tmp_path / "skill", "skill", skills=True))
    second = load_pack(
        make_pack(
            tmp_path / "control",
            "control",
            checks=[{"id": "quality", "path": "checks/quality.py", "required": True}],
        )
    )
    result = resolve_packs(profile(["skill", "control"]), (second, first), govkit_version="0.21.1")
    assert result.ready
    assert [p.id for p in result.packs] == ["control", "skill"]
    assert result.required_checks == ("quality",)
    assert first.skills[0].install_as == "skill-help"
    assert all(len(p.digest) == 64 for p in result.packs)
    assert (
        result.to_json()
        == resolve_packs(
            profile(["skill", "control"]), (first, second), govkit_version="0.21.1"
        ).to_json()
    )


def test_dependencies_have_reasons_and_are_selected_without_levels(tmp_path):
    base = load_pack(make_pack(tmp_path / "base", "base"))
    feature = load_pack(
        make_pack(
            tmp_path / "feature",
            "feature",
            requires=[
                {"capability": "base", "version": ">=1,<2", "reason": "Shared runtime protocol"}
            ],
        )
    )
    result = resolve_packs(profile(["feature"]), (feature, base), govkit_version="0.21.1")
    assert result.ready
    assert {p.id for p in result.packs} == {"base", "feature"}
    assert result.edges[0].reason == "Shared runtime protocol"
    assert "level" not in result.to_json()


@pytest.mark.parametrize(
    "scenario,code",
    [
        ("missing", "missing-capability"),
        ("cycle", "dependency-cycle"),
        ("conflict", "capability-conflict"),
        ("version", "incompatible-version"),
        ("minimum", "govkit-version"),
        ("ambiguous", "ambiguous-provider"),
    ],
)
def test_invalid_graphs_are_structured_and_never_ready(tmp_path, scenario, code):
    need = {"capability": "base", "version": ">=1,<2", "reason": "Shared runtime"}
    feature = load_pack(
        make_pack(
            tmp_path / "feature",
            "feature",
            requires=[need],
            minimum="99.0.0" if scenario == "minimum" else "0.0.0",
        )
    )
    base_requires = (
        [{"capability": "feature", "version": ">=1", "reason": "Cycle"}]
        if scenario == "cycle"
        else []
    )
    base = load_pack(
        make_pack(
            tmp_path / "base",
            "base",
            version="2.0.0" if scenario == "version" else "1.0.0",
            requires=base_requires,
            conflicts=["feature"] if scenario == "conflict" else [],
        )
    )
    catalog = [feature] if scenario == "missing" else [feature, base]
    if scenario == "ambiguous":
        catalog.append(load_pack(make_pack(tmp_path / "other", "other", provides=["base"])))
    result = resolve_packs(profile(["feature"]), tuple(catalog), govkit_version="0.21.1")
    assert not result.ready
    assert code in {d.code for d in result.decisions}
    assert all(d.message and d.subjects for d in result.decisions)


def test_local_override_requires_explicit_source_version_and_digest_pin(tmp_path):
    bundled = load_pack(make_pack(tmp_path / "bundled", "shared"), source_kind="bundled")
    local_root = make_pack(tmp_path / "local", "shared")
    (local_root / "guide.md").write_text("Project override")
    local = load_pack(local_root)
    assert not resolve_packs(profile(["shared"]), (local, bundled), govkit_version="0.21.1").ready
    selected = profile(
        ["shared"],
        pins=[{"id": "shared", "version": "1.0.0", "digest": local.digest, "source": "local"}],
    )
    result = resolve_packs(selected, (bundled, local), govkit_version="0.21.1")
    assert result.ready and result.packs[0].digest == local.digest
    bad = profile(
        ["shared"],
        pins=[{"id": "shared", "version": "1.0.0", "digest": "0" * 64, "source": "local"}],
    )
    assert not resolve_packs(bad, (bundled, local), govkit_version="0.21.1").ready


@pytest.mark.parametrize(
    "unsafe", ["../outside", "/outside", "C:/outside", "bad\\file", "a/../../outside"]
)
def test_unsafe_manifest_resources_fail_during_loading(tmp_path, unsafe):
    root = make_pack(tmp_path / "sample")
    manifest = yaml.safe_load((root / "manifest.yaml").read_text())
    manifest["capability_pack"]["resources"] = [{"path": unsafe, "kind": "advisory"}]
    (root / "manifest.yaml").write_text(yaml.safe_dump(manifest))
    with pytest.raises(PackError):
        load_pack(root)


def test_missing_and_symlinked_resources_never_enter_catalog(tmp_path):
    root = make_pack(tmp_path / "sample")
    (root / "guide.md").unlink()
    with pytest.raises(PackError, match="guide.md"):
        load_pack(root)
    outside = tmp_path / "outside.md"
    outside.write_text("outside content")
    (root / "guide.md").symlink_to(outside)
    with pytest.raises(PackError, match="symlink"):
        load_pack(root)


def test_policy_required_control_cannot_disappear_with_optional_pack(tmp_path):
    pack = load_pack(make_pack(tmp_path / "sample"))
    result = resolve_packs(
        profile(["sample"], checks=["security"]), (pack,), govkit_version="0.21.1"
    )
    assert not result.ready
    assert result.required_checks == ("security",)
    assert "unavailable-check" in {d.code for d in result.decisions}


def test_graph_resolution_has_no_io_and_does_not_mutate_inputs(tmp_path, monkeypatch):
    pack = load_pack(make_pack(tmp_path / "sample"))
    project = profile(["sample"])

    def forbidden(*args, **kwargs):
        raise AssertionError("Graph resolution attempted I/O")

    with monkeypatch.context() as guard:
        guard.setattr(builtins, "open", forbidden)
        guard.setattr(builtins, "print", forbidden)
        guard.setattr(Path, "open", forbidden)
        guard.setattr(socket, "socket", forbidden)
        first = resolve_packs(project, (pack,), govkit_version="0.21.1").to_json()
        second = resolve_packs(project, (pack,), govkit_version="0.21.1").to_json()
    assert first == second
    assert project.repository.capabilities[0].id == "sample"


def test_all_shipped_packs_and_independent_capability_combinations_resolve():
    catalog = bundled_catalog()
    assert {p.id for p in catalog} >= {
        "otter-skills",
        "llm-evaluation",
        "application-governance",
        "gherkin-delivery",
    }
    for pack in catalog:
        result = resolve_packs(profile([pack.id]), catalog, govkit_version="0.21.1")
        assert result.ready, (pack.id, result.decisions)
    for combination, absent in [
        (["application-governance", "llm-evaluation"], "gherkin-delivery"),
        (["application-governance", "gherkin-delivery"], "llm-evaluation"),
    ]:
        result = resolve_packs(profile(combination), catalog, govkit_version="0.21.1")
        assert result.ready
        assert absent not in {cap for pack in result.packs for cap in pack.provides}


def test_legacy_levels_remain_provenance_not_a_resolution_requirement():
    catalog = bundled_catalog()
    llm = next(p for p in catalog if p.id == "llm-application")
    assert llm.legacy["supported_levels"] == [5]
    assert "model-quality-evaluation" in llm.provides
    result = resolve_packs(profile(["model-quality-evaluation"]), catalog, govkit_version="0.21.1")
    assert result.ready
    assert "gherkin-delivery" not in {c for p in result.packs for c in p.provides}


def test_solver_backtracks_versions_for_shared_dependency_constraints(tmp_path):
    a = load_pack(
        make_pack(
            tmp_path / "a",
            "a",
            requires=[{"capability": "shared", "version": ">=1", "reason": "Runtime"}],
        )
    )
    b = load_pack(
        make_pack(
            tmp_path / "b",
            "b",
            requires=[{"capability": "shared", "version": "<2", "reason": "Compatibility"}],
        )
    )
    old = load_pack(make_pack(tmp_path / "old", "shared", version="1.0.0"))
    new = load_pack(make_pack(tmp_path / "new", "shared", version="2.0.0"))
    result = resolve_packs(profile(["a", "b"]), (new, a, old, b), govkit_version="0.21.1")
    assert result.ready
    assert next(p.version for p in result.packs if p.id == "shared") == "1.0.0"


def test_invalid_explicit_pack_contract_is_not_treated_as_legacy(tmp_path):
    root = make_pack(tmp_path / "sample")
    document = yaml.safe_load((root / "manifest.yaml").read_text())
    document["capability_pack"] = {}
    (root / "manifest.yaml").write_text(yaml.safe_dump(document))
    with pytest.raises(PackError):
        load_pack(root)


def test_pack_named_profile_does_not_collide_with_the_graph_root(tmp_path):
    pack = load_pack(make_pack(tmp_path / "profile", "profile"))
    result = resolve_packs(profile(["profile"]), (pack,), govkit_version="0.21.1")
    assert result.ready, result.decisions
