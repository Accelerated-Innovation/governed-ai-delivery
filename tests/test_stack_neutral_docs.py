"""Backend docs that no stack overlay replaces must not state stack-specific rules.

Only six architecture docs vary per stack. Everything else under
`docs/backend/` ships byte-identical to `python-fastapi`, `nodejs-fastify`,
`go-gin`, `java-spring-boot` and `dotnet-aspnet` alike — so a rule naming
Pydantic, FastAPI or SQLAlchemy in one of them is wrong for four stacks out of
five.

That is not cosmetic. `ARCH_CONTRACT.md` §10 instructs AI agents to cite this
contract when generating plans or code, and it told them the domain "must have
no external dependencies other than standard Python", that ports are "pure
Python interfaces", and that secrets go through Pydantic's `BaseSettings`. A Go
team's agent, following the contract it was pointed at, would have been reading
Python rules.

**Rules versus illustrations.** A fenced code block is an illustration — the
reader can see it is written in one language and translate. A sentence in prose
is a rule, and the reader has no signal that it does not apply to them. So this
module scans prose only, and code fences are permitted provided the document
says up front that its examples are illustrative
(`test_documents_with_code_examples_label_them`).

The narrower sibling of this check is
`test_layer_vocabulary.py::test_stack_agnostic_backend_docs_name_no_boundary_tool`,
which pins the same property for boundary-enforcement tools specifically.
"""

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DOCS = REPO_ROOT / "docs" / "backend"
ARCHITECTURE = BACKEND_DOCS / "architecture"

BACKEND_STACKS = (
    "dotnet-aspnet", "go-gin", "java-spring-boot", "nodejs-fastify", "python-fastapi",
)

# Names that identify one stack's language, framework or libraries. Both
# directions are covered: pasting `Fastify` into a baseline doc is the same
# defect as leaving `FastAPI` there.
_STACK_SPECIFIC = re.compile(
    r"\b("
    r"Python|Pydantic|pydantic|FastAPI|fastapi|SQLAlchemy|BaseSettings|httpx|boto3|"
    r"uvicorn|asyncio|"
    r"Fastify|TypeScript|Node\.js|pino|Vitest|"
    r"Gin|goroutine|"
    r"Spring Boot|JUnit|Maven|Gradle|"
    r"ASP\.NET|xUnit|NUnit|NuGet"
    r")\b"
)

# `docs/backend/guides/` is excluded on purpose: those guides document specific
# third-party tools (Guardrails AI, for one) that genuinely are Python
# libraries. Naming Python there describes the tool, not this service's stack.
SCANNED_DIRS = (ARCHITECTURE, BACKEND_DOCS / "evaluation")

_CODE_FENCE = re.compile(r"^\s*```")
_PY_FENCE = re.compile(r"^\s*```(python|py)\b")


def _overlaid_doc_names() -> set[str]:
    """Filenames at least one backend stack overlay replaces on install."""
    names: set[str] = set()
    for stack in BACKEND_STACKS:
        overlay = yaml.safe_load(
            (REPO_ROOT / "cli" / "stacks" / stack / "overlay.yaml").read_text(encoding="utf-8")
        )
        for entry in overlay.get("docs") or []:
            names.add(Path(entry["dest"]).name)
    return names


def _stack_agnostic_docs() -> list[Path]:
    overlaid = _overlaid_doc_names()
    docs: list[Path] = []
    for directory in SCANNED_DIRS:
        if directory.exists():
            docs.extend(p for p in sorted(directory.glob("*.md")) if p.name not in overlaid)
    return docs


def _rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT)).replace("\\", "/")


def _prose_lines(path: Path):
    """Yield (line_number, text) for prose only, skipping fenced code."""
    in_fence = False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if _CODE_FENCE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield number, line


def test_the_scan_covers_the_documents_it_should():
    """Guard against a vacuous pass: if the overlay set ever grew to cover
    everything, or a directory moved, the checks below would silently stop
    examining anything."""
    docs = {p.name for p in _stack_agnostic_docs()}
    assert docs, "no stack-agnostic backend docs found to scan"
    for expected in ("ARCH_CONTRACT.md", "BOUNDARIES.md", "REPO_STRUCTURE_README.md"):
        assert expected in docs, f"{expected} must be scanned; scanning {sorted(docs)}"


@pytest.mark.parametrize("path", _stack_agnostic_docs(), ids=_rel)
def test_stack_agnostic_doc_states_no_stack_specific_rule(path):
    offenders = [
        f"{_rel(path)}:{number}: {line.strip()}"
        for number, line in _prose_lines(path)
        if _STACK_SPECIFIC.search(line)
    ]
    assert not offenders, (
        "a doc that ships identically to all five backend stacks states a rule "
        "naming one stack's language or libraries. Defer to TECH_STACK.md or "
        "LAYER_IMPLEMENTATION.md, which are overlaid per stack:\n"
        + "\n".join(offenders)
    )


# Docs known to carry language-specific code examples. Asserted rather than
# discovered so that removing the examples from one is a deliberate act: a
# per-doc `pytest.skip` for "no examples here" would let this check quietly
# shrink to nothing, which is the failure mode the rest of this suite exists
# to prevent.
DOCS_WITH_EXAMPLES = {
    "CLI_CONVENTIONS.md",
    "CROSS_CUTTING_CONCERNS.md",
    "ERROR_MAPPING.md",
}


def test_documents_with_code_examples_label_them():
    """Code fences may be written in one language — the reader can see which.
    What they must not do is read as the required approach, so any doc
    carrying them says so once, near the top."""
    found, offenders = set(), []
    for path in _stack_agnostic_docs():
        text = path.read_text(encoding="utf-8")
        if not any(_PY_FENCE.match(line) for line in text.splitlines()):
            continue
        found.add(path.name)
        head = "\n".join(text.splitlines()[:40]).lower()
        if "illustrative" not in head:
            offenders.append(
                f"{_rel(path)} carries language-specific code examples but never "
                "says they are illustrative — a reader on another stack has no "
                "signal that the surrounding rules are language-neutral while "
                "the examples are not"
            )
        elif "tech_stack.md" not in head:
            offenders.append(
                f"{_rel(path)} labels its examples but does not point readers at "
                "TECH_STACK.md for their own stack's equivalents"
            )
    assert not offenders, "\n".join(offenders)
    assert found == DOCS_WITH_EXAMPLES, (
        f"the set of docs carrying code examples changed: {sorted(found)} vs "
        f"{sorted(DOCS_WITH_EXAMPLES)}. Update DOCS_WITH_EXAMPLES deliberately — "
        "silently dropping to an empty set would make this check vacuous."
    )
