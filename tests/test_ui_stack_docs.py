"""Anti-drift tests for the per-stack UI architecture doc sets.

UI_DOCS_PARITY_AND_DESIGN_REFERENCES_PLAN.md. Each per-stack folder under
`docs/ui/architecture/` (react, angular, nextjs) must be individually fully
functional: a core doc set every stack ships, plus intentionally
nextjs-only server-first docs. Styling history made the gap visible —
Angular shipped no styling guidance at all, and react's TECH_STACK.md
mandated Tailwind while COMPONENT_CONVENTIONS.md still showed CSS modules,
so generated code followed whichever doc the agent read first.

These tests pin: the core per-stack inventory, BRAND.md as the single
source of brand values (plan decision D7 — STYLING.md carries mechanism,
never brand values), the removal of react's CSS-module contradiction (D2),
and the per-stack doc lists in every agent's base and L4 instruction files.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
UI_ARCH = REPO_ROOT / "docs" / "ui" / "architecture"

UI_STACKS = ("react", "angular", "nextjs")

# Docs every per-stack folder ships. nextjs additionally ships the
# server-first docs (APPLICATION_STRUCTURE, API_BOUNDARY,
# SERVER_CLIENT_BOUNDARIES) that have no react/angular equivalent —
# react/angular structure lives in MVVM_CONTRACT.md §3.
CORE_STACK_DOCS = (
    "TECH_STACK.md",
    "COMPONENT_CONVENTIONS.md",
    "STATE_MANAGEMENT.md",
    "STYLING.md",
    "TESTING.md",
)

# Per-agent instruction-file directory, per cli/agent_layout.py naming.
AGENT_INSTRUCTION_DIRS = {
    "claude-code": "claude-md",
    "codex": "agents-md",
    "copilot": "copilot-instructions",
}


def _read(path: Path) -> str:
    assert path.is_file(), f"missing: {path.relative_to(REPO_ROOT)}"
    return path.read_text(encoding="utf-8")


class TestCoreStackDocInventory:
    @pytest.mark.parametrize("stack", UI_STACKS)
    @pytest.mark.parametrize("doc", CORE_STACK_DOCS)
    def test_stack_ships_core_doc(self, stack, doc):
        path = UI_ARCH / stack / doc
        assert path.is_file(), (
            f"docs/ui/architecture/{stack}/{doc} missing — every UI stack "
            f"ships the core doc set ({', '.join(CORE_STACK_DOCS)})"
        )
        assert path.stat().st_size > 0, f"{path.name} is empty"


class TestStylingContract:
    @pytest.mark.parametrize("stack", UI_STACKS)
    def test_styling_names_brand_contract_as_source_of_truth(self, stack):
        """D7: brand values live in BRAND.md; STYLING.md maps them to the
        stack's mechanism and must say so."""
        text = _read(UI_ARCH / stack / "STYLING.md")
        assert "docs/ui/design/BRAND.md" in text, (
            f"{stack}/STYLING.md must name docs/ui/design/BRAND.md as the source of brand values"
        )

    def test_react_component_conventions_no_css_module_references(self):
        """D2: Tailwind (per TECH_STACK.md) is react's styling source of
        truth; the stale CSS-module mentions are the contradiction."""
        text = _read(UI_ARCH / "react" / "COMPONENT_CONVENTIONS.md")
        for stale in ("module.css", "CSS module", "CSS modules"):
            assert stale not in text, (
                f"react/COMPONENT_CONVENTIONS.md still references '{stale}' — "
                "contradicts TECH_STACK.md's Tailwind-only styling stack"
            )

    def test_react_component_conventions_points_at_styling_doc(self):
        text = _read(UI_ARCH / "react" / "COMPONENT_CONVENTIONS.md")
        assert "STYLING.md" in text, (
            "react/COMPONENT_CONVENTIONS.md must point at STYLING.md for "
            "styling rules instead of restating them"
        )

    def test_angular_component_conventions_use_jest_not_vitest(self):
        """angular/TECH_STACK.md declares Jest + Angular Testing Library;
        COMPONENT_CONVENTIONS.md historically said Vitest with vi.mocked/
        vitest-axe examples — the same read-order contradiction as react's
        CSS modules."""
        text = _read(UI_ARCH / "angular" / "COMPONENT_CONVENTIONS.md")
        for stale in ("Vitest", "vi.mocked", "vitest-axe"):
            assert stale not in text, (
                f"angular/COMPONENT_CONVENTIONS.md still references '{stale}' — "
                "contradicts TECH_STACK.md's Jest testing stack"
            )

    def test_angular_styling_is_component_scoped(self):
        """D6: Angular styles are component-scoped with BRAND tokens; no
        Tailwind mandate."""
        text = _read(UI_ARCH / "angular" / "STYLING.md")
        assert "component-scoped" in text.lower(), (
            "angular/STYLING.md must define the component-scoped styling "
            "posture approved as plan decision D6"
        )


