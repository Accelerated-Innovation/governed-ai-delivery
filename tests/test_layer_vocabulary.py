"""Anti-drift tests for the backend hexagonal layer vocabulary.

The payload states the source layout in several places that must agree:
`BOUNDARIES.md` names the primary layers, `REPO_STRUCTURE_README.md`
draws the tree, each backend stack's `TECH_STACK.md` lists the layer
block, `LAYER_IMPLEMENTATION.md` gives the domain's location, and
`ARCH_CONTRACT.md` says what the domain contains. Historically they
disagreed three ways (`domain/` vs top-level `services/` vs
`domain/services/`), which sent teams to build a package the tooling
never looked for.

These tests pin one vocabulary across every doc source, plus the layer
names in the shipped import-linter contract. `cli/skill_context.py`'s
`_STYLE_LAYERS` is asserted in tests/test_skill_context.py, and the
contract's *behaviour* — as opposed to its vocabulary — in
tests/test_importlinter_reference.py.

Only the five *backend* stacks carry hexagonal vocabulary. `python-dbt`
and `databricks-lakehouse` are data stacks with medallion/dbt layering
and are deliberately excluded.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE_ARCH = REPO_ROOT / "docs" / "backend" / "architecture"

# The canonical six, in dependency order (outermost first).
CANONICAL_LAYERS = ("api", "ports", "services", "models", "adapters", "common")

# Stacks whose docs describe hexagonal architecture. The data stacks
# (python-dbt, databricks-lakehouse) use medallion/dbt layering instead.
BACKEND_STACKS = (
    "dotnet-aspnet",
    "go-gin",
    "java-spring-boot",
    "nodejs-fastify",
    "python-fastapi",
)


def _tech_stack_files() -> list[Path]:
    return [BASELINE_ARCH / "TECH_STACK.md"] + [
        REPO_ROOT / "cli" / "stacks" / s / "TECH_STACK.md" for s in BACKEND_STACKS
    ]


def _layer_implementation_files() -> list[Path]:
    return [BASELINE_ARCH / "LAYER_IMPLEMENTATION.md"] + [
        REPO_ROOT / "cli" / "stacks" / s / "LAYER_IMPLEMENTATION.md" for s in BACKEND_STACKS
    ]


def _rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT)).replace("\\", "/")


# `api/       → inbound adapters (HTTP interfaces)`; dotnet uses `Api/`.
_LAYER_BLOCK_LINE = re.compile(r"^\s*([A-Za-z_]+)/\s*(?:→|->)\s*\S", re.MULTILINE)


def _layer_block_names(text: str) -> list[str]:
    """Layer names from a TECH_STACK.md `name/ → purpose` block, lowercased."""
    return [m.group(1).lower() for m in _LAYER_BLOCK_LINE.finditer(text)]


@pytest.mark.parametrize("path", _tech_stack_files(), ids=_rel)
def test_tech_stack_layer_block_lists_canonical_layers(path):
    """Every backend TECH_STACK.md names exactly the canonical six."""
    names = _layer_block_names(path.read_text(encoding="utf-8"))
    assert names, f"{_rel(path)}: no `name/ → purpose` layer block found"
    assert sorted(names) == sorted(CANONICAL_LAYERS), (
        f"{_rel(path)} layer block is {names}, expected {list(CANONICAL_LAYERS)}"
    )


def test_repo_structure_tree_lists_canonical_layers():
    """REPO_STRUCTURE_README.md's `src/<package>/` tree names the six."""
    path = BASELINE_ARCH / "REPO_STRUCTURE_README.md"
    text = path.read_text(encoding="utf-8")
    tree = re.search(r"src/<[^>]+>/\n((?:.*\n)+?)```", text)
    assert tree, f"{_rel(path)}: could not locate the src/<package>/ tree block"
    names = re.findall(r"([a-z_]+)/\s*$", tree.group(1), re.MULTILINE)
    assert sorted(names) == sorted(CANONICAL_LAYERS), (
        f"{_rel(path)} tree is {names}, expected {list(CANONICAL_LAYERS)}"
    )


