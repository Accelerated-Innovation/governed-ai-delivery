"""Tests for cli/stack_select.py — stage 2 of the stack pipeline.

resolve_stack_choice decides which bundled overlay an install uses given the
inferred stack, the user's explicit --stack flag, and the requested --type.
The user's explicit --type must outrank an ambient framework signal from a
different shape (e.g. a workshop demo dir with `fastapi` in pyproject.toml plus
`--type data` must select python-dbt, not python-fastapi).
"""

from cli.detect import RepoProfile
from cli.stack_select import resolve_stack_choice


def _profile(tmp_path, frameworks=None, languages=None, signals=None):
    return RepoProfile(
        target=tmp_path,
        detected_languages=list(languages or []),
        detected_frameworks=list(frameworks or []),
        detected_ci=[],
        detected_test_packages=[],
        detected_project_paths=[],
        detected_api_style=None,
        detected_llm_signals=[],
        detected_architecture_signals=list(signals or []),
    )


class TestResolveStackChoiceTypeCompatibility:
    def test_explicit_stack_flag_always_wins(self, tmp_path):
        chosen, source, _, _ = resolve_stack_choice(
            "java-spring-boot", "data",
            _profile(tmp_path, frameworks=["fastapi"], languages=["python"]),
            inferred_stack="python-fastapi", inferred_confidence="high",
            target=tmp_path,
        )
        assert (chosen, source) == ("java-spring-boot", "flag")

    def test_type_data_overrides_fastapi_inference(self, tmp_path):
        """Workshop dir has fastapi in pyproject, user passes --type data:
        the incompatible inferred stack must not win — default to python-dbt."""
        chosen, source, _, _ = resolve_stack_choice(
            None, "data",
            _profile(tmp_path, frameworks=["fastapi"], languages=["python"]),
            inferred_stack="python-fastapi", inferred_confidence="high",
            target=tmp_path,
        )
        assert chosen == "python-dbt", (
            f"--type data with ambient fastapi signal must default to python-dbt, "
            f"not honor the incompatible inferred stack; got {chosen}"
        )
        assert source == "default"

    def test_type_data_no_signals_defaults_to_dbt(self, tmp_path):
        """No inference at all + --type data must land on python-dbt. Guards
        the bug where the manifest's silent stack default (python-fastapi)
        shadowed the per-type default in the real apply path."""
        chosen, source, _, _ = resolve_stack_choice(
            None, "data",
            _profile(tmp_path),
            inferred_stack=None, inferred_confidence="none",
            target=tmp_path,
        )
        assert (chosen, source) == ("python-dbt", "default")

    def test_type_data_honors_dbt_inference(self, tmp_path):
        """When the inferred stack IS compatible with --type data (dbt),
        we should still honor the high-confidence inference."""
        chosen, source, _, _ = resolve_stack_choice(
            None, "data",
            _profile(tmp_path, frameworks=["dbt"], languages=["python"], signals=["dbt-shape"]),
            inferred_stack="python-dbt", inferred_confidence="high",
            target=tmp_path,
        )
        assert chosen == "python-dbt"
        assert source == "detected"

    def test_type_api_overrides_dbt_inference(self, tmp_path):
        """Inverse: --type api with an ambient dbt_project.yml laying around
        must default to python-fastapi, not honor the incompatible dbt match."""
        chosen, source, _, _ = resolve_stack_choice(
            None, "api",
            _profile(tmp_path, frameworks=["dbt"], languages=["python"], signals=["dbt-shape"]),
            inferred_stack="python-dbt", inferred_confidence="high",
            target=tmp_path,
        )
        assert chosen == "python-fastapi"
        assert source == "default"

    def test_type_api_honors_compatible_backend_inference(self, tmp_path):
        """Sanity: --type api with detected csharp/aspnet still works."""
        chosen, source, _, _ = resolve_stack_choice(
            None, "api",
            _profile(tmp_path, frameworks=["aspnet-core"], languages=["csharp"]),
            inferred_stack="dotnet-aspnet", inferred_confidence="high",
            target=tmp_path,
        )
        assert chosen == "dotnet-aspnet"
        assert source == "detected"


class TestStackMarkerRecordBuilders:
    """build_stack_assumption / build_stack_meta are the single point of
    construction for the two stack records written into the marker — both
    `govkit apply --stack` and `govkit stack apply` must consume them so the
    record shapes cannot drift apart."""

    def _overlay(self):
        from cli.overlay import load_overlay

        overlay = load_overlay("python-fastapi")
        assert overlay is not None
        return overlay

    def test_assumption_from_flag_source(self):
        from cli.stack_select import build_stack_assumption

        overlay = self._overlay()
        a = build_stack_assumption(overlay, source="flag", confidence="high", evidence=[])
        assert a["id"] == "stack.id"
        assert a["value"] == "python-fastapi"
        assert a["source"] == "flag"
        assert a["confidence"] == "high"
        assert a["evidence"] == []
        assert a["files_affected"] == [d["dest"] for d in overlay.docs]
        assert a["review_required"] is False
        assert a["warning_message"] is None
        assert a["calibrated_at"] is None
        assert a["calibrated_against_overlay_version"] is None

    def test_assumption_from_default_source_requires_review(self):
        from cli.stack_select import build_stack_assumption

        a = build_stack_assumption(self._overlay(), source="default", confidence="low", evidence=[])
        assert a["review_required"] is True
        assert "python-fastapi" in a["warning_message"]

    def test_stack_meta_shape(self):
        from datetime import datetime

        from cli.stack_select import build_stack_meta

        overlay = self._overlay()
        meta = build_stack_meta(overlay)
        assert set(meta) == {"id", "version", "display_name", "applied_at"}
        assert meta["id"] == overlay.id
        assert meta["version"] == overlay.version
        assert meta["display_name"] == overlay.display_name
        datetime.fromisoformat(meta["applied_at"])  # parseable timestamp
