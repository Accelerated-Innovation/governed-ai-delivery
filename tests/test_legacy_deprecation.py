"""Legacy level-input deprecation boundary (#149).

The maintainer-approved policy: warnings start with 1.0.0; legacy level inputs
(`govkit apply`/`upgrade`, `--level`, `.govkit/marker.json`) stay supported
throughout 1.x and are removed no earlier than 2.0.0, which ships at least six
months and two minor releases after 1.0.0. These tests pin that a user of a
legacy input is told so once per process, that suppression changes nothing
but the notice, and that the replacement paths stay quiet.
"""

import json
import sys
from pathlib import Path

import pytest

from cli.govkit import main
from tests.test_migration import legacy
from tests.test_pack_store import snapshot

ENV = "GOVKIT_NO_LEGACY_WARNING"
REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def armed(monkeypatch):
    from cli import version
    from cli.marker import _reset_legacy_deprecation_warning

    # The notice starts with 1.0.0; pin a release inside the warning period.
    monkeypatch.setattr(version, "GOVKIT_VERSION", "1.0.0")
    monkeypatch.delenv(ENV, raising=False)
    monkeypatch.setenv("GOVKIT_NO_MIGRATION_WARNING", "1")
    _reset_legacy_deprecation_warning()
    yield
    _reset_legacy_deprecation_warning()


def run(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["govkit", *argv])
    try:
        main()
    except SystemExit as exited:
        return exited.code
    return 0


def legacy_apply(monkeypatch, target):
    return run(
        monkeypatch, "apply", "--agent", "claude-code", "--target", str(target),
        "--level", "4", "--type", "api", "--ci", "github", "--stack", "python-fastapi",
    )


def deprecations(err):
    return err.count(ENV)


def test_legacy_apply_announces_the_retirement_boundary(tmp_path, monkeypatch, capsys):
    target = tmp_path / "project"
    target.mkdir()

    assert legacy_apply(monkeypatch, target) == 0

    err = capsys.readouterr().err
    assert "deprecated" in err
    assert "2.0.0" in err
    assert "govkit migrate" in err
    assert deprecations(err) == 1
    assert (target / ".govkit" / "marker.json").is_file()


@pytest.mark.parametrize("flat", [False, True])
def test_reading_a_legacy_marker_warns_once(tmp_path, capsys, flat):
    from cli.marker import read_govkit_marker

    target = legacy(tmp_path, flat=flat)
    first = read_govkit_marker(target)
    read_govkit_marker(target)

    assert first["level"] == "4"
    assert deprecations(capsys.readouterr().err) == 1


def test_level_flag_without_a_marker_warns(tmp_path, monkeypatch, capsys):
    target = tmp_path / "project"
    (target / "features").mkdir(parents=True)

    assert run(monkeypatch, "init", "checkout", "--target", str(target), "--level", "4",
               "--starter", "backend") == 0

    assert (target / "features" / "checkout").is_dir()
    assert deprecations(capsys.readouterr().err) == 1


def test_suppression_removes_only_the_notice(tmp_path, monkeypatch, capsys):
    warned = tmp_path / "warned"
    quiet = tmp_path / "quiet"
    warned.mkdir()
    quiet.mkdir()

    assert legacy_apply(monkeypatch, warned) == 0
    loud = capsys.readouterr()
    monkeypatch.setenv(ENV, "1")
    from cli.marker import _reset_legacy_deprecation_warning

    _reset_legacy_deprecation_warning()
    assert legacy_apply(monkeypatch, quiet) == 0
    silent = capsys.readouterr()

    assert deprecations(loud.err) == 1
    assert deprecations(silent.err) == 0
    assert sorted(snapshot(warned)) == sorted(snapshot(quiet))


def test_replacement_paths_do_not_warn(tmp_path, monkeypatch, capsys):
    from cli.marker import read_govkit_marker

    target = legacy(tmp_path)
    assert run(monkeypatch, "migrate", "--target", str(target), "--json") == 0
    assert json.loads(capsys.readouterr().out)["acceptance"] == "proposed"
    assert read_govkit_marker(tmp_path / "markerless") is None

    assert deprecations(capsys.readouterr().err) == 0


@pytest.mark.parametrize("running", ["0.21.1", "0.99.0"])
def test_releases_before_the_warning_start_stay_quiet(tmp_path, monkeypatch, capsys, running):
    from cli import version
    from cli.marker import read_govkit_marker

    monkeypatch.setattr(version, "GOVKIT_VERSION", running)
    target = legacy(tmp_path)

    assert read_govkit_marker(target)["level"] == "4"
    assert deprecations(capsys.readouterr().err) == 0


def test_detect_dry_run_without_legacy_inputs_stays_quiet(tmp_path, monkeypatch, capsys):
    target = tmp_path / "project"
    target.mkdir()

    assert run(monkeypatch, "apply", "--agent", "claude-code", "--target", str(target),
               "--detect") == 0

    assert not (target / ".govkit").exists()
    assert deprecations(capsys.readouterr().err) == 0


@pytest.mark.parametrize("command", ["verify-authority", "verify-contract"])
def test_authority_checks_reading_the_marker_warn(tmp_path, monkeypatch, capsys, command):
    target = legacy(tmp_path)
    baseline = tmp_path / "baseline.json"
    baseline.write_text("{}", encoding="utf-8")

    extra = ["--baseline", str(baseline)] if command == "verify-authority" else []
    run(monkeypatch, command, "--target", str(target), *extra)

    assert deprecations(capsys.readouterr().err) == 1


def test_authority_checks_without_a_marker_stay_quiet(tmp_path, monkeypatch, capsys):
    target = tmp_path / "project"
    target.mkdir()
    baseline = tmp_path / "baseline.json"
    baseline.write_text("{}", encoding="utf-8")

    assert run(monkeypatch, "verify-authority", "--target", str(target),
               "--baseline", str(baseline)) == 0

    assert deprecations(capsys.readouterr().err) == 0


ANNOUNCEMENTS = ("README.md", "CHANGELOG.md", "docs/LEGACY_MIGRATION.md")
GUIDES = (
    "README.md",
    "GOVKIT_TUTORIAL.md",
    "docs/CAPABILITY_ONBOARDING.md",
    "docs/LEGACY_MIGRATION.md",
)


@pytest.mark.parametrize("name", ANNOUNCEMENTS)
def test_announcements_state_the_same_boundary(name):
    text = (REPO / name).read_text(encoding="utf-8")

    for fact in ("1.0.0", "2.0.0", "six months", "two minor releases", ENV):
        assert fact in text, f"{name} omits {fact!r}"


@pytest.mark.parametrize("name", GUIDES)
def test_guides_no_longer_claim_an_unannounced_boundary(name):
    text = " ".join((REPO / name).read_text(encoding="utf-8").split())

    assert "warning period has been announced" not in text