def test_boundaries_primary_layers_are_canonical():
    """BOUNDARIES.md section 1 lists the same six primary layers."""
    path = BASELINE_ARCH / "BOUNDARIES.md"
    text = path.read_text(encoding="utf-8")
    section = re.search(r"## 1\. Architectural Model\n((?:.*\n)+?)## 2\.", text)
    assert section, f"{_rel(path)}: could not locate section 1"
    names = re.findall(r"^\*\s+`([a-z_]+)/`", section.group(1), re.MULTILINE)
    assert sorted(names) == sorted(CANONICAL_LAYERS), (
        f"{_rel(path)} section 1 lists {names}, expected {list(CANONICAL_LAYERS)}"
    )


@pytest.mark.parametrize("path", _layer_implementation_files(), ids=_rel)
def test_layer_implementation_domain_location_is_canonical(path):
    """The domain layer's `**Location:**` points at the canonical
    top-level packages, not a nested `domain/` wrapper."""
    text = path.read_text(encoding="utf-8")
    location = re.search(r"\*\*Location:\*\*\s*(.+)", text)
    assert location, f"{_rel(path)}: no `**Location:**` line found"
    # Stacks differ in case (`Services/` on .NET) and root (`internal/` on Go).
    line = location.group(1).replace("\\", "/").lower()
    assert "domain/" not in line, (
        f"{_rel(path)} domain location still nests under `domain/`: "
        f"{location.group(1).strip()}"
    )
    assert "services/" in line and "models/" in line, (
        f"{_rel(path)} domain location should name services/ and models/: "
        f"{location.group(1).strip()}"
    )


# `domain/services/` — a nested domain wrapper, always wrong.
_NESTED_DOMAIN = re.compile(r"\bdomain/[A-Za-z_]", re.IGNORECASE)
# A list item, table row, or tree line *declaring* `domain/` as a package.
# Prose that merely mentions it (including saying it does not exist) is fine.
_DECLARED_DOMAIN = re.compile(r"^\s*(?:[*\-+|]|[├└│]+[\s─]*)\s*`?domain/", re.IGNORECASE)


def test_no_backend_doc_declares_a_top_level_domain_package():
    """`domain/` as a package path contradicts the canonical vocabulary.

    Prose using the word "domain" is fine, and so is prose stating that no
    such package exists. What must not appear is a doc *declaring* the
    folder — in a tree, a table, a bullet list — or nesting layers beneath
    it (`domain/services/`).
    """
    offenders = []
    for path in sorted(BASELINE_ARCH.glob("*.md")):
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if _NESTED_DOMAIN.search(line) or _DECLARED_DOMAIN.search(line):
                offenders.append(f"{_rel(path)}:{i}: {line.strip()}")
    assert not offenders, "top-level `domain/` package referenced:\n" + "\n".join(offenders)


def test_no_source_declares_a_use_cases_folder():
    """`use_cases` is phantom vocabulary — no tree, stack, or rule
    declares such a folder. Use cases are expressed as inbound ports."""
    offenders = []
    roots = [BASELINE_ARCH] + [REPO_ROOT / "cli" / "stacks" / s for s in BACKEND_STACKS]
    for root in roots:
        for path in sorted(root.glob("*.md")):
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(r"`use_cases`|use_cases/", line):
                    offenders.append(f"{_rel(path)}:{i}: {line.strip()}")
    assert not offenders, "`use_cases` folder declared:\n" + "\n".join(offenders)


def test_importlinter_reference_names_the_canonical_layers():
    """The shipped contract's `layers` must name the same six packages the
    docs do. Independent siblings share one entry (`api | adapters`), so
    the list is flattened before comparison."""
    import tomllib

    path = REPO_ROOT / "governance" / "backend" / "importlinter-reference.toml"
    config = tomllib.loads(path.read_text(encoding="utf-8"))
    contracts = config["tool"]["importlinter"]["contracts"]
    layered = [c for c in contracts if c.get("type") == "layers"]
    assert len(layered) == 1, f"{_rel(path)}: expected exactly one layers contract"

    names = [
        part.strip()
        for entry in layered[0]["layers"]
        for part in entry.split("|")
    ]
    assert sorted(names) == sorted(CANONICAL_LAYERS), (
        f"{_rel(path)} layers are {names}, expected {list(CANONICAL_LAYERS)}"
    )


