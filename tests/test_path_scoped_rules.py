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


def _codex_path_scoped_dests() -> list[str]:
    """The root-relative destinations codex's manifest declares as path-scoped.

    Read from the manifest rather than listed here, so a rule added or
    removed in the payload cannot leave these tests asserting a stale set.
    """
    from cli.manifest import load_manifest, resolve_variant_files

    manifest = load_manifest("codex")
    files, _shared, _governed = resolve_variant_files(
        manifest, {"level": "4", "type": "api", "ci": "github", "stack": "python-fastapi"},
    )
    return [e["dest"] for e in files if e.get("path_scoped")]


class TestMultiServiceFanOut:
    """In a `src/{orders,billing}/` repo, codex's layer rules belong inside
    each service.

    Before this, `detect_source_root` returned `""` and the destinations
    stayed root-relative, so `apply` wrote `api/AGENTS.md` at the repo root.
    Codex resolves AGENTS.md upward from the file being edited, so a file at
    `src/orders/api/handlers.py` reaches the top-level `AGENTS.md` and never
    that one — the layer rules governed no code at all. The empty root
    folders then made every later reading of the repo see a flat
    single-service layout, which is what erased `architecture.services` on
    upgrade.
    """

    @staticmethod
    def _multi_service(target):
        for svc in ("orders", "billing"):
            for layer in BACKEND_LAYERS:
                (target / "src" / svc / layer).mkdir(parents=True)

    def test_the_manifest_really_declares_path_scoped_rules(self):
        """Everything below is asserted against this set. If it emptied, the
        tests would pass by describing nothing."""
        dests = _codex_path_scoped_dests()
        assert len(dests) >= 5
        assert all(d.endswith("/AGENTS.md") for d in dests)
        assert "api/AGENTS.md" in dests

    def test_rules_land_inside_every_service(self, tmp_path):
        target = tmp_path / "project"
        target.mkdir()
        self._multi_service(target)

        _apply_codex(target)

        for svc in ("orders", "billing"):
            for dest in _codex_path_scoped_dests():
                assert (target / "src" / svc / dest).is_file(), f"{svc}: missing {dest}"

    def test_no_layer_rules_are_written_at_the_repo_root(self, tmp_path):
        target = tmp_path / "project"
        target.mkdir()
        self._multi_service(target)

        _apply_codex(target)

        for dest in _codex_path_scoped_dests():
            assert not (target / dest).exists(), (
                f"{dest} written at the root, where codex will never resolve it"
            )

    def test_the_top_level_agents_md_is_untouched_by_the_fan_out(self, tmp_path):
        """It is not path-scoped, so it stays exactly where it was."""
        target = tmp_path / "project"
        target.mkdir()
        self._multi_service(target)

        _apply_codex(target)

        assert (target / "AGENTS.md").is_file()

    def test_a_teams_own_file_at_a_service_location_keeps_its_content(self, tmp_path):
        target = tmp_path / "project"
        target.mkdir()
        self._multi_service(target)
        existing = target / "src" / "orders" / "api" / "AGENTS.md"
        existing.write_text("# Orders notes\n\nMUST SURVIVE\n", encoding="utf-8")

        _apply_codex(target)

        body = existing.read_text(encoding="utf-8")
        assert "MUST SURVIVE" in body
        assert body.count("BEGIN GOVKIT GOVERNANCE") == 1

    def test_three_services_each_get_the_rules(self, tmp_path):
        target = tmp_path / "project"
        target.mkdir()
        for svc in ("orders", "billing", "shipping"):
            for layer in BACKEND_LAYERS:
                (target / "src" / svc / layer).mkdir(parents=True)

        _apply_codex(target)

        for svc in ("orders", "billing", "shipping"):
            assert (target / "src" / svc / "api" / "AGENTS.md").is_file()

    def test_non_conforming_siblings_get_no_rules(self, tmp_path):
        """`src/legacy/` is not a service govkit can describe, so it is not
        one govkit writes layer rules into either."""
        target = tmp_path / "project"
        target.mkdir()
        self._multi_service(target)
        (target / "src" / "legacy" / "scripts").mkdir(parents=True)

        _apply_codex(target)

        assert not (target / "src" / "legacy" / "api").exists()

    def test_the_service_list_now_survives_an_upgrade(self, tmp_path):
        """The point of the whole change. `apply` recorded the services
        correctly before this; the root folders it created then made the next
        `upgrade` read the repo as flat and drop them."""
        import json

        import yaml

        from cli.cmd_upgrade import cmd_upgrade

        target = tmp_path / "project"
        target.mkdir()
        self._multi_service(target)
        _apply_codex(target)

        def services():
            data = yaml.safe_load(
                (target / ".govkit" / "skill_context.yaml").read_text(encoding="utf-8"),
            )
            return [s["name"] for s in data["architecture"].get("services", [])]

        assert services() == ["billing", "orders"]

        # An install from an earlier govkit, so upgrade does real work rather
        # than short-circuiting on a matching version.
        marker_path = target / ".govkit" / "marker.json"
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        marker["version"] = "0.13.0"
        marker_path.write_text(json.dumps(marker), encoding="utf-8")

        cmd_upgrade(argparse.Namespace(target=str(target), force=False))

        assert services() == ["billing", "orders"]


class TestSingleServiceFanOutRegression:
    """Every layout that is not multi-service must install exactly as before."""

    @pytest.mark.parametrize("prefix", ["", "src", "src/mypkg"])
    def test_single_source_root_layouts_are_unchanged(self, tmp_path, prefix):
        target = tmp_path / "project"
        target.mkdir()
        base = target / prefix if prefix else target
        for layer in BACKEND_LAYERS:
            (base / layer).mkdir(parents=True)

        _apply_codex(target)

        for dest in _codex_path_scoped_dests():
            assert (base / dest).is_file(), f"{prefix or '<root>'}: missing {dest}"

    def test_unknown_layout_still_installs_root_relative(self, tmp_path):
        target = tmp_path / "project"
        target.mkdir()

        _apply_codex(target)

        assert (target / "services" / "AGENTS.md").is_file()


@pytest.mark.parametrize("agent", ["claude-code", "copilot"])
def test_glob_based_agents_are_unaffected_by_the_fan_out(tmp_path, agent):
    """Their rules carry `**/<layer>/**` globs that already match at any
    depth, in every service — the accident #86 documents. The fan-out must
    not start creating layer folders for them."""
    target = tmp_path / "project"
    target.mkdir()
    for svc in ("orders", "billing"):
        for layer in BACKEND_LAYERS:
            (target / "src" / svc / layer).mkdir(parents=True)

    _apply_codex(target, agent=agent)

    assert not (target / "api" / "AGENTS.md").exists()
    assert not (target / "src" / "orders" / "api" / "AGENTS.md").exists()


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
