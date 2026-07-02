"""Tests for cli/overlay.py — Overlay dataclass + loader + STACKS_DIR resolver.

PR 2 / Chunk D. Stacks are bundled at cli/stacks/<id>/ with an overlay.yaml
describing metadata + docs + default_assumptions + skill_context +
review_checklist. Loader is the single source of truth for resolving stacks.
"""



class TestStacksDirResolver:
    def test_resolves_to_existing_directory(self):
        from cli.overlay import STACKS_DIR

        assert STACKS_DIR.is_dir(), f"STACKS_DIR must exist on disk: {STACKS_DIR}"
        # Sanity: at least one bundled stack lives there.
        children = {p.name for p in STACKS_DIR.iterdir() if p.is_dir()}
        assert "python-fastapi" in children


class TestListOverlays:
    def test_lists_all_bundled_stacks(self):
        from cli.overlay import list_overlays

        ids = {o.id for o in list_overlays()}
        # The original API/CLI stacks plus data stacks.
        assert {"python-fastapi", "dotnet-aspnet", "java-spring-boot",
                "nodejs-fastify", "go-gin", "python-dbt",
                "databricks-lakehouse"}.issubset(ids)

    def test_each_overlay_has_minimum_metadata(self):
        from cli.overlay import list_overlays

        for ov in list_overlays():
            assert ov.id, f"{ov} missing id"
            assert ov.version, f"{ov.id} missing version"
            assert ov.display_name, f"{ov.id} missing display_name"
            assert ov.summary, f"{ov.id} missing summary"
            # docs is a non-empty list of dicts (PR 2 ships 6 per stack)
            assert isinstance(ov.docs, list) and len(ov.docs) > 0, f"{ov.id} has no docs"

    def test_returns_overlays_sorted_by_id(self):
        from cli.overlay import list_overlays

        ids = [o.id for o in list_overlays()]
        assert ids == sorted(ids), "list_overlays should return overlays sorted by id"

    def test_every_overlay_declares_supported_types(self):
        """Guard: type-gating (stack_select) reads supported_types from the
        overlay. A bundled stack without it would silently permit every
        --type, so the contract requires a non-empty declaration."""
        from cli.overlay import list_overlays

        known_types = {"api", "cli", "data", "ui-react", "ui-angular"}
        for ov in list_overlays():
            assert ov.supported_types, f"{ov.id} missing supported_types"
            unknown = set(ov.supported_types) - known_types
            assert not unknown, f"{ov.id} has unknown supported_types: {unknown}"

    def test_every_overlay_declares_language(self):
        """Guard: doctor D005 reads skill_context.language from the overlay.
        A bundled stack without it would silently drop out of D005 coverage."""
        from cli.overlay import list_overlays

        for ov in list_overlays():
            assert ov.skill_context.get("language"), (
                f"{ov.id} missing skill_context.language"
            )


