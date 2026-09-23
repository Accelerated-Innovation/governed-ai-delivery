"""PR 185 regressions: comparable coverage, preview isolation and reference bounds."""

import json

import pytest

from cli.discovery import discover, load_baseline
from cli.discovery_scan import DiscoveryLimits, scan_repository
from cli.pack_loading import bundled_catalog
from cli.pack_store import apply_install, preview_install
from cli.profile_store import apply_profile, preview_materialization
from cli.version import GOVKIT_VERSION
from tests.test_cmd_discover import invoke
from tests.test_discovery import accepted_profile, observations, write
from tests.test_pack_store import snapshot


def test_incomplete_baseline_cannot_establish_removal_from_complete_current_scan(tmp_path):
    target = tmp_path / "consumer"
    target.mkdir()
    removed = write(target, "src/old.py", "import mcp\n")
    oversized = write(target, "README.md", "x" * 65)
    limits = DiscoveryLimits(max_bytes=64)
    original = discover(target, limits=limits)
    assert not original.document["coverage"]["complete"]
    assert observations(original)["src/old.py"]["status"] == "observed"
    record = write(tmp_path, "baseline.json", original.to_json())
    prior = load_baseline(record)
    removed.unlink()
    oversized.write_text("# Short\n")
    before = snapshot(target)
    current = discover(target, limits=limits, baseline=prior)
    assert current.document["coverage"]["complete"]
    change = next(c for c in current.document["changes"] if c["source"] == "src/old.py")
    assert change["kind"] == "unavailable"
    assert not any(f.code == "observation-removed" for f in current.maintenance_outcome().findings)
    assert snapshot(target) == before


def break_install(target, source, kind):
    if kind == "malformed-lock":
        write(target, ".govkit/pack-lock.json", "{}")
    elif kind in {"inconsistent-lock", "missing-resource"}:
        apply_profile(preview_materialization(source, target))
        apply_install(
            preview_install(source, target, bundled_catalog(), govkit_version=GOVKIT_VERSION)
        )
        if kind == "inconsistent-lock":
            path = target / ".govkit/pack-lock.json"
            lock = json.loads(path.read_text())
            lock["govkit_version"] = "not-a-version"
            path.write_text(json.dumps(lock))
        else:
            next((target / ".govkit/packs").glob("*/*/manifest.yaml")).unlink()
    elif kind == "symlink-destination":
        outside = write(target.parent, "external-skill.md", "Do not replace")
        skill = target / ".agents/skills/llm-evaluation/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.symlink_to(outside)
    elif kind == "parent-is-file":
        write(target, ".agents/skills", "Project-owned content")
    elif kind == "destination-is-directory":
        (target / ".agents/skills/llm-evaluation/SKILL.md").mkdir(parents=True)
    else:
        raise AssertionError(kind)


@pytest.mark.parametrize(
    "kind",
    [
        "malformed-lock",
        "inconsistent-lock",
        "missing-resource",
        "symlink-destination",
        "parent-is-file",
        "destination-is-directory",
    ],
)
def test_pack_errors_preserve_cli_discovery_and_scope_installation_block(
    tmp_path, monkeypatch, capsys, kind
):
    target = tmp_path / "consumer"
    target.mkdir()
    source = accepted_profile(target)
    break_install(target, source, kind)
    before = snapshot(target)
    assert invoke(monkeypatch, ["--target", str(target), "--profile", str(source), "--json"]) == 0
    captured = capsys.readouterr()
    assert not captured.err
    report = json.loads(captured.out)
    assert report["accepted_profile"] == json.loads(source.read_text())
    assert not report["install_ready"] and not report["operations"]
    assert any(
        o["source"] == "design/architecture.md" and o["digest"] for o in report["observations"]
    )
    blocked = next(d for d in report["review"] if d["id"] == "install:preview-unavailable")
    assert blocked["affects"] == ["installation"]
    assert snapshot(target) == before


class ReferenceStream:
    """A lazy input boundary that rejects reads past the inspection budget."""

    def __init__(self, allowed, *, duplicate=False):
        self.allowed = allowed
        self.duplicate = duplicate
        self.consumed = 0

    def __iter__(self):
        for number in range(self.allowed):
            self.consumed += 1
            yield "README.md" if self.duplicate else f"ref-{number}.txt"
        raise AssertionError("Reference input was consumed past the configured budget")


@pytest.mark.parametrize("entrypoint", ["scan", "discover"])
@pytest.mark.parametrize("duplicate", [False, True])
def test_reference_collection_stops_before_materializing_or_sorting_unbounded_inputs(
    tmp_path, entrypoint, duplicate
):
    for relative in ("README.md", "ref-0.txt", "ref-1.txt"):
        write(tmp_path, relative, "# Evidence\n")
    limits = DiscoveryLimits(max_files=2, max_entries=4)
    references = ReferenceStream(5 if duplicate else 3, duplicate=duplicate)
    if entrypoint == "scan":
        scan = scan_repository(tmp_path, references=references, limits=limits)
        observed, selected, complete, limitations = (
            scan.observations,
            scan.references,
            scan.complete,
            scan.limitations,
        )
    else:
        report = discover(tmp_path, references=references, limits=limits).document
        observed, selected = report["observations"], report["references"]
        complete, limitations = report["coverage"]["complete"], report["coverage"]["limitations"]
    assert references.consumed <= references.allowed
    assert len(observed) <= limits.max_files
    assert len(selected) <= limits.max_files
    assert not complete and "reference-limit" in limitations


def test_accepted_references_share_the_bounded_scan_budget(tmp_path):
    source = accepted_profile(tmp_path)
    profile = json.loads(source.read_text())
    profile["policy"]["contracts"] = [
        {
            "source": {"reference": f"contracts/{index}.txt", "authority": "accepted"},
            "scope": ["src"],
        }
        for index in range(30)
    ]
    source.write_text(json.dumps(profile))
    before = snapshot(tmp_path)
    report = discover(tmp_path, profile_path=source, limits=DiscoveryLimits(max_files=3))
    assert len(report.document["references"]) <= 3
    assert "reference-limit" in report.document["coverage"]["limitations"]
    assert report.document["accepted_profile"] == profile
    assert snapshot(tmp_path) == before


def test_reference_budget_boundary_deduplicates_and_remains_deterministic(tmp_path):
    for name in ("a.txt", "b.txt"):
        write(tmp_path, name, "existing evidence")
    limits = DiscoveryLimits(max_files=2, max_entries=4)
    first = discover(tmp_path, references=("b.txt", "a.txt", "a.txt"), limits=limits)
    second = discover(tmp_path, references=("a.txt", "b.txt"), limits=limits)
    assert first.document["coverage"]["complete"]
    assert first.document["references"] == ["a.txt", "b.txt"]
    assert first.to_json() == second.to_json()
