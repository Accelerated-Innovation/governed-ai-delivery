"""The shipped ArchUnitNET template must actually enforce BOUNDARIES.md.

Unlike the JVM template — which govkit checks structurally, because running
ArchUnit needs a JVM and Maven — this one is **executed**. `dotnet test` is
cheap enough to run in CI, and running it earned its keep immediately:

`ResideInNamespace("MyService.Api")` matches that namespace *exactly*. A
controller in `MyService.Api.Controllers`, where ASP.NET projects normally put
them, is not in the Api layer as far as the rule is concerned. The first draft
of the template used it, and a `MyService.Api.Controllers.UserController`
depending on `MyService.Services.Core` left the suite green at 8/8 — the
template would have under-enforced in essentially every real project.

No structural assertion would have caught that. It is why
`test_nested_namespace_violation_is_rejected` below exists, and why the
template uses `ResideInNamespaceMatching` with an explicit
`^Base[.]Layer($|[.])` pattern.

Marked `e2e` — these shell out to `dotnet` and are excluded from the fast
loop. They skip when the SDK is absent; CI asserts it is present so a skip
cannot pass for a pass there.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = REPO_ROOT / "governance" / "backend" / "ArchitectureTest.cs.template"

BASE = "MyService"
LAYERS = ("Api", "Ports", "Services", "Models", "Adapters", "Common")

_DOTNET = shutil.which("dotnet")

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(_DOTNET is None, reason=".NET SDK not installed"),
]

SRC_CSPROJ = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <RootNamespace>MyService</RootNamespace>
  </PropertyGroup>
</Project>
"""

TEST_CSPROJ = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <IsPackable>false</IsPackable>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="TngTech.ArchUnitNET.xUnit" Version="0.13.3" />
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.11.1" />
    <PackageReference Include="xunit" Version="2.9.2" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.8.2" />
  </ItemGroup>
  <ItemGroup>
    <ProjectReference Include="../../src/MyService/MyService.csproj" />
  </ItemGroup>
