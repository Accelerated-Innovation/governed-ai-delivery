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
        assert prof.detected_source_root == ""
        assert prof.detected_services == []


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

    def test_nextjs_detected_without_backend_stack_mapping(self, tmp_path):
        from cli.detect import build_profile, infer_stack

        (tmp_path / "package.json").write_text(
            '{"dependencies":{"next":"^16.0.0","react":"^19.0.0"}}',
            encoding="utf-8",
        )
        prof = build_profile(tmp_path)
        assert "nextjs" in prof.detected_frameworks
        assert infer_stack(prof)[0] != "nextjs"

    def test_react_vite_detected(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "package.json").write_text(
            '{"dependencies":{"react":"^19.0.0"},"devDependencies":{"vite":"^7.0.0"}}',
            encoding="utf-8",
        )
        prof = build_profile(tmp_path)
        assert "react-vite" in prof.detected_frameworks

    def test_angular_detected_from_package_or_workspace_file(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "angular.json").write_text("{}", encoding="utf-8")
        prof = build_profile(tmp_path)
        assert "angular" in prof.detected_frameworks

    def test_tailwindcss_detected(self, tmp_path):
        from cli.detect import build_profile

        (tmp_path / "package.json").write_text(
            '{"devDependencies":{"tailwindcss":"^4","@tailwindcss/postcss":"^4"}}',
            encoding="utf-8",
        )
        prof = build_profile(tmp_path)
        assert "tailwindcss" in prof.detected_frameworks

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

    def test_hexagonal_detected_under_src_package(self, tmp_path):
        """REPO_STRUCTURE_README.md documents `src/<package>/api/...`, one
        level below src/. Detection must recognise its own prescribed
        layout — otherwise a conforming repo gets style="unknown" and
        empty layer hints."""
        from cli.detect import build_profile

        for layer in ("api", "ports", "services", "models", "adapters", "common"):
            (tmp_path / "src" / "mypkg" / layer).mkdir(parents=True)
        prof = build_profile(tmp_path)
        assert "hexagonal-shape" in prof.detected_architecture_signals

    def test_hexagonal_detected_for_multi_service_layout(self, tmp_path):
        """`src/{orders,billing}/` — several services sharing one install,
        expressed as multiple import-linter containers."""
        from cli.detect import build_profile

        for svc in ("orders", "billing"):
            for layer in ("api", "ports", "services", "models", "adapters", "common"):
                (tmp_path / "src" / svc / layer).mkdir(parents=True)
        prof = build_profile(tmp_path)
        assert "hexagonal-shape" in prof.detected_architecture_signals

    def test_no_signal_for_unrelated_package_children(self, tmp_path):
        """Scanning one level deeper must not invent signals from folders
        that happen to sit under a package."""
        from cli.detect import build_profile

        for name in ("utils", "helpers", "scripts"):
            (tmp_path / "src" / "mypkg" / name).mkdir(parents=True)
        prof = build_profile(tmp_path)
        assert prof.detected_architecture_signals == []

    def test_scan_does_not_reach_two_levels_below_src(self, tmp_path):
        """The walk is bounded to direct children of src/ so this stays a
        cheap fixed-cost check rather than a full-tree scan."""
        from cli.detect import build_profile

        (tmp_path / "src" / "a" / "b" / "ports").mkdir(parents=True)
        (tmp_path / "src" / "a" / "b" / "adapters").mkdir(parents=True)
        prof = build_profile(tmp_path)
        assert prof.detected_architecture_signals == []

    def test_skip_dirs_are_not_treated_as_packages(self, tmp_path):
        """A vendored tree under src/ must not supply architecture signals."""
        from cli.detect import build_profile

        (tmp_path / "src" / "node_modules" / "ports").mkdir(parents=True)
        (tmp_path / "src" / "node_modules" / "adapters").mkdir(parents=True)
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

    def test_claude_agent_sdk_detected(self, tmp_path):
        """The SDK that drives the Claude Code CLI. It never pulls in
        `anthropic`, so the substring match on that name misses it entirely —
        the false negative this check was reported for."""
        from cli.detect import build_profile

        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname="x"\ndependencies = ["claude-agent-sdk>=0.1"]\n',
            encoding="utf-8",
        )
        prof = build_profile(tmp_path)
        assert prof.detected_llm_signals

    @pytest.mark.parametrize(
        ("filename", "content"),
        [
            ("app.csproj", '<PackageReference Include="Azure.AI.OpenAI" Version="2.0.0" />'),
            ("app.csproj", '<PackageReference Include="Microsoft.SemanticKernel" Version="1.0" />'),
            ("go.mod", "require github.com/sashabaranov/go-openai v1.32.0"),
            ("go.mod", "require github.com/tmc/langchaingo v0.1.12"),
            ("build.gradle", "implementation 'dev.langchain4j:langchain4j:0.35.0'"),
            ("build.gradle.kts", 'implementation("org.springframework.ai:spring-ai-core:1.0.0")'),
        ],
    )
    def test_llm_detected_in_stack_dependency_files(self, tmp_path, filename, content):
        """govkit ships dotnet-aspnet, go-gin and java-spring-boot stacks, but
        the scan only read pyproject / requirements / package.json / pom.xml —
        so D008 false-negatived on three of its own supported stacks
        regardless of which SDK was in use."""
        from cli.detect import build_profile

        (tmp_path / filename).write_text(content, encoding="utf-8")
        prof = build_profile(tmp_path)
        assert prof.detected_llm_signals, f"{filename} with {content!r} not detected"

    def test_package_json_found_below_the_target_root(self, tmp_path):
        """Only the root package.json was checked, unlike every other
        dependency file, so a JS monorepo hid its dependencies from the scan."""
        from cli.detect import build_profile

        app = tmp_path / "apps" / "web"
        app.mkdir(parents=True)
        (app / "package.json").write_text(
            '{"dependencies":{"@anthropic-ai/sdk":"^0.30.0"}}', encoding="utf-8",
        )
        prof = build_profile(tmp_path)
        assert prof.detected_llm_signals

    def test_plain_dotnet_and_go_repos_stay_clean(self, tmp_path):
        """Widening the file scan must not widen false positives."""
        from cli.detect import build_profile

        (tmp_path / "app.csproj").write_text(
            '<PackageReference Include="Microsoft.AspNetCore.App" />', encoding="utf-8",
        )
        (tmp_path / "go.mod").write_text("require github.com/gin-gonic/gin v1.10.0", encoding="utf-8")
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

    def test_dbt_project_repo_infers_python_dbt(self, tmp_path):
        from cli.detect import build_profile, infer_stack

        (tmp_path / "models" / "staging").mkdir(parents=True)
        (tmp_path / "models" / "intermediate").mkdir(parents=True)
        (tmp_path / "models" / "marts").mkdir(parents=True)
        (tmp_path / "dbt_project.yml").write_text("name: customer_analytics\n", encoding="utf-8")

        prof = build_profile(tmp_path)
        stack_id, confidence = infer_stack(prof)

        assert "dbt" in prof.detected_frameworks
        assert stack_id == "python-dbt"
        assert confidence == "high"

    def test_databricks_bundle_repo_infers_databricks_lakehouse(self, tmp_path):
        from cli.detect import build_profile, infer_stack

        (tmp_path / "resources").mkdir()
        (tmp_path / "src").mkdir()
        (tmp_path / "databricks.yml").write_text(
            "bundle:\n  name: customer_analytics\ninclude:\n  - resources/*.yml\n",
            encoding="utf-8",
        )
        (tmp_path / "resources" / "jobs.yml").write_text(
            "resources:\n  jobs:\n    refresh_customer_dim:\n      name: refresh_customer_dim\n",
            encoding="utf-8",
        )
        (tmp_path / "pyproject.toml").write_text('[project]\nname="x"\n', encoding="utf-8")

        prof = build_profile(tmp_path)
        stack_id, confidence = infer_stack(prof)

        assert "databricks-lakehouse" in prof.detected_frameworks
        assert stack_id == "databricks-lakehouse"
        assert confidence == "high"

    def test_mixed_dbt_and_databricks_signals_prefer_python_dbt(self, tmp_path):
        """dbt-on-Databricks is still a dbt project shape by default."""
        from cli.detect import build_profile, infer_stack

        (tmp_path / "resources").mkdir()
        (tmp_path / "models" / "staging").mkdir(parents=True)
        (tmp_path / "models" / "intermediate").mkdir(parents=True)
        (tmp_path / "models" / "marts").mkdir(parents=True)
        (tmp_path / "databricks.yml").write_text(
            "bundle:\n  name: customer_analytics\ninclude:\n  - resources/*.yml\n",
            encoding="utf-8",
        )
        (tmp_path / "resources" / "jobs.yml").write_text("resources:\n  jobs: {}\n", encoding="utf-8")
        (tmp_path / "dbt_project.yml").write_text("name: customer_analytics\n", encoding="utf-8")

        prof = build_profile(tmp_path)
        stack_id, confidence = infer_stack(prof)

        assert "dbt" in prof.detected_frameworks
        assert "databricks-lakehouse" in prof.detected_frameworks
        assert stack_id == "python-dbt"
        assert confidence == "high"

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