def test_pyproject_carries_no_duplicate_importlinter_contract():
    """govkit's own pyproject.toml must not carry a second copy of the
    reference contract.

    It was inert here — govkit's source is `cli/`, not `src/`, and no
    workflow runs `lint-imports` against this repo — which is exactly why
    it drifted unnoticed while claiming to be a template. One copy, under
    test, in governance/backend/."""
    import tomllib

    path = REPO_ROOT / "pyproject.toml"
    config = tomllib.loads(path.read_text(encoding="utf-8"))
    assert "importlinter" not in config.get("tool", {}), (
        "pyproject.toml carries a second import-linter contract; the single "
        "copy lives in governance/backend/importlinter-reference.toml"
    )


# Every boundary-enforcement tool the payload names, across all five stacks.
_BOUNDARY_TOOLS = re.compile(
    r"import-linter|importlinter|lint-imports|dependency-cruiser"
    r"|go-arch-lint|depguard|ArchUnitNET|ArchUnit|NetArchTest",
    re.IGNORECASE,
)


def _overlaid_doc_names() -> set[str]:
    """Filenames that at least one backend stack overlay replaces on install."""
    import yaml

    names: set[str] = set()
    for stack in BACKEND_STACKS:
        overlay_path = REPO_ROOT / "cli" / "stacks" / stack / "overlay.yaml"
        overlay = yaml.safe_load(overlay_path.read_text(encoding="utf-8"))
        for entry in overlay.get("docs") or []:
            names.add(Path(entry["dest"]).name)
    return names


def test_stack_agnostic_backend_docs_name_no_boundary_tool():
    """A baseline doc no overlay replaces ships byte-identical to all five
    backend stacks, so naming one stack's tool makes it wrong for four.

    The tool *is* stated per stack — `TECH_STACK.md`, `LAYER_IMPLEMENTATION.md`
    and `TESTING.md` are overlaid and already name `import-linter`,
    `dependency-cruiser`, `go-arch-lint`, ArchUnit or ArchUnitNET correctly.
    The docs those overlays do not reach must defer to them rather than
    contradict them: a `go-gin` install used to read "enforced with
    `import-linter`" in BOUNDARIES.md beside "enforced via `go-arch-lint`"
    in LAYER_IMPLEMENTATION.md.
    """
    overlaid = _overlaid_doc_names()
    scanned = [p for p in sorted(BASELINE_ARCH.glob("*.md")) if p.name not in overlaid]

    # Guard against a vacuous pass: if the overlay set ever grew to cover
    # everything, this test would silently stop checking anything.
    assert scanned, "no stack-agnostic backend docs left to scan"
    scanned_names = {p.name for p in scanned}
    assert {"BOUNDARIES.md", "ARCH_CONTRACT.md"} <= scanned_names, (
        "BOUNDARIES.md and ARCH_CONTRACT.md are stack-agnostic and must be "
        f"scanned; scanning {sorted(scanned_names)}"
    )

    offenders = []
    for path in scanned:
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if _BOUNDARY_TOOLS.search(line):
                offenders.append(f"{_rel(path)}:{i}: {line.strip()}")
    assert not offenders, (
        "stack-agnostic backend doc names a stack-specific boundary tool "
        "(defer to TECH_STACK.md instead):\n" + "\n".join(offenders)
    )


def test_common_is_not_described_as_holding_data_models():
    """Domain entities belong in `models/`. `common/` is cross-cutting
    concerns and DTOs, and must stay dependency-free."""
    offenders = []
    for path in sorted(BASELINE_ARCH.glob("*.md")):
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "common/" in line and re.search(r"data models", line, re.IGNORECASE):
                offenders.append(f"{_rel(path)}:{i}: {line.strip()}")
    assert not offenders, "`common/` described as holding data models:\n" + "\n".join(offenders)
