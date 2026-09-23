"""PR 186 regressions: native names, verified snapshots and combined scope limits."""

import json
from pathlib import Path

import pytest

from cli.agent_layout import AGENT_LAYOUTS
from cli.pack_store import verified_lock_document
from cli.workflow_store import load_workflow_plan
from tests.test_discovery import write
from tests.test_pack_store import snapshot
from tests.test_workflows import install, plan, request


@pytest.mark.parametrize("agent", ["codex", "claude-code", "copilot"])
def test_user_request_planning_skill_does_not_block_namespaced_pack(tmp_path, agent):
    relative = f"{AGENT_LAYOUTS[agent].skills_dir}/request-planning/SKILL.md"
    user_skill = write(tmp_path, relative, "# User-owned request planning\n")
    original = (user_skill.read_bytes(), user_skill.stat().st_mtime_ns)
    install(tmp_path, agent=agent)
    assert (user_skill.read_bytes(), user_skill.stat().st_mtime_ns) == original
    report = plan(tmp_path, request())
    guidance = next(g for g in report.document["guidance"] if g["id"] == "govkit-request-planning")
    assert guidance["path"] == f"{AGENT_LAYOUTS[agent].skills_dir}/govkit-request-planning/SKILL.md"
    assert report.ready and (tmp_path / guidance["path"]).is_file()


@pytest.mark.parametrize("observed_count", [192, 193, 256])
def test_all_valid_combined_scope_paths_are_retained_and_replayable(tmp_path, observed_count):
    install(tmp_path)
    document = request("feature")
    document["scope"] = [f"src/declared-{index}" for index in range(64)]
    observed = {
        "schema_version": 1,
        "paths": [f"src/observed-{index}" for index in range(observed_count)],
        "impacts": {"auth": True},
    }
    before = snapshot(tmp_path)
    original = plan(tmp_path, document)
    result = plan(tmp_path, document, observed_scope=observed, previous=original)
    expected = sorted(document["scope"] + observed["paths"])
    assert result.ready and result.document["scope"] == expected
    assert all(c["scope"] == expected for c in result.document["checks"])
    assert "review:auth" in {c["id"] for c in result.document["checks"]}
    assert result.document["reassessment"]["required"]
    assert snapshot(tmp_path) == before
    record = write(tmp_path.parent, f"{observed_count}-plan.json", result.to_json())
    assert load_workflow_plan(record).document == result.document


def replacement_metadata(target):
    """A different valid profile/lock with identical pinned resources."""
    profile_path, lock_path = target / ".govkit/profile.yaml", target / ".govkit/pack-lock.json"
    from cli.pack_loading import bundled_catalog
    from cli.pack_store import apply_install, preview_install
    from cli.version import GOVKIT_VERSION

    original = (profile_path.read_bytes(), lock_path.read_bytes())
    profile = json.loads(original[0])
    profile["repository"]["id"] = "replacement-repository"
    profile_path.write_text(json.dumps(profile))
    apply_install(
        preview_install(profile_path, target, bundled_catalog(), govkit_version=GOVKIT_VERSION)
    )
    replacement = (profile_path.read_bytes(), lock_path.read_bytes())
    profile_path.write_bytes(original[0])
    lock_path.write_bytes(original[1])
    return replacement


def test_verified_document_is_the_snapshot_whose_resources_were_checked(tmp_path, monkeypatch):
    profile = install(tmp_path)
    replacement_profile, replacement_lock = replacement_metadata(tmp_path)
    lock_path = tmp_path / ".govkit/pack-lock.json"
    original_lock = json.loads(lock_path.read_text())
    native = next(
        p for p in original_lock["files"] if p.startswith(".agents/") and p.endswith("SKILL.md")
    )
    original_read = Path.read_text
    reads = 0

    def replace_on_unverified_reread(path, *args, **kwargs):
        nonlocal reads
        if path == lock_path:
            reads += 1
            if reads == 2:
                # The lock is internally valid, but this newer state has native
                # drift and was never checked by the first verification.
                (tmp_path / ".govkit/profile.yaml").write_bytes(replacement_profile)
                lock_path.write_bytes(replacement_lock)
                (tmp_path / native).write_text("changed native guidance")
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", replace_on_unverified_reread)
    verified = verified_lock_document(tmp_path)
    assert verified == original_lock
    assert verified["profile_digest"] == profile.digest


def test_plan_rejects_different_profile_between_capture_and_lock_verification(
    tmp_path, monkeypatch
):
    install(tmp_path)
    replacement_profile, replacement_lock = replacement_metadata(tmp_path)
    profile_path = tmp_path / ".govkit/profile.yaml"
    original_read = Path.read_text
    replaced = False

    def replace_after_initial_profile(path, *args, **kwargs):
        nonlocal replaced
        value = original_read(path, *args, **kwargs)
        if path == profile_path and not replaced:
            replaced = True
            profile_path.write_bytes(replacement_profile)
            (tmp_path / ".govkit/pack-lock.json").write_bytes(replacement_lock)
        return value

    monkeypatch.setattr(Path, "read_text", replace_after_initial_profile)
    report = plan(tmp_path, request())
    assert replaced and not report.ready
    assert not report.document["guidance"]
    assert any(d["code"] == "unavailable-lock" for d in report.document["decisions"])