</Project>
"""

# (layer, type name, dependency as (namespace, type)) for the conforming tree.
CONFORMING = [
    ("Common", "Log", []),
    ("Models", "Entity", []),
    ("Ports", "Repo", [("Models", "Entity")]),
    ("Services", "Core", [("Ports", "Repo"), ("Models", "Entity")]),
    ("Adapters", "Db", [("Ports", "Repo"), ("Services", "Core")]),
    ("Api", "Routes", [("Ports", "Repo")]),
]

MINIMAL = [(layer, name, []) for layer, name, _ in CONFORMING]


def _csharp(namespace: str, name: str, uses: list[tuple[str, str]]) -> str:
    usings = "".join(f"using {BASE}.{ns};\n" for ns, _ in uses)
    fields = "".join(f"    private readonly {t}? _{t.lower()};\n" for _, t in uses)
    return f"{usings}\nnamespace {BASE}.{namespace};\n\npublic class {name}\n{{\n{fields}}}\n"


def _write_tree(root: Path, layers, extra: tuple[str, str, tuple[str, str]] | None = None):
    src = root / "src" / "MyService"
    if src.exists():
        shutil.rmtree(src)
    (src).mkdir(parents=True, exist_ok=True)
    (src / "MyService.csproj").write_text(SRC_CSPROJ, encoding="utf-8")
    spec = {layer: (name, list(uses)) for layer, name, uses in layers}
    if extra:
        layer, name, dependency = extra
        spec[layer] = (name, [dependency])
    for layer, (name, uses) in spec.items():
        path = src / layer / f"{name}.cs"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_csharp(layer, name, uses), encoding="utf-8")


@pytest.fixture(scope="module")
def dotnet_project(tmp_path_factory) -> Path:
    """One restore shared by every case — it is the slow part."""
    root = tmp_path_factory.mktemp("archunitnet")
    tests = root / "tests" / "MyService.ArchTests"
    tests.mkdir(parents=True)
    (tests / "MyService.ArchTests.csproj").write_text(TEST_CSPROJ, encoding="utf-8")
    # The template ships with a header comment block; it is valid C# as-is.
    (tests / "ArchitectureTest.cs").write_text(
        TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
    _write_tree(root, CONFORMING)
    result = subprocess.run(
        [_DOTNET, "restore", "tests/MyService.ArchTests"], cwd=root,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        shell=os.name == "nt",
    )
    if result.returncode != 0:
        message = f"dotnet restore failed: {result.stdout[-400:]}{result.stderr[-400:]}"
        if os.environ.get("CI"):
            pytest.fail(message)
        pytest.skip(f"{message} (offline?)")
    return root


def _dotnet_test(root: Path) -> tuple[int, str]:
    result = subprocess.run(
        [_DOTNET, "test", "tests/MyService.ArchTests", "--nologo", "-v", "q"],
        cwd=root, capture_output=True, text=True, encoding="utf-8",
        errors="replace", shell=os.name == "nt",
    )
    out = (result.stdout or "") + (result.stderr or "")
    assert out.strip(), "dotnet test produced no output — it did not run"
    return result.returncode, out


def _assert_rules_ran(out: str) -> None:
    """A run that executed zero tests proves nothing, and `dotnet test`
    reports success when a filter matches nothing."""
    match = re.search(r"Total:\s*(\d+)", out)
    assert match, f"no test count in output:\n{out[-800:]}"
    assert int(match.group(1)) > 1, (
        f"only {match.group(1)} test(s) ran — the architecture rules were not "
        f"picked up:\n{out[-800:]}"
    )


def test_conforming_repo_passes(dotnet_project):
    _write_tree(dotnet_project, CONFORMING)
    code, out = _dotnet_test(dotnet_project)
    _assert_rules_ran(out)
    assert code == 0, f"conforming repo rejected:\n{out[-1500:]}"


@pytest.mark.parametrize(
    ("label", "layer", "name", "dependency"),
    [
        ("Api -> Services", "Api", "Routes", ("Services", "Core")),
        ("Api -> Adapters", "Api", "Routes", ("Adapters", "Db")),
        ("Adapters -> Api", "Adapters", "Db", ("Api", "Routes")),
        ("Services -> Adapters", "Services", "Core", ("Adapters", "Db")),
        ("Services -> Api", "Services", "Core", ("Api", "Routes")),
        ("Ports -> Services", "Ports", "Repo", ("Services", "Core")),
        ("Ports -> Adapters", "Ports", "Repo", ("Adapters", "Db")),
        ("Models -> Services", "Models", "Entity", ("Services", "Core")),
        ("Models -> Ports", "Models", "Entity", ("Ports", "Repo")),
        ("Common -> Models", "Common", "Log", ("Models", "Entity")),
        ("Common -> Services", "Common", "Log", ("Services", "Core")),
    ],
)
def test_forbidden_edge_is_rejected(dotnet_project, label, layer, name, dependency):
    _write_tree(dotnet_project, MINIMAL, extra=(layer, name, dependency))
    code, out = _dotnet_test(dotnet_project)
    _assert_rules_ran(out)
    assert code != 0, f"{label} was permitted:\n{out[-1200:]}"


def test_nested_namespace_violation_is_rejected(dotnet_project):
    """The bug this test suite exists for.

    ASP.NET projects put controllers in `Api/Controllers/`, i.e. the
    `MyService.Api.Controllers` namespace. `ResideInNamespace("MyService.Api")`
    matches only the exact namespace, so a violation one level down passed
    silently — 8/8 green on a repo where a controller reached into Services.
    """
    _write_tree(dotnet_project, CONFORMING)
    nested = dotnet_project / "src" / "MyService" / "Api" / "Controllers"
    nested.mkdir(parents=True, exist_ok=True)
    (nested / "UserController.cs").write_text(
        _csharp("Api.Controllers", "UserController", [("Services", "Core")]),
        encoding="utf-8",
    )
    code, out = _dotnet_test(dotnet_project)
    _assert_rules_ran(out)
    assert code != 0, (
        "a violation in a nested namespace was not caught — the layer "
        f"predicates are matching exact namespaces only:\n{out[-1200:]}"
    )


def test_nested_namespace_conforming_type_still_passes(dotnet_project):
    """The other half: covering sub-namespaces must not create false
    positives on allowed edges."""
    _write_tree(dotnet_project, CONFORMING)
    nested = dotnet_project / "src" / "MyService" / "Api" / "Controllers"
    nested.mkdir(parents=True, exist_ok=True)
    (nested / "UserController.cs").write_text(
        _csharp("Api.Controllers", "UserController", [("Ports", "Repo")]),
        encoding="utf-8",
    )
    code, out = _dotnet_test(dotnet_project)
    _assert_rules_ran(out)
    assert code == 0, f"a conforming nested type was rejected:\n{out[-1200:]}"


def test_template_uses_recursive_namespace_matching():
    """Structural guard that runs without the SDK, so the regression above
    is visible in the fast loop too."""
    text = TEMPLATE.read_text(encoding="utf-8")
    body = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("*")
    )
    for layer in LAYERS:
        assert f"[.]{layer}($|[.])" in body, (
            f"the {layer} layer predicate does not cover sub-namespaces; "
            "an exact ResideInNamespace match misses Api.Controllers and the like"
        )
    assert "ResideInNamespace(" not in body, (
        "the exact-match overload matches only the named namespace — use "
        "ResideInNamespaceMatching with an explicit pattern"
    )


def test_template_names_the_real_nuget_package():
    """`ArchUnitNET.xUnit` does not exist on NuGet; the package is published
    under `TngTech.`. A template naming the wrong one fails at restore."""
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "TngTech.ArchUnitNET.xUnit" in text
    assert not re.search(r'(?<!TngTech\.)"ArchUnitNET\.xUnit"', text)
