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


# ---------------------------------------------------------------------------
# load_skill_context — typed reader for skill consumers (PR 6b/c)
# ---------------------------------------------------------------------------


class TestLoadSkillContext:
    def test_returns_skill_context_dataclass(self, tmp_path):
        from cli.skill_context import SkillContext, load_skill_context, write_skill_context

        marker = _write_marker(tmp_path)
        write_skill_context(tmp_path, marker)
        ctx = load_skill_context(tmp_path)
        assert isinstance(ctx, SkillContext)

    def test_returns_none_when_skill_context_yaml_missing(self, tmp_path):
        """A target without .govkit/skill_context.yaml returns None so
        callers (skills) can degrade gracefully — no crash."""
        from cli.skill_context import load_skill_context

        assert load_skill_context(tmp_path) is None

    def test_returns_none_when_no_govkit_dir(self, tmp_path):
        from cli.skill_context import load_skill_context

        assert load_skill_context(tmp_path) is None

    def test_returns_none_for_malformed_yaml(self, tmp_path):
        """If the file exists but is broken YAML, return None rather than
        propagating an exception into a skill at agent runtime."""
        from cli.skill_context import load_skill_context

        (tmp_path / ".govkit").mkdir()
        (tmp_path / ".govkit" / "skill_context.yaml").write_text(
            "not: valid: yaml: here:\n  - [unbalanced", encoding="utf-8",
        )
        assert load_skill_context(tmp_path) is None

    def test_typed_fields_match_yaml_payload(self, tmp_path):
        from cli.skill_context import load_skill_context, write_skill_context

        marker = _write_marker(tmp_path)
        write_skill_context(tmp_path, marker)
        ctx = load_skill_context(tmp_path)
        assert ctx is not None
        assert ctx.architecture_style == "unknown"
        assert ctx.stack_id == "python-fastapi"
        assert ctx.language == "python"
        assert ctx.api_framework == "fastapi"
        assert ctx.unit_test == "pytest"
        assert ctx.ci == "github-actions"
        assert ctx.llm is False
        assert ctx.extensions == []

    def test_layers_reflects_architecture_style(self, tmp_path):
        """The loader exposes a `layers` dict mapping inbound/outbound/domain
        to folder hints. Hexagonal repos get hexagonal layer names."""
        from cli.skill_context import load_skill_context, write_skill_context

        marker = _write_marker(tmp_path)
        # Hexagonal signals
        (tmp_path / "src" / "ports").mkdir(parents=True)
        (tmp_path / "src" / "adapters").mkdir(parents=True)
        write_skill_context(tmp_path, marker)

        ctx = load_skill_context(tmp_path)
        assert ctx is not None
        assert ctx.architecture_style == "hexagonal"
        assert isinstance(ctx.layers, dict)
        # The loader should expose at least inbound/outbound/domain keys.
        assert "inbound" in ctx.layers
        assert "outbound" in ctx.layers
        assert "domain" in ctx.layers

    def test_apply_writes_skill_context_yaml(self, tmp_path, monkeypatch):
        """PR 6a: cmd_apply must call write_skill_context so the file exists
        from day one — skills shouldn't have to wait for calibrate to run."""
        import argparse

        from cli.govkit import cmd_apply
        from cli.skill_context import load_skill_context

        target = tmp_path / "project"
        target.mkdir()
        cmd_apply(argparse.Namespace(
            agent="claude-code", target=str(target),
            level="4", type="api", ci="github",
            stack="python-fastapi", force=False, detect=False,
        ))

        ctx = load_skill_context(target)
        assert ctx is not None
        assert ctx.stack_id == "python-fastapi"
        assert ctx.language == "python"

    def test_stack_apply_refreshes_skill_context_yaml(self, tmp_path):
        """PR 6a: cmd_stack_apply must rewrite skill_context.yaml so the
        stack swap is reflected immediately for any skill that consults it."""
        import argparse

        from cli.govkit import cmd_apply, cmd_stack_apply
        from cli.skill_context import load_skill_context

        target = tmp_path / "project"
        target.mkdir()
        cmd_apply(argparse.Namespace(
            agent="claude-code", target=str(target),
            level="4", type="api", ci="github",
            stack="python-fastapi", force=False, detect=False,
        ))
        before = load_skill_context(target)
        assert before.stack_id == "python-fastapi"

        cmd_stack_apply(argparse.Namespace(
            stack_id="dotnet-aspnet", target=str(target), force=False,
        ))

        after = load_skill_context(target)
        assert after is not None
        assert after.stack_id == "dotnet-aspnet"
        assert after.language == "csharp"
        assert after.api_framework == "aspnet-core"

    def test_extensions_carry_capability_lists(self, tmp_path):
        from cli.skill_context import load_skill_context, write_skill_context

        marker = _write_marker(tmp_path)
        ext_dir = tmp_path / "extensions" / "test-ext"
        ext_dir.mkdir(parents=True)
        (ext_dir / "manifest.yaml").write_text(
            "id: test-ext\nname: Test\nversion: 0.2.0\nextension_type: architecture\n"
            "contract_sets:\n  - id: x\n    description: x\n    paths: []\n"
            "capabilities:\n  - agent-runtime\n  - human-approval\n",
            encoding="utf-8",
        )
        write_skill_context(tmp_path, marker)

        ctx = load_skill_context(tmp_path)
        assert ctx is not None
        assert len(ctx.extensions) == 1
        ext = ctx.extensions[0]
        assert ext["id"] == "test-ext"
        assert ext["version"] == "0.2.0"
        assert "agent-runtime" in ext["capabilities"]
        assert "human-approval" in ext["capabilities"]


