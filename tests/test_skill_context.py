"""Tests for cli/skill_context.py — skill context writer.

PR 5 / Chunk E. write_skill_context emits .govkit/skill_context.yaml so
skills (PR 6b/c) can read architecture style, stack facts, CI, LLM, and
discovered extensions from a single place.

PR 6a will add load_skill_context() for skill consumers and wire apply/
stack apply to call write_skill_context too. PR 5 only needs the writer.
"""

import json
from pathlib import Path


def _write_marker(target: Path, **overrides) -> dict:
    marker_dir = target / ".govkit"
    marker_dir.mkdir(parents=True, exist_ok=True)
    base = {
        "version": "0.10.0",
        "level": "4",
        "agent": "claude-code",
        "options": {"type": "api", "ci": "github", "stack": "python-fastapi"},
        "applied_at": "2026-05-27T10:00:00+00:00",
        "stack": {
            "id": "python-fastapi", "version": "0.10.0",
            "display_name": "Python 3.11+ / FastAPI",
            "applied_at": "2026-05-27T10:00:00+00:00",
        },
        "assumptions": [],
        "calibration": {"completed_at": None, "decisions": []},
    }
    base.update(overrides)
    (marker_dir / "marker.json").write_text(json.dumps(base), encoding="utf-8")
    return base


class TestWriteSkillContext:
    def test_creates_file_at_govkit_dir(self, tmp_path):
        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path)
        write_skill_context(tmp_path, marker)
        assert (tmp_path / ".govkit" / "skill_context.yaml").is_file()

    def test_file_is_valid_yaml_with_expected_top_level_keys(self, tmp_path):
        import yaml
        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path)
        write_skill_context(tmp_path, marker)

        text = (tmp_path / ".govkit" / "skill_context.yaml").read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        assert isinstance(data, dict)
        assert "architecture" in data
        assert "stack" in data
        assert "ci" in data
        assert "llm" in data
        assert "extensions" in data

    def test_stack_section_pulls_from_marker_and_overlay(self, tmp_path):
        import yaml
        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path)
        write_skill_context(tmp_path, marker)
        data = yaml.safe_load((tmp_path / ".govkit" / "skill_context.yaml").read_text(encoding="utf-8"))

        stack = data["stack"]
        assert stack["id"] == "python-fastapi"
        # Overlay skill_context fills in language + framework + test frameworks
        assert stack["language"] == "python"
        assert stack["api_framework"] == "fastapi"
        assert stack["unit_test"] == "pytest"

    def test_architecture_style_is_unknown_when_no_signals(self, tmp_path):
        import yaml
        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path)
        write_skill_context(tmp_path, marker)
        data = yaml.safe_load((tmp_path / ".govkit" / "skill_context.yaml").read_text(encoding="utf-8"))

        assert data["architecture"]["style"] == "unknown"

    def test_architecture_style_reflects_detected_signals(self, tmp_path):
        import yaml
        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path)
        # Hexagonal signal: ports/ + adapters/ folders
        (tmp_path / "src" / "ports").mkdir(parents=True)
        (tmp_path / "src" / "adapters").mkdir(parents=True)

        write_skill_context(tmp_path, marker)
        data = yaml.safe_load((tmp_path / ".govkit" / "skill_context.yaml").read_text(encoding="utf-8"))
        assert data["architecture"]["style"] == "hexagonal"

    def test_ci_pulled_from_marker_options(self, tmp_path):
        import yaml
        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path, options={"type": "api", "ci": "azure", "stack": "python-fastapi"})
        write_skill_context(tmp_path, marker)
        data = yaml.safe_load((tmp_path / ".govkit" / "skill_context.yaml").read_text(encoding="utf-8"))
        assert data["ci"] == "azure-pipelines"

    def test_llm_true_at_l5(self, tmp_path):
        import yaml
        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path, level="5")
        write_skill_context(tmp_path, marker)
        data = yaml.safe_load((tmp_path / ".govkit" / "skill_context.yaml").read_text(encoding="utf-8"))
        assert data["llm"] is True

    def test_llm_false_at_l4(self, tmp_path):
        import yaml
        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path, level="4")
        write_skill_context(tmp_path, marker)
        data = yaml.safe_load((tmp_path / ".govkit" / "skill_context.yaml").read_text(encoding="utf-8"))
        assert data["llm"] is False

    def test_extensions_block_populated_when_extensions_present(self, tmp_path):
        import yaml
        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path)
        # Drop a minimal extension into the target
        ext_dir = tmp_path / "extensions" / "test-ext"
        ext_dir.mkdir(parents=True)
        (ext_dir / "manifest.yaml").write_text(
            "id: test-ext\nname: Test\nversion: 0.1.0\nextension_type: architecture\n"
            "contract_sets:\n  - id: x\n    description: x\n    paths: []\n"
            "capabilities:\n  - agent-runtime\n",
            encoding="utf-8",
        )

        write_skill_context(tmp_path, marker)
        data = yaml.safe_load((tmp_path / ".govkit" / "skill_context.yaml").read_text(encoding="utf-8"))

        assert len(data["extensions"]) == 1
        ext = data["extensions"][0]
        assert ext["id"] == "test-ext"
        assert ext["version"] == "0.1.0"
        assert "agent-runtime" in ext["capabilities"]

    def test_extensions_block_empty_when_none_present(self, tmp_path):
        import yaml
        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path)
        write_skill_context(tmp_path, marker)
        data = yaml.safe_load((tmp_path / ".govkit" / "skill_context.yaml").read_text(encoding="utf-8"))
        assert data["extensions"] == []
