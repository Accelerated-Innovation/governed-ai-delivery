"""The shipped ArchUnit template must express BOUNDARIES.md.

**This is a weaker guarantee than the other three references get, and the
difference is deliberate.** `test_importlinter_reference.py`,
`test_dependency_cruiser_reference.py` and `test_go_arch_lint_reference.py`
each run the real linter against generated skeletons, so those contracts
cannot claim an enforcement they do not deliver. Doing the same here needs a
JVM and Maven in every CI run, for a template that changes rarely — the plan
weighs that trade and chooses structural assertions.

So these tests check that the template *says* the right thing, not that it
*does* the right thing. They will not catch an ArchUnit API misuse that
compiles and passes vacuously. What they do catch is the failure mode that
actually recurs in this repo: a contract drifting out of step with
BOUNDARIES.md — a layer dropped, a forbidden edge quietly removed, the
placeholder package renamed in one place but not another.

Two structural guards stand in for what execution would prove:

- the template carries its own "did any class get imported" check, because a
  wrong base package is the JVM equivalent of import-linter's zero dependency
  count;
- the gate asserts the architecture test actually *ran*, since a test class
  the build never executes is the JVM equivalent of a linter that analysed
  nothing. That assertion is checked in tests/test_boundary_gate_dispatch.py.

If the template starts changing often, revisit and add a JVM to CI.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = REPO_ROOT / "governance" / "backend" / "ArchitectureTest.java.template"
BOUNDARIES = REPO_ROOT / "docs" / "backend" / "architecture" / "BOUNDARIES.md"

LAYERS = ("api", "ports", "services", "models", "adapters", "common")

# Every edge BOUNDARIES.md forbids, as (source layer, forbidden target).
# Mirrors the rule set in governance/backend/go-arch-lint-reference.yml and
# dependency-cruiser-reference.cjs so all four contracts stay comparable.
FORBIDDEN_EDGES = [
    ("api", "services"),
    ("api", "adapters"),
    ("adapters", "api"),
    ("services", "adapters"),
    ("services", "api"),
    ("ports", "services"),
    ("ports", "adapters"),
    ("ports", "api"),
    ("models", "services"),
    ("models", "ports"),
    ("models", "adapters"),
    ("models", "api"),
    ("common", "api"),
    ("common", "adapters"),
    ("common", "services"),
    ("common", "ports"),
    ("common", "models"),
]


@pytest.fixture(scope="module")
def template() -> str:
    assert TEMPLATE.is_file(), f"{TEMPLATE} does not exist"
    return TEMPLATE.read_text(encoding="utf-8")


def test_template_names_every_canonical_layer(template):
    for layer in LAYERS:
        assert f"..{layer}.." in template, (
            f"template never references the {layer!r} layer as an ArchUnit "
            f"package identifier (`..{layer}..`)"
        )


@pytest.mark.parametrize("source, target", FORBIDDEN_EDGES)
def test_template_forbids_every_edge_boundaries_forbids(template, source, target):
    """Each forbidden edge must appear as a rule whose `that()` names the
    source layer and whose `dependOnClassesThat()` names the target."""
    rules = re.findall(
        r"noClasses\(\)(.*?);", template, re.DOTALL,
    )
    assert rules, "template declares no `noClasses()` rules"
    matched = any(
        f'resideInAPackage("..{source}..")' in rule
        and re.search(
            r"dependOnClassesThat\(\)\s*\.resideInAnyPackage\(([^)]*)\)"
            r"|dependOnClassesThat\(\)\s*\.resideInAPackage\(([^)]*)\)",
            rule,
            re.DOTALL,
        )
        and f'"..{target}.."' in rule.split("dependOnClassesThat")[-1]
        for rule in rules
    )
    assert matched, (
        f"no rule forbids {source} -> {target}; BOUNDARIES.md forbids it and "
        "the other three reference contracts express it"
    )


def test_template_guards_against_an_unresolved_base_package(template):
    """A wrong `@AnalyzeClasses` package imports zero classes — the JVM
    equivalent of import-linter's `Analyzed N files, 0 dependencies`. The
    template must notice rather than report every rule satisfied."""
    assert "@AnalyzeClasses" in template, "template does not declare @AnalyzeClasses"
    assert "JavaClasses" in template, (
        "template has no rule receiving JavaClasses, so it cannot check that "
        "the base package resolved to anything"
    )
    assert re.search(r"isEmpty\(\)", template), (
        "template never checks that the imported class set is non-empty"
    )


def test_template_placeholder_package_is_consistent(template):
    """Adopters replace one placeholder. Two base packages means half a
    rename, and the half that stays behind points ArchUnit at nothing.

    Subpackages of the base are fine — the file's own `package` declaration is
    one — so the check is that every placeholder shares the base, not that
    they are all identical.
    """
    base = "com.example.myservice"
    placeholders = set(re.findall(r"com\.example\.[a-z0-9_.]+", template))
    assert placeholders, "template declares no com.example.* placeholder package"

    strays = {p for p in placeholders if p != base and not p.startswith(f"{base}.")}
    assert not strays, (
        f"template uses a placeholder outside the {base!r} base package: "
        f"{sorted(strays)} — an adopter renaming the base would miss these"
    )
    assert f'packages = "{base}"' in template, (
        "@AnalyzeClasses must point at the base package itself, not a subpackage"
    )


def test_template_tells_the_reader_it_is_not_executed_by_govkit(template):
    """The honesty this plan exists to protect: the other three contracts are
    verified against their real linter, this one is not, and a reader must be
    able to learn that from the file itself."""
    lowered = template.lower()
    assert "structural" in lowered or "not executed" in lowered, (
        "template does not disclose that govkit checks it structurally rather "
        "than by running ArchUnit"
    )


def test_boundaries_still_forbids_what_the_template_forbids():
    """Anti-drift in the other direction: if BOUNDARIES.md ever grants one of
    these edges, this test set is what makes the contradiction visible."""
    text = BOUNDARIES.read_text(encoding="utf-8")
    section = re.search(r"### Forbidden:\n((?:.*\n)+?)\n", text)
    assert section, "could not locate BOUNDARIES.md's Forbidden list"
    forbidden = section.group(1)
    assert "`api` importing `services`" in forbidden
    assert re.search(r"`services`.*importing any adapter", forbidden)
    assert re.search(r"`models` importing `ports` or `services`", forbidden)
