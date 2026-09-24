"""PR 193 regressions execute real checks and inject filesystem races at I/O seams."""

import json
import os
from pathlib import Path

import pytest

from cli.gate_catalog import compose_catalog
from cli.pack_loading import bundled_catalog, load_pack
from cli.pack_store import apply_install, preview_install
from cli.pipeline_render import parse_settings, render_pipeline
from cli.pipeline_runtime import run_bound
from cli.pipeline_store import apply_pipeline
from cli.profiles import load_profile
from cli.version import GOVKIT_VERSION
from tests.test_capability_packs import make_pack
from tests.test_change_conformance import result
from tests.test_pack_store import snapshot
from tests.test_pipeline_render import settings
from tests.test_pipeline_runtime import fixture
from tests.test_pipeline_store import preview, setup
from tests.test_workflows import request


def conditional_fixture(tmp_path, provider, *, pack=False):
    target, trusted, base, req, _ = fixture(tmp_path, provider)
    identifier = "feature-quality"
    source = trusted / ".govkit/profile.yaml"
    profile = json.loads(source.read_text())
    profile["policy"]["workflows"].append(
        {
            "id": "feature-quality",
            "source": {"reference": "policy.md", "authority": "accepted"},
            "when": ["full-feature"],
            "additional_checks": [identifier],
        }
    )
    catalog = bundled_catalog()
    program = (
        "from pathlib import Path; assert Path('src/service.py').read_text().endswith('changed\\n')"
    )
    arguments = None
    if pack:
        root = make_pack(
            tmp_path / "quality-pack",
            checks=[{"id": identifier, "path": "check.py", "required": False}],
        )
        (root / "check.py").write_text(program + "\n")
        catalog += (load_pack(root),)
        profile["capabilities"].append({"id": "sample"})
        arguments = {identifier: []}
    else:
        config = trusted / "conformance.json"
        doc = json.loads(config.read_text())
        doc["commands"].append(
            {"id": identifier, "argv": ["{python}", "-c", program], "timeout_seconds": 10}
        )
        config.write_text(json.dumps(doc))
    source.write_text(json.dumps(profile))
    apply_install(preview_install(source, trusted, catalog, govkit_version=GOVKIT_VERSION))
    artifact = render_pipeline(
        compose_catalog(load_profile(source), catalog, govkit_version=GOVKIT_VERSION),
        parse_settings(
            settings(execute_checks=["project:tests", identifier, "defect:eligibility"])
        ),
    )
    return target, trusted, base, req, artifact, arguments


@pytest.mark.parametrize("provider", ["github", "azure"])
@pytest.mark.parametrize("pack", [False, True])
def test_fixed_allowlist_supports_applicable_and_inapplicable_workflows(tmp_path, provider, pack):
    target, trusted, base, req, artifact, arguments = conditional_fixture(
        tmp_path, provider, pack=pack
    )
    binding = artifact.document["binding"]
    small = run_bound(binding, target, trusted, req, base, pack_arguments=arguments)
    assert small.exit_code == 0
    assert "feature-quality" not in {r.spec.id for r in small.checks.results}
    req.write_text(json.dumps(request("feature")))
    full = run_bound(binding, target, trusted, req, base, pack_arguments=arguments)
    assert full.exit_code == 0
    assert result(full, "feature-quality").outcome.execution.value == "executed"
    (target / "src/service.py").write_text("# good but fails feature check\n")
    failed = run_bound(binding, target, trusted, req, base, pack_arguments=arguments)
    assert failed.exit_code == 1
    assert result(failed, "feature-quality").outcome.state.value == "fail"


def test_runtime_rejects_replayed_lock_from_another_resolver_version(tmp_path, monkeypatch):
    target, trusted, base, req, _ = fixture(tmp_path)
    upgraded = "0.21.2"
    artifact = render_pipeline(
        compose_catalog(
            load_profile(trusted / ".govkit/profile.yaml"),
            bundled_catalog(),
            govkit_version=upgraded,
        ),
        parse_settings(settings(govkit_version=upgraded, execute_checks=["project:tests"])),
    )
    monkeypatch.setattr("cli.pipeline_runtime.GOVKIT_VERSION", upgraded)
    with pytest.raises(ValueError, match="lock.*runtime pin"):
        run_bound(artifact.document["binding"], target, trusted, req, base)
    apply_install(
        preview_install(
            trusted / ".govkit/profile.yaml", trusted, bundled_catalog(), govkit_version=upgraded
        )
    )
    assert run_bound(artifact.document["binding"], target, trusted, req, base).exit_code == 0


