"""Tests for cli/skill_context.py — skill context writer.

PR 5 / Chunk E. write_skill_context emits .govkit/skill_context.yaml so
skills (PR 6b/c) can read architecture style, stack facts, CI, LLM, and
discovered extensions from a single place.

PR 6a will add load_skill_context() for skill consumers and wire apply/
stack apply to call write_skill_context too. PR 5 only needs the writer.
"""

import json
from pathlib import Path

import pytest


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
        assert "docs_area" in data
        assert "llm" in data
        assert "extensions" in data

    def test_docs_area_derived_from_marker_type(self, tmp_path):
        """docs_area follows options.type so installed skills can be
        templated to the type's docs tree (docs/<area>/architecture/)."""
        import yaml

        from cli.skill_context import write_skill_context

        for marker_type, expected in [
            ("api", "backend"), ("cli", "backend"),
            ("ui-react", "ui"), ("ui-angular", "ui"), ("ui-nextjs", "ui"),
            ("data", "data"),
        ]:
            marker = _write_marker(
                tmp_path, options={"type": marker_type, "ci": "github"},
            )
            write_skill_context(tmp_path, marker)
            data = yaml.safe_load(
                (tmp_path / ".govkit" / "skill_context.yaml").read_text(encoding="utf-8"),
            )
            assert data["docs_area"] == expected, marker_type

    def test_docs_area_empty_when_type_missing_or_unknown(self, tmp_path):
        import yaml

        from cli.skill_context import write_skill_context

        for options in ({"ci": "github"}, {"type": "mainframe", "ci": "github"}):
            marker = _write_marker(tmp_path, options=options)
            write_skill_context(tmp_path, marker)
            data = yaml.safe_load(
                (tmp_path / ".govkit" / "skill_context.yaml").read_text(encoding="utf-8"),
            )
            assert data["docs_area"] == "", options

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

    def test_hexagonal_domain_hint_names_services_and_models(self, tmp_path):
        """The domain layer is `services/` (behaviour) plus `models/`
        (entities) — the vocabulary BOUNDARIES.md and ARCH_CONTRACT.md
        settle on. This value is not merely informational: rule_templating
        expands it into the concrete `paths:` globs that scope every
        backend rule, so a hint naming a package the team does not have
        leaves those rules attached to nothing."""
        from cli.skill_context import load_skill_context, write_skill_context

        marker = _write_marker(tmp_path)
        (tmp_path / "src" / "ports").mkdir(parents=True)
        (tmp_path / "src" / "adapters").mkdir(parents=True)
        write_skill_context(tmp_path, marker)

        ctx = load_skill_context(tmp_path)
        assert ctx is not None
        assert ctx.architecture_style == "hexagonal"
        assert ctx.layers["domain"] == ["services/", "models/"]

    def test_documented_src_package_layout_yields_populated_layers(self, tmp_path):
        """A repo laid out the way REPO_STRUCTURE_README.md prescribes —
        `src/<package>/api/...` — must produce a usable skill context.
        Before detection looked below src/, this yielded style="unknown"
        with every layer hint empty, which silently unscoped the backend
        rules that template off those hints."""
        from cli.skill_context import load_skill_context, write_skill_context

        marker = _write_marker(tmp_path)
        for layer in ("api", "ports", "services", "models", "adapters", "common"):
            (tmp_path / "src" / "customer_support_ai" / layer).mkdir(parents=True)
        write_skill_context(tmp_path, marker)

        ctx = load_skill_context(tmp_path)
        assert ctx is not None
        assert ctx.architecture_style == "hexagonal"
        assert ctx.layers["domain"] == ["services/", "models/"]
        assert ctx.layers["inbound"] and ctx.layers["outbound"]

    def test_apply_writes_skill_context_yaml(self, tmp_path, monkeypatch):
        """PR 6a: cmd_apply must call write_skill_context so the file exists
        from day one — skills shouldn't have to wait for calibrate to run."""
        import argparse

        from cli.cmd_apply import cmd_apply
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

        from cli.cmd_apply import cmd_apply
        from cli.cmd_stack import cmd_stack_apply
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
        self._write(tmp_path, "architecture:\n  style: hexagonal\nstack: {}\nextensions: demo-ext\n")
        ctx = load_skill_context(tmp_path)
        assert ctx is not None
        assert isinstance(ctx.extensions, list)
        # Same anti-splat rule: characters are not extensions.
        assert all(isinstance(e, dict) for e in ctx.extensions)


class TestLoadSkillContextDocsArea:
    def _write(self, target: Path, text: str) -> None:
        (target / ".govkit").mkdir(parents=True, exist_ok=True)
        (target / ".govkit" / "skill_context.yaml").write_text(text, encoding="utf-8")

    def test_docs_area_round_trips(self, tmp_path):
        from cli.skill_context import load_skill_context
        self._write(tmp_path, "architecture:\n  style: hexagonal\nstack: {}\ndocs_area: data\n")
        ctx = load_skill_context(tmp_path)
        assert ctx is not None
        assert ctx.docs_area == "data"

    def test_docs_area_missing_or_malformed_is_empty(self, tmp_path):
        from cli.skill_context import load_skill_context
        for body in (
            "architecture:\n  style: hexagonal\nstack: {}\n",
            "architecture:\n  style: hexagonal\nstack: {}\ndocs_area: [data]\n",
        ):
            self._write(tmp_path, body)
            ctx = load_skill_context(tmp_path)
            assert ctx is not None
            assert ctx.docs_area == ""


