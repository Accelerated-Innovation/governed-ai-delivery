"""Codex path-scoped rule destinations follow the repo's real source root.

claude-code and copilot scope their backend rules with layout-agnostic
globs (`**/services/**`), expanded from skill_context.layers at install
time. Codex has no rules directory — it places an `AGENTS.md` inside each
layer folder, because codex resolves AGENTS.md from the edited file
upward. That destination was hardcoded root-relative, so a repo laid out
the way REPO_STRUCTURE_README.md prescribes (`src/<package>/services/`)
got an empty root-level `services/` holding guidance codex would never
apply to the real code.

These tests pin the destination to the detected source root, with today's
root-relative path kept as the fallback so no existing install regresses.
"""

import argparse

import pytest

BACKEND_LAYERS = ("api", "ports", "services", "models", "adapters", "common")


def _apply_codex(target, **overrides):
    from cli.cmd_apply import cmd_apply

    kwargs = dict(
        agent="codex", target=str(target), level="4", type="api",
        ci="github", stack=None, force=False, detect=False,
    )
    kwargs.update(overrides)
    cmd_apply(argparse.Namespace(**kwargs))


class TestDetectSourceRoot:
    def test_flat_layout_reports_no_prefix(self, tmp_path):
        """Layers directly under the target need no prefix."""
        from cli.detect import detect_source_root

        for layer in BACKEND_LAYERS:
            (tmp_path / layer).mkdir(parents=True)
        assert detect_source_root(tmp_path) == ""

    def test_src_layout_reports_src(self, tmp_path):
        from cli.detect import detect_source_root

        for layer in BACKEND_LAYERS:
            (tmp_path / "src" / layer).mkdir(parents=True)
        assert detect_source_root(tmp_path) == "src"

    def test_documented_package_layout_reports_the_package(self, tmp_path):
        from cli.detect import detect_source_root

        for layer in BACKEND_LAYERS:
            (tmp_path / "src" / "mypkg" / layer).mkdir(parents=True)
        assert detect_source_root(tmp_path) == "src/mypkg"

    def test_unknown_layout_reports_no_prefix(self, tmp_path):
        """An empty or unrecognisable repo falls back to root-relative."""
        from cli.detect import detect_source_root

        (tmp_path / "docs").mkdir()
        assert detect_source_root(tmp_path) == ""

    def test_multi_service_layout_reports_no_prefix(self, tmp_path):
        """Several service packages have no single source root, so codex
        rules stay root-relative rather than guessing one service."""
        from cli.detect import detect_source_root

        for svc in ("orders", "billing"):
            for layer in BACKEND_LAYERS:
                (tmp_path / "src" / svc / layer).mkdir(parents=True)
        assert detect_source_root(tmp_path) == ""


class TestCodexRulePlacement:
    def test_rules_land_under_the_detected_source_root(self, tmp_path):
        target = tmp_path / "project"
        target.mkdir()
        for layer in BACKEND_LAYERS:
            (target / "src" / "mypkg" / layer).mkdir(parents=True)

        _apply_codex(target)

        assert (target / "src" / "mypkg" / "services" / "AGENTS.md").is_file()
        assert not (target / "services").exists(), (
            "root-level services/ created despite code living at src/mypkg/"
        )

    def test_flat_layout_still_installs_root_relative(self, tmp_path):
        """Regression guard: repos whose layers sit at the target root keep
        exactly today's destinations."""
        target = tmp_path / "project"
        target.mkdir()
        for layer in BACKEND_LAYERS:
            (target / layer).mkdir(parents=True)

        _apply_codex(target)

        assert (target / "services" / "AGENTS.md").is_file()

    def test_unknown_layout_falls_back_to_root_relative(self, tmp_path):
        """A greenfield repo with no source tree yet installs as before."""
        target = tmp_path / "project"
        target.mkdir()

        _apply_codex(target)

        assert (target / "services" / "AGENTS.md").is_file()

    def test_user_content_outside_the_govkit_block_survives(self, tmp_path):
        """Placement must not disturb the merge semantics: an AGENTS.md the
        team already wrote keeps its content, with govkit's governance
        appended in a delimited block."""
        target = tmp_path / "project"
        target.mkdir()
        for layer in BACKEND_LAYERS:
            (target / "src" / "mypkg" / layer).mkdir(parents=True)
        existing = target / "src" / "mypkg" / "services" / "AGENTS.md"
        existing.write_text("# Team notes\n\nMUST SURVIVE\n", encoding="utf-8")

        _apply_codex(target)

        body = existing.read_text(encoding="utf-8")
        assert "MUST SURVIVE" in body
        assert body.count("BEGIN GOVKIT GOVERNANCE") == 1


@pytest.mark.parametrize("agent", ["claude-code", "copilot"])
def test_glob_based_agents_are_unaffected(tmp_path, agent):
    """This change brings codex toward claude-code and copilot; it must not
    change their shape. Neither creates layer folders at all."""
    target = tmp_path / "project"
    target.mkdir()
    for layer in BACKEND_LAYERS:
        (target / "src" / "mypkg" / layer).mkdir(parents=True)

    _apply_codex(target, agent=agent)

    assert not (target / "services").exists()
    assert not (target / "src" / "mypkg" / "services" / "AGENTS.md").exists()
