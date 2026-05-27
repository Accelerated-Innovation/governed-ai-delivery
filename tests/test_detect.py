"""Tests for cli/detect.py — RepoProfile + signal detectors.

PR 3. Detection is best-effort, target-scoped (per A10 — never walks from
cwd), and emits a confidence label so callers can decide whether to act on
the result. Pure functions; filesystem reads only.
"""

import pytest


class TestRepoProfileShape:
    def test_empty_repo_returns_empty_profile_not_error(self, tmp_path):
        from cli.detect import build_profile

        prof = build_profile(tmp_path)
        assert prof.target == tmp_path
        assert prof.detected_languages == []
        assert prof.detected_frameworks == []
        assert prof.detected_ci == []
        assert prof.detected_test_packages == []
        assert prof.detected_project_paths == []
        assert prof.detected_api_style is None
        assert prof.detected_llm_signals == []
        assert prof.detected_architecture_signals == []


class TestLanguageDetection:
    def test_csharp_detected_via_csproj(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "Api.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk.Web"></Project>\n', encoding="utf-8"
        )
        prof = build_profile(tmp_path)
        assert "csharp" in prof.detected_languages

    def test_csharp_detected_via_solution(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "MySolution.sln").write_text("Microsoft Visual Studio Solution File\n", encoding="utf-8")
        prof = build_profile(tmp_path)
        assert "csharp" in prof.detected_languages

    def test_csharp_detected_via_global_json(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "global.json").write_text('{"sdk":{"version":"8.0.100"}}', encoding="utf-8")
        prof = build_profile(tmp_path)
        assert "csharp" in prof.detected_languages

    def test_python_detected_via_pyproject(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n', encoding="utf-8")
        prof = build_profile(tmp_path)
        assert "python" in prof.detected_languages

    def test_python_detected_via_requirements(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "requirements.txt").write_text("requests\n", encoding="utf-8")
        prof = build_profile(tmp_path)
        assert "python" in prof.detected_languages

    def test_typescript_detected_via_tsconfig(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "tsconfig.json").write_text('{"compilerOptions":{}}', encoding="utf-8")
        prof = build_profile(tmp_path)
        assert "typescript" in prof.detected_languages

    def test_typescript_detected_via_package_json_dep(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "package.json").write_text(
            '{"name":"x","devDependencies":{"typescript":"^5.0.0"}}', encoding="utf-8",
        )
        prof = build_profile(tmp_path)
        assert "typescript" in prof.detected_languages

    def test_go_detected_via_go_mod(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "go.mod").write_text("module example.com/foo\n\ngo 1.22\n", encoding="utf-8")
        prof = build_profile(tmp_path)
        assert "go" in prof.detected_languages

    def test_java_detected_via_pom(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "pom.xml").write_text("<project></project>\n", encoding="utf-8")
        prof = build_profile(tmp_path)
        assert "java" in prof.detected_languages

    def test_java_detected_via_gradle(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "build.gradle.kts").write_text("plugins { kotlin(\"jvm\") }\n", encoding="utf-8")
        prof = build_profile(tmp_path)
        assert "java" in prof.detected_languages


class TestFrameworkDetection:
    def test_aspnet_core_detected_via_sdk_attribute(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "Api.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk.Web">\n  <PropertyGroup><TargetFramework>net8.0</TargetFramework></PropertyGroup>\n</Project>\n',
            encoding="utf-8",
        )
        prof = build_profile(tmp_path)
        assert "aspnet-core" in prof.detected_frameworks

    def test_aspnet_core_detected_via_framework_reference(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "Api.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk">\n'
            '  <ItemGroup>\n'
            '    <FrameworkReference Include="Microsoft.AspNetCore.App" />\n'
            '  </ItemGroup>\n'
            '</Project>\n',
            encoding="utf-8",
        )
        prof = build_profile(tmp_path)
        assert "aspnet-core" in prof.detected_frameworks

    def test_aspnet_core_not_detected_for_console_app(self, tmp_path):
        """R3: don't substring-match 'Microsoft.AspNetCore.*' against
        unrelated package names like AuthenticationCore."""
        from cli.detect import build_profile

        (tmp_path / "Util.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk">\n'
            '  <ItemGroup>\n'
            '    <PackageReference Include="Microsoft.AspNetCore.Authentication.Core" Version="1.0.0" />\n'
            '  </ItemGroup>\n'
            '</Project>\n',
            encoding="utf-8",
        )
        prof = build_profile(tmp_path)
        # Console SDK + no Microsoft.AspNetCore.App framework reference → not aspnet-core
        assert "aspnet-core" not in prof.detected_frameworks

    def test_fastapi_detected_in_pyproject(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname="x"\ndependencies = ["fastapi>=0.110", "uvicorn"]\n',
            encoding="utf-8",
        )
        prof = build_profile(tmp_path)
        assert "fastapi" in prof.detected_frameworks

    def test_fastapi_detected_in_requirements(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "requirements.txt").write_text("fastapi==0.110.0\nuvicorn\n", encoding="utf-8")
        prof = build_profile(tmp_path)
        assert "fastapi" in prof.detected_frameworks

    def test_fastify_detected_in_package_json(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "package.json").write_text(
            '{"dependencies":{"fastify":"^4.0.0"}}', encoding="utf-8",
        )
        prof = build_profile(tmp_path)
        assert "fastify" in prof.detected_frameworks

    def test_spring_boot_detected_in_pom(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "pom.xml").write_text(
            '<project>\n  <dependencies>\n'
            '    <dependency>\n'
            '      <groupId>org.springframework.boot</groupId>\n'
            '      <artifactId>spring-boot-starter-web</artifactId>\n'
            '    </dependency>\n'
            '  </dependencies>\n</project>\n',
            encoding="utf-8",
        )
        prof = build_profile(tmp_path)
        assert "spring-boot" in prof.detected_frameworks

    def test_gin_detected_in_go_mod(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "go.mod").write_text(
            "module example.com/foo\n\ngo 1.22\n\nrequire github.com/gin-gonic/gin v1.10.0\n",
            encoding="utf-8",
        )
        prof = build_profile(tmp_path)
        assert "gin" in prof.detected_frameworks


class TestCIDetection:
    def test_github_actions_detected(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        (tmp_path / ".github" / "workflows" / "ci.yml").write_text(
            "name: CI\non: [push]\n", encoding="utf-8",
        )
        prof = build_profile(tmp_path)
        assert "github-actions" in prof.detected_ci

    def test_azure_pipelines_detected_via_root_yaml(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "azure-pipelines.yml").write_text("trigger:\n  - main\n", encoding="utf-8")
        prof = build_profile(tmp_path)
        assert "azure-pipelines" in prof.detected_ci

    def test_both_ci_systems_detected_when_both_present(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: x\n", encoding="utf-8")
        (tmp_path / "azure-pipelines.yml").write_text("trigger:\n", encoding="utf-8")

        prof = build_profile(tmp_path)
        assert "github-actions" in prof.detected_ci
        assert "azure-pipelines" in prof.detected_ci


class TestArchitectureSignals:
    def test_hexagonal_signals_detected(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "src" / "ports").mkdir(parents=True)
        (tmp_path / "src" / "adapters").mkdir(parents=True)
        prof = build_profile(tmp_path)
        assert "hexagonal-shape" in prof.detected_architecture_signals

    def test_clean_architecture_signals_detected(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "src" / "Application").mkdir(parents=True)
        (tmp_path / "src" / "Domain").mkdir(parents=True)
        (tmp_path / "src" / "Infrastructure").mkdir(parents=True)
        prof = build_profile(tmp_path)
        assert "clean-shape" in prof.detected_architecture_signals

    def test_layered_signals_detected(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "src" / "Controllers").mkdir(parents=True)
        (tmp_path / "src" / "Services").mkdir(parents=True)
        (tmp_path / "src" / "Repositories").mkdir(parents=True)
        prof = build_profile(tmp_path)
        assert "layered-shape" in prof.detected_architecture_signals

    def test_no_signal_when_no_matching_folders(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "src" / "randomthing").mkdir(parents=True)
        prof = build_profile(tmp_path)
        assert prof.detected_architecture_signals == []


class TestLLMSignals:
    def test_litellm_detected_in_pyproject(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname="x"\ndependencies = ["litellm>=1.0", "fastapi"]\n',
            encoding="utf-8",
        )
        prof = build_profile(tmp_path)
        assert "litellm" in prof.detected_llm_signals

    def test_openai_sdk_detected_in_requirements(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "requirements.txt").write_text("openai==1.40.0\n", encoding="utf-8")
        prof = build_profile(tmp_path)
        assert "openai" in prof.detected_llm_signals

    def test_langchain_detected_in_package_json(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "package.json").write_text(
            '{"dependencies":{"langchain":"^0.3.0"}}', encoding="utf-8",
        )
        prof = build_profile(tmp_path)
        assert "langchain" in prof.detected_llm_signals

    def test_no_llm_signals_in_plain_repo(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname="x"\ndependencies = ["fastapi"]\n', encoding="utf-8",
        )
        prof = build_profile(tmp_path)
        assert prof.detected_llm_signals == []


class TestTargetScoping:
    """A10: build_profile takes an explicit target. Detectors must never walk
    from cwd. In a monorepo, scoping per-app is essential."""

    def test_only_scans_under_target(self, tmp_path):
        from cli.detect import build_profile

        # Root has a Python signal:
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
        # Subdir has a separate .NET app:
        sub = tmp_path / "apps" / "api"
        sub.mkdir(parents=True)
        (sub / "Api.csproj").write_text('<Project Sdk="Microsoft.NET.Sdk.Web"></Project>\n', encoding="utf-8")

        # Profile of the subdir should NOT pick up the root pyproject.
        prof = build_profile(sub)
        assert "csharp" in prof.detected_languages
        assert "python" not in prof.detected_languages


class TestConfidence:
    """Each signal carries an implicit confidence level. build_profile reports
    it via a parallel structure so callers (cmd_apply, doctor, calibrate)
    can decide whether to act on a detection."""

    def test_language_confidence_high_when_multiple_signals(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "Api.csproj").write_text('<Project Sdk="Microsoft.NET.Sdk.Web"></Project>\n', encoding="utf-8")
        (tmp_path / "global.json").write_text('{"sdk":{"version":"8.0"}}', encoding="utf-8")

        prof = build_profile(tmp_path)
        assert prof.language_confidence("csharp") == "high"

    def test_language_confidence_medium_when_single_signal(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "go.mod").write_text("module x\ngo 1.22\n", encoding="utf-8")

        prof = build_profile(tmp_path)
        assert prof.language_confidence("go") == "medium"

    def test_language_confidence_none_for_unsignaled(self, tmp_path):
        from cli.detect import build_profile

        prof = build_profile(tmp_path)
        assert prof.language_confidence("csharp") == "none"


class TestInferStack:
    """infer_stack(profile) -> (stack_id, confidence) — picks the best
    matching bundled stack given the detected signals. Used by cmd_apply
    to downgrade the silent default to a "detected" assumption when
    confidence is high."""

    def test_dotnet_repo_infers_dotnet_aspnet(self, tmp_path):
        from cli.detect import build_profile, infer_stack

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "Api.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk.Web"></Project>\n', encoding="utf-8",
        )
        (tmp_path / "global.json").write_text('{"sdk":{}}', encoding="utf-8")

        prof = build_profile(tmp_path)
        stack_id, confidence = infer_stack(prof)
        assert stack_id == "dotnet-aspnet"
        assert confidence == "high"

    def test_python_fastapi_repo_infers_python_fastapi(self, tmp_path):
        from cli.detect import build_profile, infer_stack

        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname="x"\ndependencies = ["fastapi"]\n', encoding="utf-8",
        )

        prof = build_profile(tmp_path)
        stack_id, confidence = infer_stack(prof)
        assert stack_id == "python-fastapi"
        # Single language signal + framework match — medium or high acceptable.
        assert confidence in ("medium", "high")

    def test_typescript_fastify_repo_infers_nodejs_fastify(self, tmp_path):
        from cli.detect import build_profile, infer_stack

        (tmp_path / "tsconfig.json").write_text('{"compilerOptions":{}}', encoding="utf-8")
        (tmp_path / "package.json").write_text(
            '{"dependencies":{"fastify":"^4.0.0","typescript":"^5"}}', encoding="utf-8",
        )

        prof = build_profile(tmp_path)
        stack_id, confidence = infer_stack(prof)
        assert stack_id == "nodejs-fastify"
        assert confidence == "high"

    def test_go_gin_repo_infers_go_gin(self, tmp_path):
        from cli.detect import build_profile, infer_stack

        (tmp_path / "go.mod").write_text(
            "module x\ngo 1.22\nrequire github.com/gin-gonic/gin v1.10.0\n",
            encoding="utf-8",
        )

        prof = build_profile(tmp_path)
        stack_id, _ = infer_stack(prof)
        assert stack_id == "go-gin"

    def test_java_spring_repo_infers_java_spring_boot(self, tmp_path):
        from cli.detect import build_profile, infer_stack

        (tmp_path / "pom.xml").write_text(
            '<project><dependencies><dependency><groupId>org.springframework.boot</groupId>'
            '<artifactId>spring-boot-starter-web</artifactId></dependency></dependencies></project>',
            encoding="utf-8",
        )

        prof = build_profile(tmp_path)
        stack_id, _ = infer_stack(prof)
        assert stack_id == "java-spring-boot"

    def test_empty_repo_returns_none(self, tmp_path):
        from cli.detect import build_profile, infer_stack

        prof = build_profile(tmp_path)
        stack_id, confidence = infer_stack(prof)
        assert stack_id is None
        assert confidence == "none"

    def test_python_without_fastapi_still_infers_python_fastapi(self, tmp_path):
        """A Python repo without fastapi still gets the python-fastapi
        default — it's the only Python stack today and a reasonable starting
        point."""
        from cli.detect import build_profile, infer_stack

        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname="x"\ndependencies = ["requests"]\n', encoding="utf-8",
        )

        prof = build_profile(tmp_path)
        stack_id, confidence = infer_stack(prof)
        assert stack_id == "python-fastapi"
        # No fastapi marker → confidence is medium at best.
        assert confidence in ("medium", "low")

    def test_mismatched_framework_wins_over_language_alone(self, tmp_path):
        """If language=python but no fastapi, and language=csharp + aspnet-core,
        csharp wins (more specific signal)."""
        from cli.detect import build_profile, infer_stack

        (tmp_path / "pyproject.toml").write_text('[project]\nname="x"\n', encoding="utf-8")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "Api.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk.Web"></Project>\n', encoding="utf-8",
        )

        prof = build_profile(tmp_path)
        stack_id, _ = infer_stack(prof)
        assert stack_id == "dotnet-aspnet"