class TestArchitectureEditPreservation:
    """A team's hand-edits to the architecture block must survive the rewrite
    that apply / upgrade / stack apply / calibrate each perform.

    Two comments in cli/skill_context.py have long promised this — "Teams
    using medallion (bronze/silver/gold) edit `architecture.layers` ...
    directly during calibrate" and `source_root` "caller may edit
    post-write" — while every write clobbered both.

    Preservation is provenance-based rather than "non-empty wins": govkit
    records what it derived, so a value differing from that record is a
    team edit and is kept, while an untouched value still refreshes when
    the derivation legitimately changes (a stack swap, a restructured repo).
    """

    @staticmethod
    def _read(target):
        import yaml
        return yaml.safe_load(
            (target / ".govkit" / "skill_context.yaml").read_text(encoding="utf-8"),
        )

    @staticmethod
    def _edit(target, mutate):
        import yaml
        path = target / ".govkit" / "skill_context.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        mutate(data)
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    def _hexagonal(self, tmp_path):
        (tmp_path / "src" / "ports").mkdir(parents=True)
        (tmp_path / "src" / "adapters").mkdir(parents=True)

    def test_rewrite_preserves_edited_layers(self, tmp_path):
        """The medallion case the docstring promises: a data team renames the
        layer hints to bronze/silver/gold and re-runs calibrate."""
        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path)
        self._hexagonal(tmp_path)
        write_skill_context(tmp_path, marker)

        medallion = {"inbound": ["bronze/"], "outbound": ["gold/"], "domain": ["silver/"]}
        self._edit(tmp_path, lambda d: d["architecture"].update(layers=medallion))

        write_skill_context(tmp_path, marker)

        assert self._read(tmp_path)["architecture"]["layers"] == medallion

    def test_rewrite_preserves_a_single_edited_layer_hint(self, tmp_path):
        """Editing one hint in place is what a team actually does, and it must
        not silently edit the provenance record too.

        The live block and the record must be independent objects. Sharing
        one makes `yaml.safe_dump` emit an anchor and an alias, so on reload
        they are the same object again — a hand-edit rewrites the record it
        is supposed to be compared against, and preservation quietly stops
        working while whole-dict replacement still appears to pass."""
        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path)
        self._hexagonal(tmp_path)
        write_skill_context(tmp_path, marker)

        self._edit(tmp_path, lambda d: d["architecture"]["layers"].__setitem__("domain", ["core/"]))
        raw = (tmp_path / ".govkit" / "skill_context.yaml").read_text(encoding="utf-8")
        assert "*id" not in raw, f"YAML alias in skill_context.yaml:\n{raw}"

        write_skill_context(tmp_path, marker)

        assert self._read(tmp_path)["architecture"]["layers"]["domain"] == ["core/"]

    def test_style_layers_constant_is_not_mutated(self, tmp_path):
        """The derived block must be a copy — handing out the module-level
        _STYLE_LAYERS dict lets any caller corrupt every later install in
        the same process."""
        from cli.skill_context import _STYLE_LAYERS, build_skill_context

        marker = _write_marker(tmp_path)
        self._hexagonal(tmp_path)
        data = build_skill_context(tmp_path, marker)
        data["architecture"]["layers"]["domain"] = ["mutated/"]

        assert _STYLE_LAYERS["hexagonal"]["domain"] == ["services/", "models/"]

    def test_rewrite_preserves_edited_source_root(self, tmp_path):
        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path)
        self._hexagonal(tmp_path)
        write_skill_context(tmp_path, marker)

        self._edit(tmp_path, lambda d: d["architecture"].update(source_root="services/"))
        write_skill_context(tmp_path, marker)

        assert self._read(tmp_path)["architecture"]["source_root"] == "services/"

    def test_rewrite_preserves_edited_style(self, tmp_path):
        """Detection can guess wrong on a mixed repo; a corrected style must
        stick."""
        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path)
        self._hexagonal(tmp_path)
        write_skill_context(tmp_path, marker)

        self._edit(tmp_path, lambda d: d["architecture"].update(style="clean"))
        write_skill_context(tmp_path, marker)

        assert self._read(tmp_path)["architecture"]["style"] == "clean"

    def test_editing_only_style_reseeds_the_layer_hints(self, tmp_path):
        """`layers` describes `style` — the two cannot disagree.

        Correcting the style alone is the natural edit: a team on a mixed
        repo fixes the one field they can see is wrong. If `layers` then
        kept the *detected* style's hints, the file would claim Clean
        Architecture while scoping rules to hexagonal folders, and
        rule_templating would expand globs for packages the repo does not
        have."""
        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path)
        self._hexagonal(tmp_path)
        write_skill_context(tmp_path, marker)

        self._edit(tmp_path, lambda d: d["architecture"].update(style="clean"))
        write_skill_context(tmp_path, marker)

        arch = self._read(tmp_path)["architecture"]
        assert arch["style"] == "clean"
        assert arch["layers"]["domain"] == ["Application/", "Domain/"]
        assert arch["layers"]["outbound"] == ["Infrastructure/"]

    def test_editing_style_and_layers_keeps_the_teams_layers(self, tmp_path):
        """Reseeding must not overwrite hints the team chose deliberately —
        it only fills in for hints they left alone."""
        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path)
        self._hexagonal(tmp_path)
        write_skill_context(tmp_path, marker)

        custom = {"inbound": ["Web/"], "outbound": ["Data/"], "domain": ["Core/"]}
        self._edit(tmp_path, lambda d: d["architecture"].update(style="clean", layers=custom))
        write_skill_context(tmp_path, marker)

        arch = self._read(tmp_path)["architecture"]
        assert arch["style"] == "clean"
        assert arch["layers"] == custom

    def test_unrecognised_edited_style_falls_back_to_empty_hints(self, tmp_path):
        """A style govkit does not know cannot seed hints; empty lists tell
        skills to ask rather than guess, and rule_templating leaves each
        rule's fallback glob intact."""
        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path)
        self._hexagonal(tmp_path)
        write_skill_context(tmp_path, marker)

        self._edit(tmp_path, lambda d: d["architecture"].update(style="onion"))
        write_skill_context(tmp_path, marker)

        arch = self._read(tmp_path)["architecture"]
        assert arch["style"] == "onion"
        assert arch["layers"] == {"inbound": [], "outbound": [], "domain": []}

    def test_untouched_values_still_refresh_when_derivation_changes(self, tmp_path):
        """The reason this is not "non-empty wins": a team that never edited
        the file must still get updated hints when the repo's shape changes.
        Freezing the first-written value would be its own bug."""
        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path)
        self._hexagonal(tmp_path)
        write_skill_context(tmp_path, marker)
        assert self._read(tmp_path)["architecture"]["style"] == "hexagonal"

        # Repo restructured into Clean Architecture; nothing was hand-edited.
        for layer in ("Application", "Domain", "Infrastructure", "Presentation"):
            (tmp_path / "src" / layer).mkdir(parents=True, exist_ok=True)
        for layer in ("ports", "adapters"):
            (tmp_path / "src" / layer).rmdir()

        write_skill_context(tmp_path, marker)

        arch = self._read(tmp_path)["architecture"]
        assert arch["style"] == "clean"
        assert arch["layers"]["domain"] == ["Application/", "Domain/"]

    def test_detected_signals_always_refresh(self, tmp_path):
        """detected_signals is pure observation of the repo, never a team
        preference, so it must not be caught by preservation."""
        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path)
        self._hexagonal(tmp_path)
        write_skill_context(tmp_path, marker)
        self._edit(tmp_path, lambda d: d["architecture"].update(
            style="clean", detected_signals=["nonsense"],
        ))

        write_skill_context(tmp_path, marker)

        assert self._read(tmp_path)["architecture"]["detected_signals"] == ["hexagonal-shape"]

    def test_fresh_install_is_unaffected(self, tmp_path):
        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path)
        self._hexagonal(tmp_path)
        write_skill_context(tmp_path, marker)

        arch = self._read(tmp_path)["architecture"]
        assert arch["style"] == "hexagonal"
        assert arch["layers"]["domain"] == ["services/", "models/"]

    def test_load_skill_context_ignores_the_provenance_record(self, tmp_path):
        """The bookkeeping govkit writes must not leak into the typed view
        skills consume."""
        from cli.skill_context import load_skill_context, write_skill_context

        marker = _write_marker(tmp_path)
        self._hexagonal(tmp_path)
        write_skill_context(tmp_path, marker)

        ctx = load_skill_context(tmp_path)
        assert ctx is not None
        assert ctx.architecture_style == "hexagonal"
        assert ctx.layers["domain"] == ["services/", "models/"]

    def test_missing_provenance_record_does_not_crash(self, tmp_path):
        """Files written by an older govkit carry no record. Those rewrite as
        before rather than failing — the edit is lost once, then protected."""
        import yaml

        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path)
        self._hexagonal(tmp_path)
        path = tmp_path / ".govkit" / "skill_context.yaml"
        path.write_text(
            yaml.safe_dump({
                "architecture": {"style": "layered", "source_root": "app/", "layers": {}},
                "stack": {}, "pii": {"keyword_list": ["email"]},
            }, sort_keys=False),
            encoding="utf-8",
        )

        write_skill_context(tmp_path, marker)

        data = self._read(tmp_path)
        assert data["architecture"]["style"] == "hexagonal"
        assert data["pii"]["keyword_list"] == ["email"]