class TestLoadSkillContextMalformedBlocks:
    """The loader's contract is 'return None when missing or unparseable'
    so skills (and _post_install_finalize) never see propagating exceptions.
    Hand-edited skill_context.yaml can introduce shape mismatches the loader
    must absorb without crashing:
      - architecture/stack flattened to a scalar
      - layers swapped for a string or list
      - individual layer values written as a string instead of a list
      - detected_signals / extensions written as a scalar
    """

    def _write(self, tmp_path, body: str) -> None:
        (tmp_path / ".govkit").mkdir()
        (tmp_path / ".govkit" / "skill_context.yaml").write_text(body, encoding="utf-8")

    def test_architecture_as_scalar_does_not_crash(self, tmp_path):
        from cli.skill_context import load_skill_context
        self._write(tmp_path, "architecture: hexagonal\nstack:\n  id: python-fastapi\n")
        # Must not raise AttributeError on `arch.get(...)`.
        ctx = load_skill_context(tmp_path)
        # Loader may return None or a context with default architecture; either
        # is acceptable, but it must not propagate an exception.
        if ctx is not None:
            assert ctx.architecture_style == "unknown"
            assert isinstance(ctx.layers, dict)

    def test_stack_as_scalar_does_not_crash(self, tmp_path):
        from cli.skill_context import load_skill_context
        self._write(tmp_path, "architecture:\n  style: hexagonal\nstack: python-fastapi\n")
        ctx = load_skill_context(tmp_path)
        if ctx is not None:
            assert ctx.stack_id is None  # scalar stack can't be unpacked

    def test_layers_as_string_falls_back_to_unknown(self, tmp_path):
        """Hand-edit fat-fingered `layers: api/` instead of a mapping.
        Must not raise ValueError on `dict('api/')`."""
        from cli.skill_context import load_skill_context
        self._write(tmp_path, "architecture:\n  style: hexagonal\n  layers: api/\nstack: {}\n")
        ctx = load_skill_context(tmp_path)
        assert ctx is not None, "loader must absorb malformed layers, not return None"
        assert isinstance(ctx.layers, dict)
        # Falls back to the unknown-style layer skeleton (empty lists per key).
        assert ctx.layers == {"inbound": [], "outbound": [], "domain": []}

    def test_layers_as_list_falls_back_to_unknown(self, tmp_path):
        from cli.skill_context import load_skill_context
        self._write(tmp_path, "architecture:\n  style: hexagonal\n  layers:\n    - api/\n    - ports/\nstack: {}\n")
        ctx = load_skill_context(tmp_path)
        assert ctx is not None
        assert isinstance(ctx.layers, dict)
        assert ctx.layers == {"inbound": [], "outbound": [], "domain": []}

    def test_layer_value_as_string_is_normalized_to_list(self, tmp_path):
        """`inbound: api/` (scalar) becomes `inbound: ["api/"]` so the
        rule_templating consumer's `for h in hints` loop iterates folder
        names instead of characters."""
        from cli.skill_context import load_skill_context
        self._write(tmp_path, "architecture:\n  style: hexagonal\n  layers:\n    inbound: api/\n    outbound: adapters/\n    domain: services/\nstack: {}\n")
        ctx = load_skill_context(tmp_path)
        assert ctx is not None
        assert ctx.layers["inbound"] == ["api/"]
        assert ctx.layers["outbound"] == ["adapters/"]
        assert ctx.layers["domain"] == ["services/"]

    def test_detected_signals_as_scalar_does_not_crash(self, tmp_path):
        from cli.skill_context import load_skill_context
        self._write(tmp_path, "architecture:\n  style: hexagonal\n  detected_signals: hexagonal-shape\nstack: {}\n")
        ctx = load_skill_context(tmp_path)
        assert ctx is not None
        # Must not splat the string into characters: `list("hexagonal-shape")`
        # would give ['h','e','x',...]. Either keep it as a one-item list or
        # drop to an empty list — both are correct; characters are not.
        assert isinstance(ctx.detected_signals, list)
        assert ctx.detected_signals in ([], ["hexagonal-shape"])

    def test_extensions_as_scalar_does_not_crash(self, tmp_path):
        from cli.skill_context import load_skill_context
        self._write(tmp_path, "architecture:\n  style: hexagonal\nstack: {}\nextensions: agentic-skills\n")
        ctx = load_skill_context(tmp_path)
        assert ctx is not None
        assert isinstance(ctx.extensions, list)
        # Same anti-splat rule: characters are not extensions.
        assert all(isinstance(e, dict) for e in ctx.extensions)
