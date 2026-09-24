"""Concrete previews bind source/destination state and never replace user workflows."""

import json
import os

import pytest

from cli.pack_loading import bundled_catalog
from cli.pipeline_store import apply_pipeline, check_pipeline, preview_pipeline
from tests.test_capability_packs import profile
from tests.test_pack_store import snapshot
from tests.test_pipeline_render import settings


def setup(tmp_path):
    target = tmp_path / "consumer"
    target.mkdir()
    source = tmp_path / "profile.json"
    source.write_text(json.dumps(profile(["application-governance"]).document))
    config = tmp_path / "pipeline.json"
    config.write_text(json.dumps(settings()))
    return source, target, config


def preview(source, target, config):
    return preview_pipeline(source, target, config, bundled_catalog())


def test_preview_generate_check_and_repeat_preserve_other_workflows(tmp_path):
    source, target, config = setup(tmp_path)
    existing = target / ".github/workflows/team.yml"
    existing.parent.mkdir(parents=True)
    existing.write_text("# Team workflow\n")
    before = snapshot(target)
    proposed = preview(source, target, config)
    assert snapshot(target) == before
    assert check_pipeline(proposed)["configuration"] == "missing"
    assert check_pipeline(proposed)["execution"] == "unknown"
    with pytest.raises(ValueError, match="digest"):
        apply_pipeline(proposed, "wrong")
    assert snapshot(target) == before
    apply_pipeline(proposed, proposed.digest)
    repeated = preview(source, target, config)
    assert check_pipeline(repeated)["configuration"] == "current"
    assert check_pipeline(repeated)["enforcement"] == "unknown"
    installed = snapshot(target)
    apply_pipeline(repeated, repeated.digest)
    assert snapshot(target) == installed
    assert existing.read_text() == "# Team workflow\n"


@pytest.mark.parametrize("change", ["source", "config", "destination"])
def test_changed_inputs_invalidate_approved_preview_before_any_writes(tmp_path, change):
    source, target, config = setup(tmp_path)
    proposed = preview(source, target, config)
    if change == "source":
        source.write_text(source.read_text() + "\n")
    elif change == "config":
        config.write_text(json.dumps(settings(execute_checks=["project:tests"])))
    else:
        dest = target / proposed.artifact.document["path"]
        dest.parent.mkdir(parents=True)
        dest.write_text("# Existing custom action\n")
    before = snapshot(target)
    with pytest.raises(ValueError, match="[Ss]tale"):
        apply_pipeline(proposed, proposed.digest)
    assert snapshot(target) == before


@pytest.mark.parametrize("managed", [False, True])
def test_existing_or_edited_template_is_protected(tmp_path, managed):
    source, target, config = setup(tmp_path)
    proposed = preview(source, target, config)
    if managed:
        apply_pipeline(proposed, proposed.digest)
    dest = target / proposed.artifact.document["path"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("# User change\n")
    changed = preview(source, target, config)
    assert check_pipeline(changed)["configuration"] == "drifted"
    before = snapshot(target)
    with pytest.raises(ValueError, match="protected"):
        apply_pipeline(changed, changed.digest)
    assert snapshot(target) == before


def test_update_reports_new_opt_ins_and_requires_new_digest(tmp_path):
    source, target, config = setup(tmp_path)
    first = preview(source, target, config)
    apply_pipeline(first, first.digest)
    config.write_text(json.dumps(settings(execute_checks=["project:tests"])))
    updated = preview(source, target, config)
    assert updated.digest != first.digest
    assert {o.action for o in updated.operations} == {"update"}
    assert check_pipeline(updated)["configuration"] == "drifted"
    assert updated.artifact.document["settings"]["execute_checks"] == ["project:tests"]
    apply_pipeline(updated, updated.digest)
    assert check_pipeline(preview(source, target, config))["configuration"] == "current"


def test_symlinked_destination_parent_is_never_written(tmp_path):
    source, target, config = setup(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (target / ".github").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        preview(source, target, config)
    assert list(outside.iterdir()) == []


def test_caught_write_failure_restores_bytes_modes_and_timestamps(tmp_path, monkeypatch):
    source, target, config = setup(tmp_path)
    first = preview(source, target, config)
    apply_pipeline(first, first.digest)
    paths = [target / op.path for op in first.operations]
    for path in paths:
        path.chmod(0o640)
        os.utime(path, ns=(1000000000, 2000000000))
    before = [(p.read_bytes(), p.stat().st_mode, p.stat().st_mtime_ns) for p in paths]
    config.write_text(json.dumps(settings(execute_checks=["project:tests"])))
    updated = preview(source, target, config)
    replace = os.replace
    count = 0

    def fail_second(src, dest, **kwargs):
        nonlocal count
        count += 1
        if count == 2:
            raise OSError("injected write failure")
        return replace(src, dest, **kwargs)

    monkeypatch.setattr("cli.pipeline_files.os.replace", fail_second)
    with pytest.raises(ValueError, match="write failure"):
        apply_pipeline(updated, updated.digest)
    assert [(p.read_bytes(), p.stat().st_mode, p.stat().st_mtime_ns) for p in paths] == before
    assert not list(target.rglob(".govkit-stage-*"))


def test_generation_never_proposes_metadata_too_large_to_read_back(tmp_path):
    source, target, config = setup(tmp_path)
    document = json.loads(source.read_text())
    document["policy"]["workflows"] = [
        {
            "id": "many-controls",
            "source": {"authority": "accepted", "reference": "x" * 450000},
            "when": ["*"],
            "additional_checks": [f"control-{n}" for n in range(12)],
        }
    ]
    source.write_text(json.dumps(document))
    assert source.stat().st_size < 4 * 1024 * 1024
    with pytest.raises(ValueError, match="generated.*large"):
        preview(source, target, config)
    assert list(target.iterdir()) == []