@pytest.mark.parametrize("phase", ["stage", "replace"])
@pytest.mark.parametrize("operation", [0, 1])
def test_generation_cannot_follow_a_parent_swapped_to_an_outside_symlink(
    tmp_path, monkeypatch, phase, operation
):
    source, target, config = setup(tmp_path)
    first = preview(source, target, config)
    apply_pipeline(first, first.digest)
    config.write_text(json.dumps(settings(execute_checks=["project:tests"])))
    proposed = preview(source, target, config)
    destination = target / proposed.operations[operation].path
    original_content = destination.read_bytes()
    outside = tmp_path / "outside"
    outside.mkdir()
    victim = outside / destination.name
    victim.write_bytes(b"unrelated outside file\n")
    parked = destination.parent.with_name("parked-original")
    triggered, stages = False, 0
    escaped_writes = []
    original_open, original_replace = os.open, os.replace

    def swap():
        nonlocal triggered
        triggered = True
        destination.parent.rename(parked)
        destination.parent.symlink_to(outside, target_is_directory=True)

    def opening(name, flags, *args, **kwargs):
        nonlocal stages
        if phase == "stage" and Path(name).name.startswith(".govkit-stage-"):
            if not triggered and stages == operation:
                swap()
            stages += 1
        descriptor = original_open(name, flags, *args, **kwargs)
        if triggered and Path(name).name.startswith(".govkit-stage-"):
            escaped_writes.extend(p.name for p in outside.iterdir() if p != victim)
        return descriptor

    def replacing(src, dest, *args, **kwargs):
        if phase == "replace" and not triggered and Path(dest).name == destination.name:
            # A pathname-based rename can have its source redirected as well.
            staged_bytes = Path(src).read_bytes() if Path(src).is_absolute() else None
            swap()
            if staged_bytes is not None:
                (outside / Path(src).name).write_bytes(staged_bytes)
        value = original_replace(src, dest, *args, **kwargs)
        if victim.read_bytes() != b"unrelated outside file\n":
            escaped_writes.append(victim.name)
        return value

    monkeypatch.setattr(os, "open", opening)
    monkeypatch.setattr(os, "replace", replacing)
    try:
        apply_pipeline(proposed, proposed.digest)
    except (OSError, ValueError):
        pass
    assert triggered
    assert escaped_writes == []
    assert victim.read_bytes() == b"unrelated outside file\n"
    assert (parked / destination.name).read_bytes() == original_content
    assert not list(parked.glob(".govkit-stage-*"))


@pytest.mark.parametrize("pack", [False, True])
def test_applicable_checks_without_execution_opt_in_still_fail(tmp_path, pack):
    target, trusted, base, req, artifact, _ = conditional_fixture(tmp_path, "github", pack=pack)
    binding = artifact.document["binding"]
    binding["execute_checks"].remove("feature-quality")
    req.write_text(json.dumps(request("feature")))
    report = run_bound(binding, target, trusted, req, base)
    assert report.exit_code == 1
    assert result(report, "feature-quality").outcome.execution.value == "not-run"


@pytest.mark.parametrize("identifier", ["unknown-check", "change:scope", "govkit:pack-lock"])
def test_allowlist_does_not_silently_drop_invalid_execution_selections(tmp_path, identifier):
    target, trusted, base, req, artifact = fixture(tmp_path)
    binding = artifact.document["binding"]
    binding["execute_checks"].append(identifier)
    with pytest.raises(ValueError, match="selected configured check"):
        run_bound(binding, target, trusted, req, base)


@pytest.mark.parametrize(
    "arguments", [{"feature-quality": 7}, {"unknown-check": []}, {"feature-quality": [False]}]
)
def test_inapplicable_pack_arguments_are_validated_before_filtering(tmp_path, arguments):
    target, trusted, base, req, artifact, _ = conditional_fixture(tmp_path, "github", pack=True)
    with pytest.raises(ValueError, match="Pack arguments"):
        run_bound(
            artifact.document["binding"], target, trusted, req, base, pack_arguments=arguments
        )


def test_actual_sensitive_scope_activates_full_workflow_check_despite_small_request(tmp_path):
    target, trusted, base, req, artifact, _ = conditional_fixture(tmp_path, "github")
    auth = target / "src/auth/login.py"
    auth.parent.mkdir()
    auth.write_text("# Actual authentication change\n")
    (target / "src/service.py").write_text("# good but fails feature check\n")
    report = run_bound(artifact.document["binding"], target, trusted, req, base)
    assert report.plan.document["workflow"] == "full-feature"
    assert result(report, "feature-quality").outcome.state.value == "fail"
    assert report.exit_code == 1


def test_local_explicit_selection_remains_strict(tmp_path):
    from cli.change_conformance import inspect_change
    from cli.workflows import parse_request

    target, trusted, base, _, artifact, _ = conditional_fixture(tmp_path, "github")
    with pytest.raises(ValueError, match="selected configured check"):
        inspect_change(
            target,
            parse_request(request()),
            base=base,
            policy_target=trusted,
            execute_checks=artifact.document["binding"]["execute_checks"],
        )


def test_generation_refuses_unsafe_platform_fallback_before_writes(tmp_path, monkeypatch):
    source, target, config = setup(tmp_path)
    proposed = preview(source, target, config)
    before = snapshot(target)
    monkeypatch.setattr("cli.pipeline_files.SUPPORTED", False)
    with pytest.raises(ValueError, match="directory-descriptor support"):
        apply_pipeline(proposed, proposed.digest)
    assert snapshot(target) == before


def test_no_follow_directory_open_rejects_swap_after_creation(tmp_path, monkeypatch):
    source, target, config = setup(tmp_path)
    proposed = preview(source, target, config)
    outside = tmp_path / "outside"
    outside.mkdir()
    original = os.open
    destination = target / proposed.artifact.document["path"]
    swapped = False

    def opening(name, flags, *args, **kwargs):
        nonlocal swapped
        if name == destination.parent.name and not swapped:
            swapped = True
            destination.parent.symlink_to(outside, target_is_directory=True)
        return original(name, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", opening)
    with pytest.raises((OSError, ValueError)):
        apply_pipeline(proposed, proposed.digest)
    assert swapped and list(outside.iterdir()) == []


def test_failed_first_install_cleans_bound_files_and_created_directories(tmp_path, monkeypatch):
    source, target, config = setup(tmp_path)
    proposed = preview(source, target, config)
    original, calls = os.replace, 0

    def replacing(src, dest, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected lock write failure")
        return original(src, dest, **kwargs)

    monkeypatch.setattr(os, "replace", replacing)
    with pytest.raises(ValueError, match="lock write failure"):
        apply_pipeline(proposed, proposed.digest)
    assert list(target.iterdir()) == []
