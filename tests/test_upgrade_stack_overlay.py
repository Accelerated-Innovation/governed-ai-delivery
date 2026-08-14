"""`govkit upgrade` must not revert a team's stack to the bundled baseline.

Issue #132, reported as "the `govkit:editable` guard misses local edits after a
baseline key rename". There is no rename, and the guard is not broken: it is
that **`cmd_upgrade` never knew about stacks**.

Six architecture docs vary by stack. They ship from `cli/stacks/<id>/` and are
installed by `apply_overlay`, which stamps `baseline: <stack>@<version>`. They
also live under `docs/<area>/architecture/`, which every manifest declares as a
`governed` path — and `upgrade` re-installs governed contracts with
`skip_existing=False`. So upgrade overwrote each one with the stack-agnostic
copy and re-stamped it `baseline: govkit@<version>`, which is exactly the
header transition the issue reports.

`apply` escapes this because it copies governed paths with `skip_existing=True`,
so the overlay it wrote moments earlier is left alone. Only upgrade clobbers.

Two consequences, in ascending order of severity:

1. **The baseline key is falsified.** `doctor`'s D006 only checks non-`govkit@`
   baselines, so after one upgrade it stops reporting stale overlays entirely —
   the check silently goes blind.
2. **The content reverts.** Every stack except `python-fastapi` ships genuinely
   different docs, so a Go, .NET, JVM or Node team's architecture contracts
   become Python/FastAPI ones. `python-fastapi` is the exception only because
   its content *is* the baseline, which is why the issue reporter saw the
   baseline key change while the body hash stayed identical.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from cli.cmd_upgrade import cmd_upgrade
from cli.headers import parse_editable_header
from cli.overlay import list_overlays

REPO_ROOT = Path(__file__).resolve().parent.parent

STACK_DOC = "docs/backend/architecture/TECH_STACK.md"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class TestPremise:
    """Guard the premise. If overlays stopped differing from the baseline, the
    behavioral tests below would pass while proving nothing."""

    def test_overlays_ship_docs_that_differ_from_the_stack_agnostic_baseline(self):
        differing = {}
        for overlay in list_overlays():
            for doc in overlay.docs:
                src = overlay.root / doc["src"]
                dest = REPO_ROOT / doc["dest"]
                if not src.is_file() or not dest.is_file():
                    continue
                if _sha(src.read_text(encoding="utf-8")) != _sha(
                    dest.read_text(encoding="utf-8")
                ):
                    differing.setdefault(overlay.id, []).append(doc["dest"])
        assert differing, (
            "no bundled overlay differs from the baseline docs — the revert this "
            "module tests would be undetectable"
        )

    def test_the_stack_docs_live_under_a_governed_path(self):
        """The overlap that causes the clobber: an overlay writes into a
        directory the manifest hands to upgrade as a governed contract."""
        from cli.manifest import load_manifest, resolve_variant_files

        _files, _shared, governed = resolve_variant_files(
            load_manifest("claude-code"),
            {"level": "4", "type": "api", "ci": "github", "stack": "go-gin"},
        )
        assert any(
            STACK_DOC.startswith(entry) for entry in governed
        ), governed


def _make_repo(tmp_path: Path) -> Path:
    """A minimal bundle: one agent, one governed docs/ tree, one stack overlay
    whose doc is deliberately different from the baseline copy."""
    repo = tmp_path / "repo"
    agents = repo / "agents" / "test-agent"
    agents.mkdir(parents=True)
    (agents / "CLAUDE.md").write_text("# agent v2\n", encoding="utf-8")
    (agents / "manifest.json").write_text(
        json.dumps({
            "agent": "test-agent",
            "description": "stack upgrade test agent",
            "options": {
                "level": {"prompt": "Level?", "choices": ["4"], "default": "4"},
                "type": {"prompt": "Type?", "choices": ["api"], "default": "api"},
                "ci": {"prompt": "CI?", "choices": ["github"], "default": "github"},
                "stack": {"choices": ["test-stack"], "default": "test-stack"},
            },
            "variants": {
                "type": {
                    "api": {
                        "files": [{"src": "CLAUDE.md", "dest": "CLAUDE.md"}],
                        "shared": [],
                        "governed": ["docs/backend/architecture/"],
                    },
                },
                "ci": {"github": {"files": [], "shared": [], "governed": []}},
            },
            "base_files": [],
        }),
        encoding="utf-8",
    )

    baseline = repo / STACK_DOC
    baseline.parent.mkdir(parents=True)
    baseline.write_text("# Tech Stack\n\nBASELINE CONTENT (stack-agnostic)\n", encoding="utf-8")

    stack = repo / "stacks" / "test-stack"
    stack.mkdir(parents=True)
    (stack / "TECH_STACK.md").write_text(
        "# Tech Stack\n\nSTACK CONTENT (test-stack only)\n", encoding="utf-8",
    )
    (stack / "overlay.yaml").write_text(
        yaml.safe_dump({
            "id": "test-stack",
            "version": "0.10.0",
            "display_name": "Test Stack",
            "docs": [{"src": "TECH_STACK.md", "dest": STACK_DOC}],
        }),
        encoding="utf-8",
    )
    return repo


def _make_target(tmp_path: Path, repo: Path) -> Path:
    """A target as `apply --stack test-stack` would leave it: the overlay's doc
    installed, carrying the overlay's own baseline header."""
    from cli.overlay import load_overlay, apply_overlay

    target = tmp_path / "project"
    target.mkdir()
    (target / "CLAUDE.md").write_text("# agent v1\n", encoding="utf-8")
    overlay = load_overlay("test-stack")
    assert overlay is not None, "test fixture overlay did not load"
    apply_overlay(overlay, target)

    (target / ".govkit").mkdir()
    (target / ".govkit" / "marker.json").write_text(
        json.dumps({
            "version": "0.1.0",
            "level": "4",
            "agent": "test-agent",
            "options": {"type": "api", "ci": "github", "stack": "test-stack"},
            "stack": {"id": "test-stack", "version": "0.10.0"},
            "applied_at": "2026-01-01T00:00:00+00:00",
        }),
        encoding="utf-8",
    )
    return target