class TestPiiKeywordList:
    def test_write_seeds_default_keyword_list(self, tmp_path):
        import yaml

        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path)
        write_skill_context(tmp_path, marker)
        data = yaml.safe_load(
            (tmp_path / ".govkit" / "skill_context.yaml").read_text(encoding="utf-8"),
        )
        assert data["pii"]["keyword_list"] == [
            "email", "phone", "ssn", "dob", "birth", "address", "name",
        ]

    def test_rewrite_preserves_team_tuned_list(self, tmp_path):
        """upgrade/stack apply regenerate skill_context.yaml; a tuned
        keyword_list must survive the rewrite."""
        import yaml

        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path)
        write_skill_context(tmp_path, marker)
        path = tmp_path / ".govkit" / "skill_context.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["pii"]["keyword_list"] = ["email", "iban", "national_id"]
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

        write_skill_context(tmp_path, marker)

        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert data["pii"]["keyword_list"] == ["email", "iban", "national_id"]

    def test_load_returns_pii_keywords(self, tmp_path):
        from cli.skill_context import load_skill_context

        (tmp_path / ".govkit").mkdir(parents=True)
        (tmp_path / ".govkit" / "skill_context.yaml").write_text(
            "architecture: {}\nstack: {}\npii:\n  keyword_list: [email, iban]\n",
            encoding="utf-8",
        )
        ctx = load_skill_context(tmp_path)
        assert ctx is not None
        assert ctx.pii_keywords == ["email", "iban"]