class TestFindRecursivePruning:
    """_find_recursive must prune noise dirs during traversal (not after).
    Walking into node_modules / .venv etc. is what makes detection slow on
    large repos. These tests pin both behaviour (right file set) and
    implementation (os.walk + dirnames pruning)."""

    def _make_tree(self, tmp_path):
        # Files at varying depths, inside and outside noise dirs.
        (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
        (tmp_path / "src" / "Api").mkdir(parents=True)
        (tmp_path / "src" / "Api" / "Api.csproj").write_text("", encoding="utf-8")
        # Inside a skip_dir at depth 1 — must be ignored.
        (tmp_path / "node_modules" / "pkg" / "subpkg").mkdir(parents=True)
        (tmp_path / "node_modules" / "pkg" / "pyproject.toml").write_text("", encoding="utf-8")
        (tmp_path / "node_modules" / "pkg" / "subpkg" / "deep.csproj").write_text("", encoding="utf-8")
        # Inside .venv at depth 1 — must be ignored.
        (tmp_path / ".venv" / "lib").mkdir(parents=True)
        (tmp_path / ".venv" / "lib" / "pyproject.toml").write_text("", encoding="utf-8")
        # File beyond max_depth=4 → must be ignored.
        deep = tmp_path / "a" / "b" / "c" / "d"
        deep.mkdir(parents=True)
        (deep / "too_deep.csproj").write_text("", encoding="utf-8")

    def test_returns_files_outside_skip_dirs_only(self, tmp_path):
        from cli.detect import _find_recursive

        self._make_tree(tmp_path)
        py = {p.name for p in _find_recursive(tmp_path, "pyproject.toml")}
        cs = {p.relative_to(tmp_path).as_posix() for p in _find_recursive(tmp_path, "*.csproj")}

        assert py == {"pyproject.toml"}, (
            "should find exactly one pyproject.toml at root; "
            f"found from skip_dirs/excess depth: {py}"
        )
        assert cs == {"src/Api/Api.csproj"}, (
            "should find the one .csproj at depth 3; deep file (depth 5) and "
            f"node_modules file must be excluded; got: {cs}"
        )

    def test_respects_max_depth_exactly_at_boundary(self, tmp_path):
        from cli.detect import _find_recursive

        # At depth = max_depth (4 segments incl. file name) → included.
        ok = tmp_path / "w" / "x" / "y"
        ok.mkdir(parents=True)
        (ok / "ok.csproj").write_text("", encoding="utf-8")
        # At depth = max_depth + 1 (5 segments) → excluded.
        nope = tmp_path / "w" / "x" / "y" / "z"
        nope.mkdir(parents=True)
        (nope / "nope.csproj").write_text("", encoding="utf-8")

        names = {p.name for p in _find_recursive(tmp_path, "*.csproj", max_depth=4)}
        assert names == {"ok.csproj"}

    def test_does_not_walk_into_skip_dirs(self, tmp_path, monkeypatch):
        """Implementation contract: traversal must prune noise dirs, not just
        filter results. We prove it by spying on os.walk and asserting no
        yielded dirpath is inside a skip_dir."""
        import cli.detect as detect_mod

        self._make_tree(tmp_path)

        visited_dirs: list[str] = []
        real_walk = detect_mod.os.walk

        def tracking_walk(path, *args, **kwargs):
            for dirpath, dirnames, filenames in real_walk(path, *args, **kwargs):
                visited_dirs.append(str(dirpath))
                yield dirpath, dirnames, filenames

        monkeypatch.setattr(detect_mod.os, "walk", tracking_walk)
        detect_mod._find_recursive(tmp_path, "pyproject.toml")

        # No yielded dirpath should be inside node_modules / .venv / etc.
        skip = {"node_modules", ".venv", "venv", ".git", "__pycache__",
                "dist", "build", "target", "bin", "obj", ".tox", ".pytest_cache"}
        from pathlib import Path as _P
        for d in visited_dirs:
            parts = set(_P(d).relative_to(tmp_path).parts)
            assert not (parts & skip), (
                f"_find_recursive walked into a skip dir: {d}; "
                f"pruning must happen via dirnames[:] mutation"
            )


# ---------------------------------------------------------------------------
# Service detection — #86
# ---------------------------------------------------------------------------

BACKEND_LAYERS = ("api", "ports", "services", "models", "adapters", "common")


def _hexagonal_package(target, prefix: str) -> None:
    """Create one hexagonal package rooted at `prefix` ("" = target root)."""
    base = target / prefix if prefix else target
    for layer in BACKEND_LAYERS:
        (base / layer).mkdir(parents=True, exist_ok=True)


class TestDetectServices:
    """`detect_services` names the service packages in a multi-service repo.

    It reads the same candidate roots `detect_source_root` walks — the work
    that function already did and threw away whenever it found more than one
    (see the plan's open question 1). The two answers must stay consistent,
    which is what `TestSourceRootAndServicesAgree` below is for.
    """

    def test_two_service_packages_are_both_named(self, tmp_path):
        from cli.detect import detect_services

        for svc in ("orders", "billing"):
            _hexagonal_package(tmp_path, f"src/{svc}")

        assert detect_services(tmp_path) == [
            ("billing", "src/billing"),
            ("orders", "src/orders"),
        ]

    def test_three_service_packages_are_all_named(self, tmp_path):
        """Two is the case #86 reports; nothing may cap the list at two."""
        from cli.detect import detect_services

        for svc in ("billing", "orders", "shipping"):
            _hexagonal_package(tmp_path, f"src/{svc}")

        assert [name for name, _ in detect_services(tmp_path)] == [
            "billing", "orders", "shipping",
        ]

    def test_documented_single_package_is_not_a_service_list(self, tmp_path):
        """One package is the canonical single-service layout, described by
        `source_root` alone. Emitting a one-entry list would make every
        conforming repo look multi-service."""
        from cli.detect import detect_services

        _hexagonal_package(tmp_path, "src/mypkg")

        assert detect_services(tmp_path) == []

    def test_flat_under_src_is_not_a_service(self, tmp_path):
        """`src/` holding the layers directly is a source root, not a service
        package. Naming it would put a service called "src" in the file."""
        from cli.detect import detect_services

        _hexagonal_package(tmp_path, "src")

        assert detect_services(tmp_path) == []

    def test_layers_at_the_target_root_are_not_a_service(self, tmp_path):
        from cli.detect import detect_services

        _hexagonal_package(tmp_path, "")

        assert detect_services(tmp_path) == []

    def test_unrecognisable_repo_has_no_services(self, tmp_path):
        from cli.detect import detect_services

        (tmp_path / "docs").mkdir()

        assert detect_services(tmp_path) == []

    def test_non_conforming_sibling_is_omitted(self, tmp_path):
        """`src/legacy/` that is not hexagonal at all sits beside two real
        services. Only the conforming packages are listed — the plan's open
        question 3."""
        from cli.detect import detect_services

        for svc in ("orders", "billing"):
            _hexagonal_package(tmp_path, f"src/{svc}")
        (tmp_path / "src" / "legacy" / "scripts").mkdir(parents=True)

        assert [name for name, _ in detect_services(tmp_path)] == ["billing", "orders"]

    def test_one_conforming_package_beside_a_non_conforming_one(self, tmp_path):
        """Only one service survives the filter, so this is the single-service
        case and gets no list."""
        from cli.detect import detect_services

        _hexagonal_package(tmp_path, "src/orders")
        (tmp_path / "src" / "legacy" / "scripts").mkdir(parents=True)

        assert detect_services(tmp_path) == []

    def test_skip_dirs_are_never_services(self, tmp_path):
        from cli.detect import detect_services

        for svc in ("orders", "billing"):
            _hexagonal_package(tmp_path, f"src/{svc}")
        _hexagonal_package(tmp_path, "src/node_modules")
        _hexagonal_package(tmp_path, "src/.hidden")

        assert [name for name, _ in detect_services(tmp_path)] == ["billing", "orders"]

    def test_roots_are_posix_relative_to_the_target(self, tmp_path):
        """Windows separators in an emitted YAML path would be wrong for the
        agents that read it."""
        from cli.detect import detect_services

        for svc in ("orders", "billing"):
            _hexagonal_package(tmp_path, f"src/{svc}")

        for _name, root in detect_services(tmp_path):
            assert "\\" not in root
            assert not root.startswith("/")


class TestSourceRootAndServicesAgree:
    """One walk, two readings — the invariant that binds them.

    `detect_source_root` and `detect_services` read the same candidate list.
    If they ever disagree, `skill_context.yaml` states both a single root and
    a set of services, which is the contradiction #86 exists to remove.
    """

    # layout -> (dirs to create, expected source_root, expected service count)
    LAYOUTS = {
        "flat-at-root":       ([""], "", 0),
        "flat-under-src":     (["src"], "src", 0),
        "documented-package": (["src/mypkg"], "src/mypkg", 0),
        "two-services":       (["src/orders", "src/billing"], "", 2),
        "three-services":     (["src/orders", "src/billing", "src/shipping"], "", 3),
    }

    @pytest.mark.parametrize("layout", sorted(LAYOUTS))
    def test_both_answers_match_the_layout(self, tmp_path, layout):
        from cli.detect import detect_services, detect_source_root

        dirs, expected_root, expected_count = self.LAYOUTS[layout]
        for prefix in dirs:
            _hexagonal_package(tmp_path, prefix)

        assert detect_source_root(tmp_path) == expected_root
        assert len(detect_services(tmp_path)) == expected_count

    @pytest.mark.parametrize("layout", sorted(LAYOUTS))
    def test_services_are_listed_only_when_there_is_no_single_root(self, tmp_path, layout):
        """The contradiction this pair must never produce: a file naming one
        source root *and* a set of services."""
        from cli.detect import detect_services, detect_source_root

        dirs, _root, _count = self.LAYOUTS[layout]
        for prefix in dirs:
            _hexagonal_package(tmp_path, prefix)

        if detect_services(tmp_path):
            assert detect_source_root(tmp_path) == "", (
                f"{layout}: services listed alongside a single source root"
            )

    def test_the_layout_table_asserts_both_outcomes(self):
        """Guard against this table drifting to one shape. Written as counts
        rather than "some layout has services", so a table that lost its
        multi-service rows — or its single-service ones — fails here instead
        of quietly making the parametrized tests vacuous."""
        counts = {count for _dirs, _root, count in self.LAYOUTS.values()}
        assert len(self.LAYOUTS) == 5
        assert 0 in counts
        assert {c for c in counts if c > 1} == {2, 3}
        assert {root for _d, root, _c in self.LAYOUTS.values()} == {"", "src", "src/mypkg"}

    def test_a_source_root_beside_a_foreign_package_names_neither(self, tmp_path):
        """`src/` holding layers directly, next to `Source/pkg` that also
        does. Two candidates, so no single root — but only one of them is a
        service package, and one service is not a multi-service repo. The
        honest answer is "govkit cannot tell", not a one-entry list naming
        `src` as a service.

        This is the case that decided `detect_services` filters candidates by
        their parent rather than trusting the count.
        """
        from cli.detect import detect_services, detect_source_root

        _hexagonal_package(tmp_path, "src")
        _hexagonal_package(tmp_path, "Source/pkg")

        assert detect_source_root(tmp_path) == ""
        assert detect_services(tmp_path) == []

    def test_root_layers_win_over_service_packages(self, tmp_path):
        """A repo with layers at the root *and* `src/{orders,billing}/` has no
        coherent answer. `detect_source_root` has always stopped at the root
        in that case; the shared walk keeps that rather than inheriting it by
        accident, and services stay unlisted."""
        from cli.detect import detect_services, detect_source_root

        _hexagonal_package(tmp_path, "")
        (tmp_path / "api" / "handlers.py").write_text("x = 1\n", encoding="utf-8")
        (tmp_path / "services" / "orders.py").write_text("x = 1\n", encoding="utf-8")
        for svc in ("orders", "billing"):
            _hexagonal_package(tmp_path, f"src/{svc}")

        assert detect_source_root(tmp_path) == ""
        assert detect_services(tmp_path) == []


class TestGovkitsOwnFoldersAreNotEvidence:
    """govkit must not read its own output as the repo's architecture.

    Before the per-service fan-out, a multi-service install put codex's
    layer rules at the repo root — `api/AGENTS.md`, `ports/AGENTS.md` and so
    on, in folders govkit created. Every later reading then saw layers at
    the target root and reported a flat single-service repo. The damage was
    self-perpetuating: once those folders existed, `detect_services` could
    never again return anything, so the fan-out would never fire on the very
    installs that needed it and the doctor check for stale rules could never
    fire either.

    A folder holding nothing but a govkit-authored `AGENTS.md` is govkit's
    own artifact, not a source layer. Discounted **only at the target
    root**, which is the one place govkit creates layer folders — everywhere
    else it writes into folders the team already had, and discounting there
    would make a greenfield `src/<pkg>/` install relocate its own rules on
    the second run.
    """

    GOVKIT_ONLY = (
        "<!-- BEGIN GOVKIT GOVERNANCE -->\n# rule\n"
        "<!-- END GOVKIT GOVERNANCE -->\n"
    )

    def _pollute_root(self, target, *layers):
        for layer in layers:
            (target / layer).mkdir(parents=True, exist_ok=True)
            (target / layer / "AGENTS.md").write_text(self.GOVKIT_ONLY, encoding="utf-8")

    def test_a_polluted_multi_service_repo_still_reports_its_services(self, tmp_path):
        from cli.detect import detect_services, detect_source_root

        for svc in ("orders", "billing"):
            _hexagonal_package(tmp_path, f"src/{svc}")
        self._pollute_root(tmp_path, "api", "ports", "services", "adapters", "security")

        assert detect_source_root(tmp_path) == ""
        assert [n for n, _r in detect_services(tmp_path)] == ["billing", "orders"]

    def test_real_root_layers_are_still_evidence(self, tmp_path):
        """A team's own flat repo must keep reporting as flat. The layer
        folders there hold code, not just govkit's file."""
        from cli.detect import detect_services, detect_source_root

        _hexagonal_package(tmp_path, "")
        (tmp_path / "api" / "handlers.py").write_text("x = 1\n", encoding="utf-8")
        (tmp_path / "services" / "orders.py").write_text("x = 1\n", encoding="utf-8")

        assert detect_source_root(tmp_path) == ""
        assert detect_services(tmp_path) == []

    def test_a_layer_folder_holding_a_teams_own_agents_md_is_evidence(self, tmp_path):
        """Only a folder holding *nothing but* govkit's block is discounted.
        A file the team wrote — govkit's block appended below their content —
        means they own that folder."""
        from cli.detect import detect_source_root

        _hexagonal_package(tmp_path, "")
        for layer in ("api", "ports", "services", "adapters"):
            (tmp_path / layer / "AGENTS.md").write_text(
                "# Team notes\n\nOurs.\n" + self.GOVKIT_ONLY, encoding="utf-8",
            )

        # Still reads as layers at the root, so no service packages.
        assert detect_source_root(tmp_path) == ""

    def test_a_greenfield_package_layout_does_not_relocate_itself(self, tmp_path):
        """The regression the narrow scoping exists to avoid. Empty layer
        folders under `src/<pkg>/` hold only govkit's AGENTS.md after the
        first install; discounting them there would drop the source root and
        send the next run's rules back to the repo root."""
        from cli.detect import detect_source_root

        _hexagonal_package(tmp_path, "src/mypkg")
        for layer in BACKEND_LAYERS:
            (tmp_path / "src" / "mypkg" / layer / "AGENTS.md").write_text(
                self.GOVKIT_ONLY, encoding="utf-8",
            )

        assert detect_source_root(tmp_path) == "src/mypkg"

    def test_a_folder_with_other_files_beside_agents_md_is_evidence(self, tmp_path):
        from cli.detect import detect_source_root

        _hexagonal_package(tmp_path, "")
        for layer in ("api", "ports", "services", "adapters"):
            (tmp_path / layer / "AGENTS.md").write_text(self.GOVKIT_ONLY, encoding="utf-8")
        (tmp_path / "api" / "handlers.py").write_text("x = 1\n", encoding="utf-8")
        (tmp_path / "services" / "orders.py").write_text("x = 1\n", encoding="utf-8")

        assert detect_source_root(tmp_path) == ""



# ---------------------------------------------------------------------------
# Near-miss packages — #120
# ---------------------------------------------------------------------------

class TestDetectNearMissPackages:
    """Packages govkit *almost* recognised as services.

    `detect_services` omits anything that does not hold enough architecture
    layers, correctly — but silently. A team reading `services: [orders,
    billing]` cannot tell whether that is the whole repo.

    A near miss is a package overlapping some fingerprint by exactly one
    folder: enough that govkit looked at it, too little to name it. That is
    the set where the omission is surprising. `src/utils/` overlapping
    nothing is not surprising and is not reported — reporting every unlisted
    directory would fire on every shared package in every repo.
    """

    def test_a_package_with_one_hexagonal_folder_is_a_near_miss(self, tmp_path):
        from cli.detect import detect_near_miss_packages

        for svc in ("orders", "billing"):
            _hexagonal_package(tmp_path, f"src/{svc}")
        (tmp_path / "src" / "legacy" / "ports").mkdir(parents=True)

        assert [root for root, _layers in detect_near_miss_packages(tmp_path)] == [
            "src/legacy",
        ]

    def test_the_matched_folders_are_reported(self, tmp_path):
        """So the message can say what govkit saw, not just that it saw
        something."""
        from cli.detect import detect_near_miss_packages

        for svc in ("orders", "billing"):
            _hexagonal_package(tmp_path, f"src/{svc}")
        (tmp_path / "src" / "legacy" / "adapters").mkdir(parents=True)

        assert detect_near_miss_packages(tmp_path) == [("src/legacy", ("adapters",))]

    def test_a_clean_architecture_near_miss_is_found(self, tmp_path):
        from cli.detect import detect_near_miss_packages

        for svc in ("orders", "billing"):
            _hexagonal_package(tmp_path, f"src/{svc}")
        (tmp_path / "src" / "shared" / "Domain").mkdir(parents=True)

        assert detect_near_miss_packages(tmp_path) == [("src/shared", ("Domain",))]

    def test_a_package_overlapping_nothing_is_not_reported(self, tmp_path):
        """`src/utils/` is not a service and nobody expected it to be.
        Reporting it is the noise this check exists to avoid."""
        from cli.detect import detect_near_miss_packages

        for svc in ("orders", "billing"):
            _hexagonal_package(tmp_path, f"src/{svc}")
        (tmp_path / "src" / "utils" / "helpers").mkdir(parents=True)
        (tmp_path / "src" / "config").mkdir(parents=True)

        assert detect_near_miss_packages(tmp_path) == []

    def test_a_lowercase_services_folder_overlaps_nothing(self, tmp_path):
        """The layered fingerprint holds `Services`, not `services`. A
        package with only `src/x/services/` matches no fingerprint at all, so
        it is not a near miss — #120's original write-up got this wrong and
        would have had the check silent on its own example."""
        from cli.detect import detect_near_miss_packages

        for svc in ("orders", "billing"):
            _hexagonal_package(tmp_path, f"src/{svc}")
        (tmp_path / "src" / "reporting" / "services").mkdir(parents=True)

        assert detect_near_miss_packages(tmp_path) == []

    def test_a_recognised_service_is_never_a_near_miss(self, tmp_path):
        from cli.detect import detect_near_miss_packages, detect_services

        for svc in ("orders", "billing"):
            _hexagonal_package(tmp_path, f"src/{svc}")

        named = {root for _n, root in detect_services(tmp_path)}
        assert named == {"src/orders", "src/billing"}
        assert not [r for r, _ in detect_near_miss_packages(tmp_path) if r in named]

    def test_reported_for_a_single_service_repo_too(self, tmp_path):
        """The sub-question #120 left open, answered yes. One conforming
        package and one near miss reads as single-service, and govkit picked
        a source root while ignoring the other package — more surprising
        there, not less."""
        from cli.detect import detect_near_miss_packages, detect_source_root

        _hexagonal_package(tmp_path, "src/orders")
        (tmp_path / "src" / "legacy" / "ports").mkdir(parents=True)

        assert detect_source_root(tmp_path) == "src/orders"
        assert detect_near_miss_packages(tmp_path) == [("src/legacy", ("ports",))]

    def test_silent_when_the_layers_sit_at_the_repo_root(self, tmp_path):
        from cli.detect import detect_near_miss_packages

        _hexagonal_package(tmp_path, "")

        assert detect_near_miss_packages(tmp_path) == []

    def test_silent_on_a_repo_with_no_source_root(self, tmp_path):
        from cli.detect import detect_near_miss_packages

        (tmp_path / "docs").mkdir()

        assert detect_near_miss_packages(tmp_path) == []

    def test_skip_dirs_and_hidden_packages_are_ignored(self, tmp_path):
        from cli.detect import detect_near_miss_packages

        for svc in ("orders", "billing"):
            _hexagonal_package(tmp_path, f"src/{svc}")
        (tmp_path / "src" / "node_modules" / "ports").mkdir(parents=True)
        (tmp_path / "src" / ".cache" / "ports").mkdir(parents=True)

        assert detect_near_miss_packages(tmp_path) == []

    def test_the_threshold_is_the_one_detection_uses(self, tmp_path):
        """Near miss is defined against the same fingerprints and the same
        `>= 2` threshold `detect_source_root` applies. If the check kept its
        own copy the two would drift and this would report packages that are
        in fact services, or miss ones that are not."""
        from cli.detect import detect_near_miss_packages, detect_services

        # Exactly the threshold: two hexagonal folders -> a service.
        (tmp_path / "src" / "orders" / "ports").mkdir(parents=True)
        (tmp_path / "src" / "orders" / "adapters").mkdir(parents=True)
        (tmp_path / "src" / "billing" / "ports").mkdir(parents=True)
        (tmp_path / "src" / "billing" / "adapters").mkdir(parents=True)
        # One below it -> a near miss.
        (tmp_path / "src" / "legacy" / "ports").mkdir(parents=True)

        assert len(detect_services(tmp_path)) == 2
        assert [r for r, _ in detect_near_miss_packages(tmp_path)] == ["src/legacy"]