@pytest.fixture()
def bundle(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    monkeypatch.setattr("cli.paths.AGENTS_DIR", repo / "agents")
    monkeypatch.setattr("cli.paths.REPO_ROOT", repo)
    monkeypatch.setattr("cli.overlay.STACKS_DIR", repo / "stacks")
    monkeypatch.setattr("cli.version.GOVKIT_VERSION", "0.2.0")
    return repo


class TestUpgradePreservesTheStack:
    def test_the_fixture_starts_on_the_stack_doc(self, bundle, tmp_path):
        """Non-vacuous guard: if apply_overlay stopped installing, the assertions
        below would be checking an empty file."""
        target = _make_target(tmp_path, bundle)
        text = (target / STACK_DOC).read_text(encoding="utf-8")
        assert "STACK CONTENT" in text
        assert parse_editable_header(text)["baseline"] == "test-stack@0.10.0"

    def test_upgrade_keeps_the_stack_content(self, bundle, tmp_path):
        """The severe half of #132: a Go/.NET/JVM/Node team's architecture
        contracts silently became Python/FastAPI ones on upgrade."""
        target = _make_target(tmp_path, bundle)
        cmd_upgrade(argparse.Namespace(target=str(target), force=False))

        text = (target / STACK_DOC).read_text(encoding="utf-8")
        assert "STACK CONTENT" in text, (
            "upgrade reverted the stack doc to the stack-agnostic baseline"
        )
        assert "BASELINE CONTENT" not in text

    def test_upgrade_keeps_the_stack_baseline_header(self, bundle, tmp_path):
        """The half the issue actually observed. It also matters on its own:
        doctor's D006 skips `govkit@` baselines, so a falsified key means stale
        overlays stop being reported at all."""
        target = _make_target(tmp_path, bundle)
        cmd_upgrade(argparse.Namespace(target=str(target), force=False))

        header = parse_editable_header((target / STACK_DOC).read_text(encoding="utf-8"))
        assert header["baseline"] == "test-stack@0.10.0", (
            f"baseline became {header['baseline']!r} — doctor's D006 only checks "
            "non-govkit baselines, so it would now skip this doc entirely"
        )

    def test_the_recorded_hash_still_describes_the_installed_body(
        self, bundle, tmp_path,
    ):
        """Whatever upgrade leaves behind, the header must describe it — or the
        next run's edit-protection compares against a body that was never there."""
        from cli.headers import compute_body_hash

        target = _make_target(tmp_path, bundle)
        cmd_upgrade(argparse.Namespace(target=str(target), force=False))

        text = (target / STACK_DOC).read_text(encoding="utf-8")
        assert parse_editable_header(text)["hash"] == compute_body_hash(text)

    def test_a_user_edited_stack_doc_is_still_refused(self, bundle, tmp_path, capsys):
        """Restoring the overlay must not become a second way to lose edits."""
        target = _make_target(tmp_path, bundle)
        doc = target / STACK_DOC
        doc.write_text(
            doc.read_text(encoding="utf-8") + "\n## Our own section\n", encoding="utf-8",
        )

        cmd_upgrade(argparse.Namespace(target=str(target), force=False))

        text = doc.read_text(encoding="utf-8")
        assert "Our own section" in text, "upgrade destroyed a user edit"
        assert "refused" in capsys.readouterr().err

    def test_force_still_reinstates_the_stack_doc_not_the_baseline(
        self, bundle, tmp_path,
    ):
        """--force means 'overwrite my edits with what govkit ships'. What
        govkit ships for this repo is the stack's doc."""
        target = _make_target(tmp_path, bundle)
        doc = target / STACK_DOC
        doc.write_text(
            doc.read_text(encoding="utf-8") + "\n## Our own section\n", encoding="utf-8",
        )

        cmd_upgrade(argparse.Namespace(target=str(target), force=True))

        text = doc.read_text(encoding="utf-8")
        assert "STACK CONTENT" in text
        assert "BASELINE CONTENT" not in text
        assert "Our own section" not in text

    def test_a_stackless_install_is_unaffected(self, bundle, tmp_path):
        """Repos that never chose a stack must see no change in behavior."""
        target = _make_target(tmp_path, bundle)
        marker_path = target / ".govkit" / "marker.json"
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        del marker["stack"]
        marker["options"].pop("stack", None)
        marker_path.write_text(json.dumps(marker), encoding="utf-8")

        cmd_upgrade(argparse.Namespace(target=str(target), force=False))

        text = (target / STACK_DOC).read_text(encoding="utf-8")
        assert "BASELINE CONTENT" in text
        assert parse_editable_header(text)["baseline"] == "govkit@0.2.0"

    def test_an_unknown_stack_is_reported_rather_than_left_silent(
        self, bundle, tmp_path, capsys,
    ):
        """Degrading to the baseline is the only thing upgrade can do, but doing
        it quietly would swap a team's architecture contracts without telling
        them."""
        target = _make_target(tmp_path, bundle)
        marker_path = target / ".govkit" / "marker.json"
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        marker["stack"] = {"id": "stack-that-was-removed", "version": "9.9.9"}
        marker_path.write_text(json.dumps(marker), encoding="utf-8")

        cmd_upgrade(argparse.Namespace(target=str(target), force=False))

        err = capsys.readouterr().err
        assert "stack-that-was-removed" in err and "does not bundle" in err, err

    def test_an_unknown_stack_id_does_not_crash_the_upgrade(self, bundle, tmp_path):
        """A marker naming a stack this govkit no longer bundles must degrade to
        the baseline rather than raising."""
        target = _make_target(tmp_path, bundle)
        marker_path = target / ".govkit" / "marker.json"
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        marker["stack"] = {"id": "stack-that-was-removed", "version": "9.9.9"}
        marker_path.write_text(json.dumps(marker), encoding="utf-8")

        cmd_upgrade(argparse.Namespace(target=str(target), force=False))

        assert (target / STACK_DOC).is_file()


class TestWhyTheBaselineKeyMatters:
    """D006 is the reason the falsified key was more than cosmetic.

    `_check_baseline_staleness` skips any `govkit@<version>` baseline, because
    that tracks the govkit version rather than an overlay version. So once
    upgrade re-stamped every stack doc `govkit@…`, the stale-overlay check had
    nothing left to inspect and reported nothing — permanently, for the life of
    the repo. These tests run the real check both ways so that claim is
    enforced rather than asserted in a comment.
    """

    def _target_with_baseline(self, tmp_path: Path, baseline: str) -> Path:
        from cli.headers import format_editable_header

        target = tmp_path / "proj"
        doc = target / STACK_DOC
        doc.parent.mkdir(parents=True)
        doc.write_text(
            format_editable_header(baseline=baseline) + "# Tech Stack\n",
            encoding="utf-8",
        )
        return target

    def _findings(self, target: Path):
        from cli.doctor import _check_baseline_staleness

        return _check_baseline_staleness(target, {})

    def test_a_stale_overlay_baseline_is_reported(self, tmp_path):
        """Guard the premise: with the overlay's own key, D006 works."""
        overlays = [o for o in list_overlays() if o.version != "0.0.0"]
        assert overlays, "no bundled overlays to test against"
        stack = overlays[0]
        target = self._target_with_baseline(tmp_path, f"{stack.id}@0.0.1")
        findings = self._findings(target)
        assert [f.id for f in findings] == ["D006"], findings

    def test_a_govkit_baseline_is_never_inspected(self, tmp_path):
        """What upgrade used to write. Same stale doc, no finding."""
        target = self._target_with_baseline(tmp_path, "govkit@0.15.0")
        assert self._findings(target) == []