# ---------------------------------------------------------------------------
# architecture.source_root — #86
# ---------------------------------------------------------------------------

BACKEND_LAYERS = ("api", "ports", "services", "models", "adapters", "common")


def _layers_under(prefix: str) -> list[str]:
    """Relative dirs for one hexagonal package rooted at `prefix`."""
    base = f"{prefix}/" if prefix else ""
    return [f"{base}{layer}" for layer in BACKEND_LAYERS]


# (id, directories to create, expected architecture.source_root).
#
# Every layout govkit recognises, plus the two that resolve to "no single
# root". Expected values are written out rather than computed, so a
# derivation that collapsed to one answer cannot satisfy the table.
_SOURCE_ROOT_LAYOUTS = [
    ("flat-at-root", _layers_under(""), ""),
    ("flat-under-src", _layers_under("src"), "src"),
    ("documented-package", _layers_under("src/mypkg"), "src/mypkg"),
    ("multi-service", _layers_under("src/orders") + _layers_under("src/billing"), ""),
    ("unrecognisable", ["docs"], ""),
]

_LAYOUT_IDS = [layout_id for layout_id, _, _ in _SOURCE_ROOT_LAYOUTS]


def _make_layout(target: Path, dirs: list[str]) -> None:
    for rel in dirs:
        (target / rel).mkdir(parents=True, exist_ok=True)


def _emit_architecture(target: Path) -> dict:
    import yaml

    from cli.skill_context import write_skill_context

    marker = _write_marker(target)
    write_skill_context(target, marker)
    data = yaml.safe_load(
        (target / ".govkit" / "skill_context.yaml").read_text(encoding="utf-8"),
    )
    return data["architecture"]


class TestDerivedSourceRoot:
    """`architecture.source_root` must describe the repo it is written into.

    It was hardcoded to `"src/"` from the day the writer shipped, so it was
    wrong for both layouts that are not flat-under-`src/` — including the
    `src/<package>/` shape REPO_STRUCTURE_README.md prescribes as canonical.
    Nothing reads the field yet, which is why the lie went unnoticed; #86
    pins it before a consumer arrives.
    """

    @pytest.mark.parametrize(
        "dirs, expected",
        [(dirs, expected) for _, dirs, expected in _SOURCE_ROOT_LAYOUTS],
        ids=_LAYOUT_IDS,
    )
    def test_source_root_matches_the_layout(self, tmp_path, dirs, expected):
        _make_layout(tmp_path, dirs)

        assert _emit_architecture(tmp_path)["source_root"] == expected

    @pytest.mark.parametrize(
        "dirs",
        [dirs for _, dirs, _ in _SOURCE_ROOT_LAYOUTS],
        ids=_LAYOUT_IDS,
    )
    def test_source_root_agrees_with_detect_source_root(self, tmp_path, dirs):
        """One notion of where the source lives, not two.

        `detect_source_root` already answers this question for codex rule
        placement. The emitted value must be byte-equal to it — a near-miss
        like `src/` beside `src` is the defect #86 reports.
        """
        from cli.detect import detect_source_root

        _make_layout(tmp_path, dirs)

        assert _emit_architecture(tmp_path)["source_root"] == detect_source_root(tmp_path)

    def test_the_layout_table_still_distinguishes_three_answers(self):
        """Guard against the table above going vacuous.

        A parametrize expecting `""` everywhere would pass against the very
        bug these tests exist to catch, and one that emptied would be
        skipped in silence.
        """
        assert len(_SOURCE_ROOT_LAYOUTS) == len(set(_LAYOUT_IDS)) == 5
        assert {expected for _, _, expected in _SOURCE_ROOT_LAYOUTS} == {
            "", "src", "src/mypkg",
        }

    @pytest.mark.parametrize(
        "dirs",
        [dirs for _, dirs, _ in _SOURCE_ROOT_LAYOUTS],
        ids=_LAYOUT_IDS,
    )
    def test_no_layout_emits_the_old_hardcoded_literal(self, tmp_path, dirs):
        """`src/`, with the trailing slash, is a value no derivation
        produces — including for the one layout it happened to describe."""
        _make_layout(tmp_path, dirs)

        assert _emit_architecture(tmp_path)["source_root"] != "src/"