class TestLoadOverlay:
    def test_loads_known_overlay(self):
        from cli.overlay import load_overlay

        ov = load_overlay("dotnet-aspnet")
        assert ov is not None
        assert ov.id == "dotnet-aspnet"
        assert "ASP.NET Core" in ov.display_name
        assert ov.version == "0.10.0"

    def test_returns_none_for_unknown_overlay(self):
        from cli.overlay import load_overlay

        assert load_overlay("does-not-exist") is None

    def test_returns_none_for_empty_id(self):
        from cli.overlay import load_overlay

        assert load_overlay("") is None

    def test_default_assumptions_populated(self):
        from cli.overlay import load_overlay

        ov = load_overlay("dotnet-aspnet")
        assert ov is not None
        ids = [a["id"] for a in ov.default_assumptions]
        assert "stack.language" in ids
        assert "stack.framework" in ids

    def test_docs_are_resolvable_paths(self, tmp_path):
        """Every src in overlay.docs must exist relative to the overlay dir."""
        from cli.overlay import load_overlay

        for stack_id in ("python-fastapi", "dotnet-aspnet", "java-spring-boot",
                         "nodejs-fastify", "go-gin", "python-dbt",
                         "databricks-lakehouse"):
            ov = load_overlay(stack_id)
            assert ov is not None, f"{stack_id} should load"
            for doc in ov.docs:
                src_path = ov.root / doc["src"]
                assert src_path.is_file(), (
                    f"{stack_id}: overlay.yaml claims docs.{doc['src']} exists but "
                    f"{src_path} is missing"
                )

    def test_skill_context_present(self):
        from cli.overlay import load_overlay

        ov = load_overlay("python-fastapi")
        assert ov is not None
        assert ov.skill_context.get("language") == "python"
        assert ov.skill_context.get("api_framework") == "fastapi"

    def test_supported_types_for_backend_stack(self):
        from cli.overlay import load_overlay

        ov = load_overlay("python-fastapi")
        assert ov is not None
        assert ov.supported_types == ["api", "cli"]

    def test_supported_types_for_data_stack(self):
        from cli.overlay import load_overlay

        ov = load_overlay("python-dbt")
        assert ov is not None
        assert ov.supported_types == ["data"]

    def test_supported_types_defaults_to_empty_when_absent(self, tmp_path, monkeypatch):
        """The loader tolerates an overlay without supported_types (empty
        list, not a crash) — consumers treat empty as 'no restriction'.
        The schema + guard test keep bundled overlays from actually
        shipping that way."""
        stack_dir = tmp_path / "minimal-stack"
        stack_dir.mkdir()
        (stack_dir / "overlay.yaml").write_text(
            'id: minimal-stack\nversion: "0.1.0"\ndisplay_name: "Minimal"\n',
            encoding="utf-8",
        )
        monkeypatch.setattr("cli.overlay.STACKS_DIR", tmp_path)
        from cli.overlay import load_overlay

        ov = load_overlay("minimal-stack")
        assert ov is not None
        assert ov.supported_types == []

    def test_databricks_lakehouse_overlay_metadata(self):
        from cli.overlay import load_overlay

        ov = load_overlay("databricks-lakehouse")
        assert ov is not None
        assert "Databricks" in ov.display_name
        assert ov.skill_context.get("language") == "python"
        assert ov.skill_context.get("framework") == "databricks-lakehouse"
        assert ov.skill_context.get("deployment") == "databricks-asset-bundles"
        dests = {doc["dest"] for doc in ov.docs}
        assert {
            "docs/data/architecture/TECH_STACK.md",
            "docs/data/architecture/TESTING.md",
            "docs/data/architecture/MODEL_LAYERING.md",
            "docs/data/architecture/PIPELINE_CONTRACT.md",
            "docs/data/architecture/PII_HANDLING.md",
            "docs/data/architecture/LINEAGE_OBSERVABILITY.md",
        }.issubset(dests)


class TestApplyOverlay:
    """apply_overlay copies the overlay's docs into the target repo and
    returns a list of (dest, baseline) tuples for the caller to record."""

    def test_copies_docs_to_target(self, tmp_path):
        from cli.overlay import apply_overlay, load_overlay

        ov = load_overlay("python-fastapi")
        assert ov is not None

        apply_overlay(ov, tmp_path)

        tech_stack = tmp_path / "docs" / "backend" / "architecture" / "TECH_STACK.md"
        assert tech_stack.is_file()
        # Stack docs get the editable header with the overlay's id+version.
        content = tech_stack.read_text(encoding="utf-8")
        assert content.startswith("<!-- govkit:editable")
        assert "baseline: python-fastapi@0.10.0" in content

    def test_returns_list_of_copied_files(self, tmp_path):
        from cli.overlay import apply_overlay, load_overlay

        ov = load_overlay("python-fastapi")
        copied = apply_overlay(ov, tmp_path)
        # Six stack docs per the overlay.yaml
        assert len(copied) == 6
        rels = {str(p.relative_to(tmp_path)).replace("\\", "/") for p in copied}
        assert "docs/backend/architecture/TECH_STACK.md" in rels

    def test_respects_edit_protection_with_applied_at(self, tmp_path, capsys):
        """apply_overlay must route through copy_entry's edit-protection
        so user-edited stack docs are not silently clobbered."""
        import os
        from datetime import datetime, timezone

        from cli.headers import format_editable_header
        from cli.overlay import apply_overlay, load_overlay

        # Pre-populate dest with a headed + edited TECH_STACK.md.
        dest = tmp_path / "docs" / "backend" / "architecture" / "TECH_STACK.md"
        dest.parent.mkdir(parents=True)
        header = format_editable_header(baseline="python-fastapi@0.10.0")
        dest.write_text(header + "# my custom edits\n", encoding="utf-8")
        edited_time = datetime(2026, 5, 27, 11, 0, 0, tzinfo=timezone.utc).timestamp()
        os.utime(dest, (edited_time, edited_time))
        applied_at = datetime(2026, 5, 27, 10, 0, 0, tzinfo=timezone.utc).isoformat()

        ov = load_overlay("python-fastapi")
        apply_overlay(ov, tmp_path, applied_at=applied_at, force=False)

        # User edits preserved.
        assert "my custom edits" in dest.read_text(encoding="utf-8")
        err = capsys.readouterr().err
        assert "refused" in err
