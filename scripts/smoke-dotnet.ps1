<#
.SYNOPSIS
  Smoke-tests govkit scaffolding against the agent x level matrix using a
  .NET-flavored backend API smoke feature.

.DESCRIPTION
  Parallel to smoke.ps1 but the embedded smoke feature describes an ASP.NET
  Core minimal API instead of a generic backend. Validation rules in
  cli/validate.py are stack-agnostic, so what differs here is the realism of
  the spec inputs (Kestrel/xUnit/WebApplicationFactory phrasing). Useful for
  confirming the scaffolding reads cleanly when a real .NET team would adopt it.

  Does NOT invoke `dotnet build` or scaffold an actual .NET project. Use a
  separate script if you want to exercise the SDK end to end.

  Drops the 3 spec inputs (acceptance.feature, nfrs.md, eval_criteria.yaml).
  plan.md and architecture_preflight.md are intentionally absent so the
  /architecture-preflight and /spec-planning skills can be invoked against
  the sandbox to generate them.

  L3: validate short-circuits (no per-feature artifacts).
  L4: validate is expected to FAIL until the planning artifacts are generated.
  L5: validate also expected to fail (missing artifacts plus mode is not llm).

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

function Write-HelloDotnetFeature {
    param([string]$ProjectRoot)
    $dir = Join-Path $ProjectRoot "features\hello_world_dotnet_api"
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
    Set-Content -Path (Join-Path $dir "acceptance.feature") -Value $featureAcceptance -Encoding utf8
    Set-Content -Path (Join-Path $dir "nfrs.md")            -Value $featureNfrs       -Encoding utf8
    Set-Content -Path (Join-Path $dir "eval_criteria.yaml") -Value $featureEval       -Encoding utf8
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
        & $venvGovkit apply --agent $agent --level $level --type api --ci github --target $projectPath
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

$failed = $results | Where-Object {
    $_.Apply -like "FAIL*" -or
    ($_.Validate -like "FAIL*" -and $_.Config -notlike "*-l4" -and $_.Config -notlike "*-l5")
}
if ($failed) {
    Write-Host "Some configs failed (L4/L5 validate-fails are expected; only L3 validate must pass)." -ForegroundColor Red
    exit 1
}
Write-Host "All apply steps and L3 validate passed. L4/L5 validate are expected to fail until /architecture-preflight and /spec-planning generate the missing artifacts." -ForegroundColor Green
exit 0
