"""The shipped ArchUnit template must actually enforce BOUNDARIES.md.

Two layers of coverage. The structural tests run everywhere and catch the
failure mode that recurs in this repo — a contract drifting out of step with
BOUNDARIES.md, a layer dropped, an edge quietly removed. The `e2e` tests run
the real linter inside a real Maven project, and catch what no assertion on
the file's text can: an ArchUnit API misuse that compiles and passes
vacuously.

The second layer was added by #109, reversing the trade #93 made. That trade
— structural only, because ArchUnit needs a JVM and Maven in CI — was
defensible when it was made and turned out to be wrong. Executing the *.NET*
template found two real defects in it, both of which had already passed their
structural checks:

  ResideInNamespace matched namespaces exactly, so a violation in
  Api.Controllers passed at 8/8 green; and the base namespace was
  interpolated into a regex unescaped, so `Contoso.Billing` also matched
  `ContosoXBilling.*`.

The argument that Java was safe — ArchUnit's `..api..` is recursive by
construction, unlike ArchUnitNET's string form — was correct, and
`TestPackageMatching` below now proves it instead of asserting it. Being
right for the right reason and being verified are different things, and only
one of them survives the next edit.
"""

import os
import re
import shutil
import subprocess
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


def test_template_tells_the_reader_to_verify_their_own_wiring(template):
    """A reader must be able to learn from the file how far its guarantee
    reaches.

    This test previously asserted the opposite — that the template disclosed
    it was *not* executed by govkit — which was accurate until #109 added the
    Maven fixtures. The claim changed; the obligation did not. CI proves the
    rules are correct, and can say nothing about whether an adopter pointed
    `@AnalyzeClasses` at the right package or put the class in a source set
    their build actually runs. That gap is the reader's to close, so the file
    has to name it.
    """
    lowered = template.lower()
    assert "verify it once" in lowered or "verify it yourself" in lowered, (
        "template does not tell adopters to confirm the rules fire in their "
        "own project"
    )
    assert "deliberate violation" in lowered, (
        "template does not say how to verify — introducing a known violation "
        "is the check that catches a mis-wired base package or source set"
    )


BASE = "com.example.myservice"
BASE_PATH = BASE.replace(".", "/")
CLASS_FOR = {"api": "Routes", "ports": "Repo", "services": "Core",
             "models": "Entity", "adapters": "Db", "common": "Log"}

# Allowed edges populated, so a rule that over-forbids surfaces as a failing
# conforming case rather than passing unnoticed.
CONFORMING = {
    "common": [], "models": [],
    "ports": ["models", "common"],
    "services": ["ports", "models", "common"],
    "adapters": ["ports", "services", "models", "common"],
    "api": ["ports", "models", "common"],
}
# No edges at all — the base for violation cases, so each is tested alone.
ISOLATED = {layer: [] for layer in LAYERS}

POM = """<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>myservice</artifactId>
  <version>1.0</version>
  <properties>
    <maven.compiler.source>17</maven.compiler.source>
    <maven.compiler.target>17</maven.compiler.target>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
  </properties>
  <dependencies>
    <dependency>
      <groupId>com.tngtech.archunit</groupId>
      <artifactId>archunit-junit5</artifactId>
      <version>1.3.0</version>
      <scope>test</scope>
    </dependency>
  </dependencies>
  <build>
    <plugins>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-surefire-plugin</artifactId>
        <version>3.2.5</version>
      </plugin>
    </plugins>
  </build>
</project>
"""

_MVN = shutil.which("mvn") or shutil.which("mvn.cmd")
_JAVA = shutil.which("java")


def _java_source(package: str, name: str, uses: list[str]) -> str:
    imports = "".join(f"import {BASE}.{u}.{CLASS_FOR[u]};\n" for u in uses)
    fields = "".join(f"    private {CLASS_FOR[u]} field{u.title()};\n" for u in uses)
    return f"package {BASE}.{package};\n\n{imports}\npublic class {name} {{\n{fields}}}\n"


def _write_project(root: Path, spec: dict, extra=None, decoys=None) -> None:
    src = root / "src"
    if src.exists():
        shutil.rmtree(src)
    (root / "pom.xml").write_text(POM, encoding="utf-8")
    plan = {layer: list(uses) for layer, uses in spec.items()}
    if extra:
        layer, target = extra
        plan[layer] = [target]
    for layer, uses in plan.items():
        path = src / "main" / "java" / BASE_PATH / layer / f"{CLASS_FOR[layer]}.java"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_java_source(layer, CLASS_FOR[layer], uses), encoding="utf-8")
    for package, name, body in decoys or []:
        path = src / "main" / "java" / package.replace(".", "/") / f"{name}.java"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    # The template ships ready to compile once the placeholder matches.
    test = src / "test" / "java" / BASE_PATH / "architecture" / "ArchitectureTest.java"
    test.parent.mkdir(parents=True, exist_ok=True)
    test.write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")


