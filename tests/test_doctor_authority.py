"""`doctor` says which authority mode a project is in — increment 11 follow-up.

The dangerous state is not "no PDG" — that is the default and it is fine. It
is a project whose owners believe it verifies and which silently does not,
because the check then reports *not applicable* and exits zero while looking
like a pass. Nothing surfaced the mode, so nothing would have told them.
"""

from __future__ import annotations

import json

import pytest

from cli.doctor import _authority_line, _print_findings, run_doctor


@pytest.fixture
def project(tmp_path):
    (tmp_path / ".govkit").mkdir()
    (tmp_path / ".govkit" / "marker.json").write_text(json.dumps({
        "version": "0.20.0", "level": "4", "agent": "claude-code",
        "options": {"type": "api", "ci": "github", "stack": "python-fastapi"},
    }), encoding="utf-8")
    return tmp_path


def report(target, capsys) -> str:
    """The printed report, which is what a person actually reads."""
    _print_findings(target, run_doctor(target))
    return capsys.readouterr().out


def test_a_project_without_a_pdg_says_so_plainly(project, capsys):
    """Reported, not warned about. Having no PDG is the default and the
    common case, and dressing it as a finding would train people to ignore
    the line that matters."""
    out = report(project, capsys)

    assert "authority" in out.lower()
    assert "none" in out.lower()


def test_a_pdg_enabled_project_says_so(project, capsys):
    marker = json.loads((project / ".govkit" / "marker.json").read_text())
    marker["authority"] = {"source": "pdg"}
    (project / ".govkit" / "marker.json").write_text(json.dumps(marker), encoding="utf-8")

    out = report(project, capsys)

    assert "pdg" in out.lower()


# ---------------------------------------------------------------------------
# A marker that parses but is not shaped like a marker
# ---------------------------------------------------------------------------


def test_a_marker_whose_authority_is_not_an_object_does_not_stop_the_report(project, capsys):
    """`{"authority": "pdg"}` is the shape someone writes by hand when they
    read the docs quickly. It is valid JSON, it survives the earlier checks,
    and calling `.get()` on the string killed `doctor` before it printed
    anything — turning a malformed field into the loss of the whole report,
    including the findings that would have explained it.
    """
    marker = json.loads((project / ".govkit" / "marker.json").read_text())
    marker["authority"] = "pdg"
    (project / ".govkit" / "marker.json").write_text(json.dumps(marker), encoding="utf-8")

    out = report(project, capsys)

    assert "authority" in out.lower()
    assert "unknown" in out.lower() or "none" in out.lower()


def test_a_marker_that_is_json_but_not_an_object_does_not_stop_the_report(tmp_path):
    """A top-level list or string parses fine and has no `.get()`. The mode
    is then genuinely unknown, which is what it should say — not the default
    of `none`, which would read as "checked, and you have no PDG"."""
    (tmp_path / ".govkit").mkdir()
    (tmp_path / ".govkit" / "marker.json").write_text('["not", "a", "marker"]', encoding="utf-8")

    line = _authority_line(tmp_path)

    assert "unknown" in line.lower()


def test_an_authority_block_without_a_source_is_not_a_pdg_project(project, capsys):
    """`{"authority": {}}` says nothing about a PDG, and the absent default
    is `none`."""
    marker = json.loads((project / ".govkit" / "marker.json").read_text())
    marker["authority"] = {}
    (project / ".govkit" / "marker.json").write_text(json.dumps(marker), encoding="utf-8")

    out = report(project, capsys)

    assert "authority: none" in out.lower()