class TestSourceRootProvenanceMigration:
    """The first tunable field whose *derived* value changes for installs
    that already exist.

    Both branches matter and they pull in opposite directions: an untouched
    `src/` must refresh to the real root, while a hand-edited one must not.
    Get the comparison backwards and one of the two silently does the wrong
    thing — an untouched file freezes a value known to be wrong, or a team's
    correction is discarded.
    """

    @staticmethod
    def _read(target):
        import yaml
        return yaml.safe_load(
            (target / ".govkit" / "skill_context.yaml").read_text(encoding="utf-8"),
        )

    @staticmethod
    def _write_pre_change_file(target: Path, live_source_root: str) -> None:
        """Write the file a pre-#86 govkit produced for a hexagonal repo.

        Hand-built rather than produced by `write_skill_context`: today's
        writer records the *derived* root in the provenance block, so a file
        it produced could never reproduce the `src/`-in-both-places state
        this migration is about. Seeding the fixture with the real writer
        would leave both tests passing without exercising anything.
        """
        import yaml

        def hexagonal_layers() -> dict:
            return {
                "inbound": ["api/", "ports/inbound/"],
                "outbound": ["adapters/", "ports/outbound/"],
                "domain": ["services/", "models/"],
            }

        (target / ".govkit").mkdir(parents=True, exist_ok=True)
        (target / ".govkit" / "skill_context.yaml").write_text(
            yaml.safe_dump({
                "architecture": {
                    "style": "hexagonal",
                    "source_root": live_source_root,
                    "layers": hexagonal_layers(),
                    "detected_signals": ["hexagonal-shape"],
                },
                "stack": {},
                "pii": {"keyword_list": ["email"]},
                "_govkit_generated": {
                    "style": "hexagonal",
                    # What the hardcoded writer recorded for every repo.
                    "source_root": "src/",
                    "layers": hexagonal_layers(),
                },
            }, sort_keys=False),
            encoding="utf-8",
        )

    def test_untouched_pre_change_install_picks_up_the_corrected_root(self, tmp_path):
        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path)
        _make_layout(tmp_path, _layers_under("src/mypkg"))
        self._write_pre_change_file(tmp_path, live_source_root="src/")

        write_skill_context(tmp_path, marker)

        assert self._read(tmp_path)["architecture"]["source_root"] == "src/mypkg"

    def test_hand_edited_pre_change_root_survives_the_correction(self, tmp_path):
        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path)
        _make_layout(tmp_path, _layers_under("src/mypkg"))
        self._write_pre_change_file(tmp_path, live_source_root="services/")

        write_skill_context(tmp_path, marker)

        assert self._read(tmp_path)["architecture"]["source_root"] == "services/"

    def test_both_cases_start_from_the_same_recorded_value(self, tmp_path):
        """Neither branch above is decided by the provenance record, which
        reads `src/` in both. Only the live value differs — that is the
        whole mechanism, and this pins that the fixture models it."""
        for live in ("src/", "services/"):
            target = tmp_path / live.strip("/").replace("/", "-")
            target.mkdir()
            self._write_pre_change_file(target, live_source_root=live)

            data = self._read(target)
            assert data["_govkit_generated"]["source_root"] == "src/"
            assert data["architecture"]["source_root"] == live


class TestLoadSkillContextSourceRoot:
    def test_derived_root_round_trips(self, tmp_path):
        from cli.skill_context import load_skill_context

        _make_layout(tmp_path, _layers_under("src/mypkg"))
        _emit_architecture(tmp_path)

        ctx = load_skill_context(tmp_path)
        assert ctx is not None
        assert ctx.source_root == "src/mypkg"

    def test_missing_source_root_is_empty_not_a_guess(self, tmp_path):
        """A file that does not say where the source lives does not license
        the loader to invent `src/`. Empty is the same "govkit cannot tell"
        the derivation now uses."""
        from cli.skill_context import load_skill_context

        (tmp_path / ".govkit").mkdir(parents=True)
        (tmp_path / ".govkit" / "skill_context.yaml").write_text(
            "architecture:\n  style: hexagonal\nstack: {}\n", encoding="utf-8",
        )

        ctx = load_skill_context(tmp_path)
        assert ctx is not None
        assert ctx.source_root == ""

    def test_malformed_source_root_is_empty(self, tmp_path):
        from cli.skill_context import load_skill_context

        (tmp_path / ".govkit").mkdir(parents=True)
        (tmp_path / ".govkit" / "skill_context.yaml").write_text(
            "architecture:\n  source_root: [src]\nstack: {}\n", encoding="utf-8",
        )

        ctx = load_skill_context(tmp_path)
        assert ctx is not None
        assert ctx.source_root == ""