def _mvn_test(root: Path) -> tuple[int, str]:
    result = subprocess.run(
        [_MVN, "-q", "-B", "test"], cwd=root,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return result.returncode, (result.stdout or "") + (result.stderr or "")


def _rules_executed(root: Path) -> int:
    """How many @ArchTest rules surefire actually ran.

    A build can go green having executed nothing — the JVM stack's silent-pass
    mode, and what ci/<flavour>/boundary-gate-jvm.yml checks in production.
    """
    reports = (root / "target" / "surefire-reports").glob("*ArchitectureTest*.xml")
    total = 0
    for report in reports:
        match = re.search(r'tests="(\d+)"', report.read_text(encoding="utf-8"))
        if match:
            total += int(match.group(1))
    return total


@pytest.fixture(scope="module")
def maven_project(tmp_path_factory) -> Path:
    """One project, one dependency resolution, reused by every case."""
    root = tmp_path_factory.mktemp("archunit")
    _write_project(root, CONFORMING)
    # Resolve and compile only — the cases below each run the tests anyway, so
    # a full `mvn test` here would just be a sixteenth JVM start.
    result = subprocess.run(
        [_MVN, "-q", "-B", "test-compile"], cwd=root,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    out = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        message = f"maven test-compile failed: {out[-400:]}"
        if os.environ.get("CI"):
            pytest.fail(message)
        pytest.skip(f"{message} (offline?)")
    return root


@pytest.mark.e2e
@pytest.mark.skipif(
    _MVN is None or _JAVA is None,
    reason="JDK or Maven not installed",
)
class TestAgainstRealArchUnit:
    """The template, run by Maven inside a real project."""

    def test_conforming_repo_passes(self, maven_project):
        _write_project(maven_project, CONFORMING)
        code, out = _mvn_test(maven_project)
        assert _rules_executed(maven_project) > 1, (
            f"the architecture rules did not run, so a clean build proves "
            f"nothing:\n{out[-1000:]}"
        )
        assert code == 0, f"conforming repo rejected:\n{out[-1500:]}"

    @pytest.mark.parametrize(
        ("label", "layer", "target"),
        [
            ("api -> services", "api", "services"),
            ("api -> adapters", "api", "adapters"),
            ("adapters -> api", "adapters", "api"),
            ("services -> adapters", "services", "adapters"),
            ("services -> api", "services", "api"),
            ("ports -> services", "ports", "services"),
            ("ports -> adapters", "ports", "adapters"),
            ("models -> services", "models", "services"),
            ("models -> ports", "models", "ports"),
            ("common -> models", "common", "models"),
            ("common -> services", "common", "services"),
        ],
    )
    def test_forbidden_edge_is_rejected(self, maven_project, label, layer, target):
        """Each edge is tested against a skeleton holding only that edge.

        Java permits import cycles where Go does not, so a fully-wired tree
        would work here — but isolating the edge still proves *which* rule
        fires rather than that something, somewhere, objected.
        """
        _write_project(maven_project, ISOLATED, extra=(layer, target))
        code, out = _mvn_test(maven_project)
        assert _rules_executed(maven_project) > 1, f"rules did not run:\n{out[-800:]}"
        assert code != 0, f"{label} was permitted:\n{out[-1200:]}"


@pytest.mark.e2e
@pytest.mark.skipif(
    _MVN is None or _JAVA is None,
    reason="JDK or Maven not installed",
)
class TestPackageMatching:
    """The three cases the .NET template got wrong, asked of this one.

    ArchUnit's `..api..` should be recursive, should require a whole package
    segment rather than a substring, and `@AnalyzeClasses` should not reach
    into a look-alike sibling of the base package. All three were true when
    checked — but the equivalent reasoning about ArchUnitNET was also
    convincing, and it was wrong twice.
    """

    def test_a_violation_in_a_nested_package_is_rejected(self, maven_project):
        """`api/controllers/` is where Spring MVC puts controllers, so this is
        the normal case, not an edge case. The ArchUnitNET analogue of this
        shipped broken."""
        _write_project(
            maven_project, CONFORMING,
            decoys=[(f"{BASE}.api.controllers", "UserController",
                     f"package {BASE}.api.controllers;\n\n"
                     f"import {BASE}.services.Core;\n\n"
                     "public class UserController {\n    private Core core;\n}\n")],
        )
        code, out = _mvn_test(maven_project)
        assert _rules_executed(maven_project) > 1, f"rules did not run:\n{out[-800:]}"
        assert code != 0, (
            "a violation in api.controllers was not caught — `..api..` is not "
            f"reaching nested packages:\n{out[-1200:]}"
        )

    def test_a_package_merely_containing_the_layer_name_is_not_a_layer(self, maven_project):
        """`legacyapi` is not the `api` layer. Matching it would reject repos
        that comply."""
        _write_project(
            maven_project, CONFORMING,
            decoys=[(f"{BASE}.legacyapi", "Legacy",
                     f"package {BASE}.legacyapi;\n\n"
                     f"import {BASE}.services.Core;\n\n"
                     "public class Legacy {\n    private Core core;\n}\n")],
        )
        code, out = _mvn_test(maven_project)
        assert _rules_executed(maven_project) > 1, f"rules did not run:\n{out[-800:]}"
        assert code == 0, (
            "a package whose name merely contains 'api' was treated as the api "
            f"layer:\n{out[-1200:]}"
        )

    def test_a_lookalike_sibling_base_package_is_not_analysed(self, maven_project):
        """The direct analogue of the ArchUnitNET escaping defect: with a base
        of `com.example.myservice`, types in `com.example.myserviceextra` must
        stay outside the analysis."""
        _write_project(
            maven_project, CONFORMING,
            decoys=[("com.example.myserviceextra.api", "Outside",
                     "package com.example.myserviceextra.api;\n\n"
                     f"import {BASE}.services.Core;\n\n"
                     "public class Outside {\n    private Core core;\n}\n")],
        )
        code, out = _mvn_test(maven_project)
        assert _rules_executed(maven_project) > 1, f"rules did not run:\n{out[-800:]}"
        assert code == 0, (
            "com.example.myserviceextra.api was judged against this service's "
            f"layer rules — @AnalyzeClasses is matching a raw prefix:\n{out[-1200:]}"
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