class TestBrandSourcesTraceability:
    def test_brand_template_has_brand_sources_line(self):
        """D7: the BRAND.md template records where external brand guides
        live, so completed values are traceable to their source."""
        text = _read(REPO_ROOT / "docs" / "ui" / "design" / "BRAND.md")
        assert "Brand sources" in text, (
            "docs/ui/design/BRAND.md must carry a 'Brand sources' line for "
            "recording external brand guides used to complete it"
        )


class TestAsymmetryReadme:
    """docs/ui/architecture/README.md records why the nextjs folder ships
    more docs than react/angular, so a future 'parity' pass doesn't
    manufacture server-first docs for SPA stacks. It is repo-side only —
    the manifests' governed lists name entries explicitly and must not
    pick it up."""

    def test_readme_names_the_intentionally_nextjs_only_docs(self):
        text = _read(UI_ARCH / "README.md")
        for doc in (
            "APPLICATION_STRUCTURE.md",
            "API_BOUNDARY.md",
            "SERVER_CLIENT_BOUNDARIES.md",
        ):
            assert doc in text, f"README.md must name nextjs-only doc {doc}"
        assert "MVVM_CONTRACT.md" in text, (
            "README.md must say react/angular structure lives in MVVM_CONTRACT.md"
        )

    @pytest.mark.parametrize("agent", sorted(AGENT_INSTRUCTION_DIRS))
    def test_readme_is_not_installed_by_any_manifest(self, agent):
        manifest_text = (
            REPO_ROOT / "agents" / agent / "manifest.json"
        ).read_text(encoding="utf-8")
        assert "docs/ui/architecture/README.md" not in manifest_text, (
            f"{agent}: the asymmetry README is repo-side documentation and "
            "must not be installed"
        )
        # Would sweep the README (and anything else) into every UI install.
        assert '"docs/ui/architecture/"' not in manifest_text, (
            f"{agent}: manifests must name docs/ui/architecture/ entries "
            "explicitly, never the whole directory"
        )


class TestAgentInstructionDocLists:
    """A doc added to the payload but unreachable from the instruction files
    is invisible to the agents that are supposed to read it. Reachable means
    either the exact path appears in the file's doc list, or the file
    instructs reading all files under docs/ui/architecture/ (the copilot L4
    and all L5 instruction files use the directory-wide form)."""

    @pytest.mark.parametrize("agent", sorted(AGENT_INSTRUCTION_DIRS))
    @pytest.mark.parametrize("ui_type,stack", [("ui-react", "react"), ("ui-angular", "angular")])
    @pytest.mark.parametrize("prefix", ["", "l4-"])
    @pytest.mark.parametrize("doc", ["STYLING.md", "TESTING.md"])
    def test_instruction_file_reaches_added_docs(self, agent, ui_type, stack, prefix, doc):
        path = (
            REPO_ROOT / "agents" / agent / AGENT_INSTRUCTION_DIRS[agent] / f"{prefix}{ui_type}.md"
        )
        text = _read(path)
        explicit = f"docs/ui/architecture/{stack}/{doc}" in text
        directory_wide = "all files under `docs/ui/architecture/" in text
        assert explicit or directory_wide, (
            f"{path.relative_to(REPO_ROOT)} must make "
            f"docs/ui/architecture/{stack}/{doc} reachable — list it "
            "explicitly or instruct reading all files under "
            "docs/ui/architecture/"
        )