# ---------------------------------------------------------------------------
# architecture.services — #86
# ---------------------------------------------------------------------------

def _multi_service(target: Path, *names: str) -> None:
    for svc in names:
        _make_layout(target, _layers_under(f"src/{svc}"))


# Layouts that describe exactly one place the code lives, and so must not
# grow a `services` list. Written out so the "absent" assertion covers every
# shape rather than whichever one was convenient.
_SINGLE_SERVICE_LAYOUTS = [
    ("flat-at-root", _layers_under("")),
    ("flat-under-src", _layers_under("src")),
    ("documented-package", _layers_under("src/mypkg")),
    ("unrecognisable", ["docs"]),
]


class TestEmittedServices:
    """`architecture.services` says "this repo holds several services".

    Absent for the single-service case, which keeps every file written
    before #86 valid and the common case a two-line read.
    """

    def test_multi_service_layout_names_every_service(self, tmp_path):
        _multi_service(tmp_path, "orders", "billing")

        assert _emit_architecture(tmp_path)["services"] == [
            {"name": "billing", "root": "src/billing"},
            {"name": "orders", "root": "src/orders"},
        ]

    def test_multi_service_layout_reports_no_single_source_root(self, tmp_path):
        """The two fields are read together: `""` plus a list means "several
        services", `""` alone means "govkit could not tell"."""
        _multi_service(tmp_path, "orders", "billing")

        arch = _emit_architecture(tmp_path)
        assert arch["source_root"] == ""
        assert len(arch["services"]) == 2

    @pytest.mark.parametrize(
        "dirs",
        [dirs for _, dirs in _SINGLE_SERVICE_LAYOUTS],
        ids=[layout_id for layout_id, _ in _SINGLE_SERVICE_LAYOUTS],
    )
    def test_single_service_layouts_omit_the_key_entirely(self, tmp_path, dirs):
        _make_layout(tmp_path, dirs)

        assert "services" not in _emit_architecture(tmp_path)

    def test_unrecognisable_repo_is_distinguishable_from_multi_service(self, tmp_path):
        """Both carry `source_root: ""`. The presence of `services` is the
        only thing separating "there are three services" from "govkit could
        not read this repo", so it must not be emitted as an empty list."""
        _make_layout(tmp_path, ["docs"])
        unreadable = _emit_architecture(tmp_path)

        assert unreadable["source_root"] == ""
        assert "services" not in unreadable

    def test_the_single_service_table_is_populated(self):
        assert len(_SINGLE_SERVICE_LAYOUTS) == 4


class TestRepoIsObservedBeforeGovkitWritesToIt:
    """The emitted file must describe the team's repo, not the repo govkit
    just finished modifying.

    Codex places a path-scoped `AGENTS.md` inside each layer folder. When
    there is no single source root — which is exactly the multi-service
    case — those destinations stay root-relative, so `apply` creates
    root-level `api/`, `ports/`, `services/` and `adapters/`. Re-deriving
    afterwards reads that as a flat single-service repo and the service
    list vanishes.

    `style` and `detected_signals` never had this problem: they come from a
    `RepoProfile` built during stack selection, before a byte is written.
    These pin the layout facts to that same observation.
    """

    @staticmethod
    def _apply(target, agent):
        import argparse

        from cli.cmd_apply import cmd_apply

        cmd_apply(argparse.Namespace(
            agent=agent, target=str(target), level="4", type="api",
            ci="github", stack=None, force=False, detect=False,
        ))

    @staticmethod
    def _architecture(target):
        import yaml
        return yaml.safe_load(
            (target / ".govkit" / "skill_context.yaml").read_text(encoding="utf-8"),
        )["architecture"]

    @pytest.mark.parametrize("agent", ["claude-code", "codex", "copilot"])
    def test_apply_records_the_services_that_were_there_before_it_ran(self, tmp_path, agent):
        target = tmp_path / "project"
        target.mkdir()
        _multi_service(target, "orders", "billing")

        self._apply(target, agent)

        arch = self._architecture(target)
        assert [s["name"] for s in arch.get("services", [])] == ["billing", "orders"], (
            f"{agent}: services lost — the file describes the post-install tree"
        )
        assert arch["source_root"] == ""

    def test_codex_really_does_create_the_folders_that_would_hide_them(self, tmp_path):
        """Without this, the codex row above could pass for the wrong reason
        — a future change that stopped creating root-level layer folders
        would make the regression untestable while looking green."""
        target = tmp_path / "project"
        target.mkdir()
        _multi_service(target, "orders", "billing")

        self._apply(target, "codex")

        created = {d.name for d in target.iterdir() if d.is_dir()}
        assert {"api", "ports", "services", "adapters"} <= created

    @pytest.mark.parametrize("agent", ["claude-code", "codex", "copilot"])
    def test_apply_records_the_source_root_that_was_there_before_it_ran(self, tmp_path, agent):
        target = tmp_path / "project"
        target.mkdir()
        _make_layout(target, _layers_under("src/mypkg"))

        self._apply(target, agent)

        assert self._architecture(target)["source_root"] == "src/mypkg"


