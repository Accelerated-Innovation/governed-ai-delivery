<#
.SYNOPSIS
  Smoke-tests govkit scaffolding against the agent x level matrix using a
  .NET-flavored backend API smoke feature.

.DESCRIPTION
  Parallel to smoke.ps1 but the embedded smoke feature describes an ASP.NET
  Core minimal API instead of a generic backend. Validation rules in
  cli/validate.py are stack-agnostic, so what differs here is the realism of
  plan.md and architecture_preflight.md (project layout, xUnit + FIRST,
  controller-vs-minimal-API note). Useful for confirming the scaffolding
  reads cleanly when a real .NET team would adopt it.

  Does NOT invoke `dotnet build` or scaffold an actual .NET project. Use a
  separate script if you want to exercise the SDK end to end.

  L3: validate short-circuits (no per-feature artifacts).
  L4: full 5-artifact validation against hello_world_dotnet_api.
  L5: applies and creates the folder. The smoke feature is deterministic mode
      and WILL FAIL the L5-specific LLM checks. That is expected.

.PARAMETER SandboxRoot
  Where the per-config project folders are created. Default: this script's directory.
  Override with -SandboxRoot to redirect output elsewhere (e.g. an external sandbox dir).

.PARAMETER RepoPath
  Path to the governed-ai-delivery repo (editable install source).
  Default: parent of this script's directory (i.e. the repo root when run from scripts/).

.PARAMETER Agents
  Agents to test. Default: claude-code, codex, copilot.

.PARAMETER Levels
  Levels to test. Default: 3, 4, 5.

.PARAMETER Force
  Delete existing sandbox folders before recreating.

.EXAMPLE
  .\smoke-dotnet.ps1
  .\smoke-dotnet.ps1 -Agents claude-code -Levels 4 -Force
  .\smoke-dotnet.ps1 -SandboxRoot c:\users\marty\source\sandbox\govkit-test
#>

[CmdletBinding()]
param(
    [string]$SandboxRoot = $PSScriptRoot,
    [string]$RepoPath    = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string[]]$Agents    = @("claude-code", "codex", "copilot"),
    [string[]]$Levels    = @("3", "4", "5"),
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# ----------------------------------------------------------------------------
# venv bootstrap (shares the same .venv as smoke.ps1)
# ----------------------------------------------------------------------------

$venvDir    = Join-Path $SandboxRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$venvGovkit = Join-Path $venvDir "Scripts\govkit.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating venv at $venvDir" -ForegroundColor Cyan
    python -m venv $venvDir
}

if (-not (Test-Path $venvGovkit)) {
    Write-Host "Installing govkit (editable) from $RepoPath" -ForegroundColor Cyan
    & $venvPython -m pip install --quiet --upgrade pip
    & $venvPython -m pip install --quiet -e $RepoPath
}

$installedVersion = (& $venvPython -c "from importlib.metadata import version; print(version('govkit'))").Trim()
Write-Host "govkit version: $installedVersion" -ForegroundColor Cyan
Write-Host ""

$env:GOVKIT_NO_MIGRATION_WARNING = "1"

# ----------------------------------------------------------------------------
# hello_world_dotnet_api feature content (L4 smoke feature)
# ----------------------------------------------------------------------------

$featureAcceptance = @'
Feature: Hello World .NET API

  As a developer smoke-testing the govkit install on a .NET stack
  I want a minimal ASP.NET Core minimal API greeting endpoint
  So that I can confirm scaffolding and validation work end to end

  Scenario: Greet the default visitor
    Given the HelloApi web host is running on Kestrel
    When a client sends GET /hello
    Then the response status is 200
    And the response body is {"message": "hello, world"}

  @nfr-performance
  Scenario: Greeting responds within the latency target
    Given the HelloApi web host is running on Kestrel
    When a client sends GET /hello under normal load
    Then the response is returned within 50ms at p95
'@

$featureNfrs = @'
# Non-Functional Requirements: Hello World .NET API

## Repository Scope

**Scope:** `single-repo`

## Performance
- The `/hello` endpoint must respond within 50ms at p95 under normal load on Kestrel
'@

$featureEval = @'
version: 1
feature: hello_world_dotnet_api
mode: deterministic
owner: smoke-test