class TestServicesProvenance:
    """`services` is tunable on the same terms as the rest of the block —
    with one wrinkle the other fields do not have: govkit writes it only
    sometimes, so a team may add a key govkit never derived."""

    @staticmethod
    def _read(target):
        import yaml
        return yaml.safe_load(
            (target / ".govkit" / "skill_context.yaml").read_text(encoding="utf-8"),
        )

    @staticmethod
    def _edit(target, mutate):
        import yaml
        path = target / ".govkit" / "skill_context.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        mutate(data)
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    def test_derived_services_are_recorded_for_the_next_run(self, tmp_path):
        _multi_service(tmp_path, "orders", "billing")
        _emit_architecture(tmp_path)

        record = self._read(tmp_path)["_govkit_generated"]
        assert record["services"] == [
            {"name": "billing", "root": "src/billing"},
            {"name": "orders", "root": "src/orders"},
        ]

    def test_no_services_means_no_record_entry(self, tmp_path):
        _make_layout(tmp_path, _layers_under("src/mypkg"))
        _emit_architecture(tmp_path)

        assert "services" not in self._read(tmp_path)["_govkit_generated"]

    def test_a_hand_added_service_list_survives(self, tmp_path):
        """The plan's promise: "a team that lists services govkit did not
        detect keeps that list". govkit derived nothing here, so there is no
        record entry to compare against — a live value govkit never wrote is
        by definition the team's."""
        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path)
        _make_layout(tmp_path, _layers_under("src/mypkg"))
        write_skill_context(tmp_path, marker)

        theirs = [{"name": "orders", "root": "services/orders"}]
        self._edit(tmp_path, lambda d: d["architecture"].update(services=theirs))
        write_skill_context(tmp_path, marker)

        assert self._read(tmp_path)["architecture"]["services"] == theirs

    def test_a_hand_added_service_list_survives_repeated_writes(self, tmp_path):
        """Once is not enough: the next write records what it derived again,
        so the comparison has to keep coming out the same way."""
        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path)
        _make_layout(tmp_path, _layers_under("src/mypkg"))
        write_skill_context(tmp_path, marker)

        theirs = [{"name": "orders", "root": "services/orders"}]
        self._edit(tmp_path, lambda d: d["architecture"].update(services=theirs))
        for _ in range(3):
            write_skill_context(tmp_path, marker)

        assert self._read(tmp_path)["architecture"]["services"] == theirs

    def test_an_edited_service_entry_survives(self, tmp_path):
        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path)
        _multi_service(tmp_path, "orders", "billing")
        write_skill_context(tmp_path, marker)

        renamed = [
            {"name": "invoicing", "root": "src/billing"},
            {"name": "orders", "root": "src/orders"},
        ]
        self._edit(tmp_path, lambda d: d["architecture"].update(services=renamed))
        write_skill_context(tmp_path, marker)

        assert self._read(tmp_path)["architecture"]["services"] == renamed

    def test_untouched_services_refresh_when_a_service_is_added(self, tmp_path):
        """The reason this is provenance and not "non-empty wins": a repo
        that grows a third service must show it."""
        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path)
        _multi_service(tmp_path, "orders", "billing")
        write_skill_context(tmp_path, marker)
        assert len(self._read(tmp_path)["architecture"]["services"]) == 2

        _multi_service(tmp_path, "shipping")
        write_skill_context(tmp_path, marker)

        assert [s["name"] for s in self._read(tmp_path)["architecture"]["services"]] == [
            "billing", "orders", "shipping",
        ]

    def test_an_install_predating_the_field_picks_it_up(self, tmp_path):
        """An increment-1 file on a multi-service repo has no `services`
        anywhere — not in the live block, not in the record. The new field
        must appear, the same way increment 1's corrected root did.

        Hand-built: a file produced by today's writer would already carry
        the field and prove nothing.
        """
        import yaml

        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path)
        _multi_service(tmp_path, "orders", "billing")
        hexagonal = {
            "inbound": ["api/", "ports/inbound/"],
            "outbound": ["adapters/", "ports/outbound/"],
            "domain": ["services/", "models/"],
        }
        (tmp_path / ".govkit").mkdir(parents=True, exist_ok=True)
        (tmp_path / ".govkit" / "skill_context.yaml").write_text(
            yaml.safe_dump({
                "architecture": {
                    "style": "hexagonal", "source_root": "",
                    "layers": dict(hexagonal), "detected_signals": ["hexagonal-shape"],
                },
                "stack": {},
                "_govkit_generated": {
                    "style": "hexagonal", "source_root": "", "layers": dict(hexagonal),
                },
            }, sort_keys=False),
            encoding="utf-8",
        )

        write_skill_context(tmp_path, marker)

        assert [s["name"] for s in self._read(tmp_path)["architecture"]["services"]] == [
            "billing", "orders",
        ]

    def test_a_live_value_with_no_record_entry_is_treated_as_a_team_edit(self, tmp_path):
        """The general rule `services` needs, stated for a field that has
        always been derived. A record that does not mention a key did not
        write it, so whatever is live came from somewhere else and stays."""
        import yaml

        from cli.skill_context import write_skill_context

        marker = _write_marker(tmp_path)
        _make_layout(tmp_path, _layers_under("src/mypkg"))
        write_skill_context(tmp_path, marker)

        path = tmp_path / ".govkit" / "skill_context.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["architecture"]["source_root"] = "app/"
        del data["_govkit_generated"]["source_root"]
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

        write_skill_context(tmp_path, marker)

        assert self._read(tmp_path)["architecture"]["source_root"] == "app/"