unit_tests:
  enforce_FIRST: true
  minimum_FIRST_average: 4

code_quality:
  enforce_virtues: true
  minimum_virtue_average: 4
'@

$featurePlan = @'
# Feature Plan: hello_world_dotnet_api

## Objective

- Provide a minimal `GET /hello` endpoint on an ASP.NET Core 8 minimal API
  returning a fixed JSON greeting
- Used as a smoke test for govkit scaffolding on the .NET stack
- Success: both acceptance scenarios pass; p95 latency < 50ms

## Scope Boundaries

### In scope
- One minimal API endpoint mapped via `app.MapGet("/hello", ...)`
- One xUnit test project asserting status code and body

### Out of scope
- Authentication, OpenAPI customisation beyond the default Swashbuckle generation
- Persistence, EF Core, background services
- Deployment manifests

### Assumptions
- Target framework: net8.0 (LTS)
- Test framework: xUnit + Microsoft.AspNetCore.Mvc.Testing (`WebApplicationFactory`)
- Service is reachable on a Kestrel-bound localhost port during tests

## Architecture Alignment

### Relevant contracts
- docs/backend/evaluation/eval_criteria.md: FIRST principles, 7 Virtues, deterministic mode
- docs/backend/architecture/API_CONVENTIONS.md: REST route naming and JSON error model

### ADRs
- No new ADRs required for this smoke endpoint.

## Evaluation Compliance Summary (MANDATORY)

```yaml
evaluation_prediction:
  first:
    fast:           { score: 5, evidence: "WebApplicationFactory keeps tests in-process; no Kestrel socket" }
    isolated:       { score: 5, evidence: "Each test creates its own factory; no shared state" }
    repeatable:     { score: 5, evidence: "Deterministic response body" }
    self_verifying: { score: 5, evidence: "Assertions on HttpResponseMessage status and content" }
    timely:         { score: 4, evidence: "Tests written before the MapGet handler" }
    average: 4.8
  virtues:
    working:   { score: 5, evidence: "Both acceptance scenarios automated via WebApplicationFactory" }
    unique:    { score: 5, evidence: "Single MapGet; no duplication" }
    simple:    { score: 5, evidence: "Minimal API, no controllers, no DI graph" }
    clear:     { score: 5, evidence: "Route literal matches the scenario" }
    easy:      { score: 5, evidence: "No service dependencies to inject" }
    developed: { score: 5, evidence: "No dead code or TODOs" }
    brief:     { score: 5, evidence: "Single file Program.cs" }
    average: 5.0
  thresholds_met: true
```

## Increments

### Increment 1: Implement `/hello`

**Goal**
- Add `app.MapGet("/hello", () => Results.Ok(new { message = "hello, world" }))` in `Program.cs`

**Deliverables**
- `src/HelloApi/Program.cs` (minimal API)
- `tests/HelloApi.Tests/HelloEndpointTests.cs` (xUnit + WebApplicationFactory)

**Definition of Done**
- Both acceptance scenarios pass under `dotnet test`
- p95 latency target met under a local k6 or BenchmarkDotNet run
'@

$featurePreflight = @'
# Architecture Preflight: hello_world_dotnet_api

## 1. Artifact Review

- acceptance.feature reviewed: yes
- nfrs.md reviewed: yes
- eval_criteria.yaml exists: yes
- plan.md exists: yes
- Gherkin scenarios cover all populated NFR categories: yes
  - @nfr-performance: yes (1 scenario)

## 2. Standards Referenced

- docs/backend/architecture/API_CONVENTIONS.md
- docs/backend/evaluation/eval_criteria.md

## 3. Boundary Analysis

- Single MapGet handler in Program.cs; no domain/adapter split required for a fixed response.
- Compliant with BOUNDARIES.md (no cross-layer imports because there is only one layer).

## 4. API Impact

- Routes affected: `GET /hello` (new)
- Versioning impact: new route -- no breaking change
- OpenAPI updates: Swashbuckle picks up the MapGet automatically; no manual swagger edits

## 5. Security Impact

- Endpoint is unauthenticated by design (smoke test only)
- No PII; HTTPS redirection inherited from the default Program.cs template
- No request body, so no model-binding attack surface

## 6. Evaluation Impact

- Mode: deterministic
- Predicted FIRST 4.8 / Virtues 5.0 -- above 4.0 threshold

## 7. ADR Determination

- ADR required: no -- no architectural commitment beyond a smoke endpoint

## 8. Shared Contract Analysis

- Produces shared artifact: no

## 9. Preflight Conclusion

- Architecture, security, evaluation alignment: compliant
- Final status: Approved for planning
'@

function Write-HelloDotnetFeature {
    param([string]$ProjectRoot)
    $dir = Join-Path $ProjectRoot "features\hello_world_dotnet_api"
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
    Set-Content -Path (Join-Path $dir "acceptance.feature")        -Value $featureAcceptance -Encoding utf8
    Set-Content -Path (Join-Path $dir "nfrs.md")                   -Value $featureNfrs       -Encoding utf8
    Set-Content -Path (Join-Path $dir "eval_criteria.yaml")        -Value $featureEval       -Encoding utf8
    Set-Content -Path (Join-Path $dir "plan.md")                   -Value $featurePlan       -Encoding utf8
    Set-Content -Path (Join-Path $dir "architecture_preflight.md") -Value $featurePreflight  -Encoding utf8
}

# ----------------------------------------------------------------------------
# Matrix runner
# ----------------------------------------------------------------------------

$projectsRoot = Join-Path $SandboxRoot "projects-dotnet"
New-Item -ItemType Directory -Path $projectsRoot -Force | Out-Null

$results = @()

foreach ($agent in $Agents) {
    foreach ($level in $Levels) {
        $name        = "$agent-l$level"
        $projectPath = Join-Path $projectsRoot $name

        Write-Host "================================================================" -ForegroundColor Yellow
        Write-Host " $name (.NET)" -ForegroundColor Yellow
        Write-Host "================================================================" -ForegroundColor Yellow

        if (Test-Path $projectPath) {
            if ($Force) {
                Write-Host "  removing existing $projectPath" -ForegroundColor DarkGray
                Remove-Item -Recurse -Force $projectPath
            } else {
                Write-Host "  SKIP -- already exists (use -Force to recreate)" -ForegroundColor DarkYellow
                $results += [pscustomobject]@{ Config = $name; Apply = "skip"; Validate = "skip" }
                continue
            }
        }
        New-Item -ItemType Directory -Path $projectPath -Force | Out-Null

        # ---- apply ----
        Write-Host "  govkit apply --agent $agent --level $level" -ForegroundColor Cyan
        & $venvGovkit apply --agent $agent --level $level --type api --ui none --ci github --target $projectPath
        $applyExit   = $LASTEXITCODE
        $applyStatus = if ($applyExit -eq 0) { "PASS" } else { "FAIL($applyExit)" }

        # ---- drop hello_world_dotnet_api for L4+ ----
        if ($applyExit -eq 0 -and $level -ne "3") {
            Write-Host "  writing features/hello_world_dotnet_api/" -ForegroundColor Cyan
            Write-HelloDotnetFeature -ProjectRoot $projectPath
        }

        # ---- validate ----
        Write-Host "  govkit validate --level $level" -ForegroundColor Cyan
        & $venvGovkit validate --target $projectPath --level $level
        $validateExit   = $LASTEXITCODE
        $validateStatus = if ($validateExit -eq 0) { "PASS" } else { "FAIL($validateExit)" }

        $results += [pscustomobject]@{
            Config   = $name
            Apply    = $applyStatus
            Validate = $validateStatus
        }
        Write-Host ""
    }
}

# ----------------------------------------------------------------------------
# Summary
# ----------------------------------------------------------------------------

Write-Host "================================================================" -ForegroundColor Green
Write-Host " .NET Summary" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
$results | Format-Table -AutoSize

$failed = $results | Where-Object { $_.Apply -like "FAIL*" -or ($_.Validate -like "FAIL*" -and $_.Config -notlike "*-l5") }
if ($failed) {
    Write-Host "Some configs failed (L5 validate-fails are expected for this smoke feature)." -ForegroundColor Red
    exit 1
}
Write-Host "All apply steps and L3/L4 validates passed. L5 validate is expected to fail until the smoke feature is extended with LLM artifacts." -ForegroundColor Green
exit 0