class TestLoadSkillContextServices:
    def _write(self, target: Path, body: str) -> None:
        (target / ".govkit").mkdir(parents=True, exist_ok=True)
        (target / ".govkit" / "skill_context.yaml").write_text(body, encoding="utf-8")

    def test_services_round_trip_as_typed_refs(self, tmp_path):
        from cli.skill_context import ServiceRef, load_skill_context

        _multi_service(tmp_path, "orders", "billing")
        _emit_architecture(tmp_path)

        ctx = load_skill_context(tmp_path)
        assert ctx is not None
        assert ctx.services == [
            ServiceRef(name="billing", root="src/billing"),
            ServiceRef(name="orders", root="src/orders"),
        ]

    def test_single_service_repo_loads_an_empty_list(self, tmp_path):
        """`if ctx.services:` must read as "is this a multi-service repo",
        so the single-service case is falsy rather than None."""
        from cli.skill_context import load_skill_context

        _make_layout(tmp_path, _layers_under("src/mypkg"))
        _emit_architecture(tmp_path)

        ctx = load_skill_context(tmp_path)
        assert ctx is not None
        assert ctx.services == []

    @pytest.mark.parametrize("body", [
        "architecture:\n  services: orders\nstack: {}\n",
        "architecture:\n  services: 3\nstack: {}\n",
        "architecture:\n  services:\n    orders: src/orders\nstack: {}\n",
    ], ids=["scalar-string", "scalar-int", "mapping"])
    def test_a_hand_mangled_services_value_does_not_crash_the_loader(self, tmp_path, body):
        """`list("orders")` would splat into characters; a mapping is the
        other natural mistake. Both degrade to no services rather than
        raising into _post_install_finalize."""
        from cli.skill_context import load_skill_context

        self._write(tmp_path, body)

        ctx = load_skill_context(tmp_path)
        assert ctx is not None
        assert ctx.services == []

    def test_non_dict_entries_are_skipped_not_fatal(self, tmp_path):
        from cli.skill_context import ServiceRef, load_skill_context

        self._write(tmp_path, (
            "architecture:\n"
            "  services:\n"
            "  - orders\n"
            "  - {name: billing, root: src/billing}\n"
            "  - [a, b]\n"
            "stack: {}\n"
        ))

        ctx = load_skill_context(tmp_path)
        assert ctx is not None
        assert ctx.services == [ServiceRef(name="billing", root="src/billing")]

    def test_entries_missing_a_field_are_skipped(self, tmp_path):
        """A ref without a root cannot be acted on; half an entry is worse
        than none."""
        from cli.skill_context import ServiceRef, load_skill_context

        self._write(tmp_path, (
            "architecture:\n"
            "  services:\n"
            "  - {name: orders}\n"
            "  - {root: src/billing}\n"
            "  - {name: shipping, root: src/shipping}\n"
            "  - {name: '', root: src/empty}\n"
            "stack: {}\n"
        ))

        ctx = load_skill_context(tmp_path)
        assert ctx is not None
        assert ctx.services == [ServiceRef(name="shipping", root="src/shipping")]

    def test_wrong_typed_fields_are_skipped(self, tmp_path):
        from cli.skill_context import load_skill_context

        self._write(tmp_path, (
            "architecture:\n"
            "  services:\n"
            "  - {name: 3, root: src/orders}\n"
            "  - {name: billing, root: [src/billing]}\n"
            "stack: {}\n"
        ))

        ctx = load_skill_context(tmp_path)
        assert ctx is not None
        assert ctx.services == []

    def test_services_are_read_from_the_live_block_not_the_record(self, tmp_path):
        """`_govkit_generated` carries its own `services` list. The two are
        made to differ here, so a loader reading the wrong one is visible."""
        from cli.skill_context import ServiceRef, load_skill_context

        self._write(tmp_path, (
            "architecture:\n"
            "  services:\n"
            "  - {name: orders, root: src/orders}\n"
            "stack: {}\n"
            "_govkit_generated:\n"
            "  services:\n"
            "  - {name: billing, root: src/billing}\n"
        ))

        ctx = load_skill_context(tmp_path)
        assert ctx is not None
        assert ctx.services == [ServiceRef(name="orders", root="src/orders")]
