<#
.SYNOPSIS
  TACTICAL helper: smoke-tests govkit's NEW-PATH UI shapes (--type ui-react /
  --type ui-angular) across the agent x level matrix.

.DESCRIPTION
  Parallel to smoke-ui.ps1, but exercises the flat --type enumeration introduced
  in Phase 2 of the project-shape refactor (--type ui-react / --type ui-angular)
  instead of the legacy --type api --ui <framework> cross-product.

  This script will be SUPERSEDED in Phase 4 (Increment 11): smoke-ui.ps1 itself
  gets rewritten to drop --ui and use the flat enumeration, at which point this
  file should be deleted. See plans/PROJECT_SHAPE_REFACTOR_PLAN.md §10.3.

  Output lands at projects-ui-new/ to avoid clobbering smoke-ui.ps1's
  projects-ui/ output (which still exercises the legacy path).

  Drops the 3 spec inputs (acceptance.feature, nfrs.md, eval_criteria.yaml).
  plan.md and architecture_preflight.md are intentionally absent so the
  /ui-architecture-preflight and /ui-spec-planning skills can be invoked
  against the sandbox to generate them.

  L3: validate short-circuits (no per-feature artifacts).
  L4: validate is expected to FAIL until the planning artifacts are generated.
  L5: validate also expected to fail (missing artifacts plus mode is not llm).

.PARAMETER SandboxRoot
  Where the per-config project folders are created. Default: this script's directory.
  Override with -SandboxRoot to redirect output elsewhere (e.g. an external sandbox dir).

.PARAMETER RepoPath
  Path to the governed-ai-delivery repo (editable install source).
  Default: parent of this script's directory.

.PARAMETER Agents
  Agents to test. Default: all three (claude-code, codex, copilot).

.PARAMETER Types
  UI shape types to test. Default: ui-react, ui-angular.

.PARAMETER Levels
  Levels to test. Default: 3, 4, 5.

.PARAMETER Force
  Delete existing sandbox folders before recreating.

.EXAMPLE
  .\smoke-ui-new.ps1
  .\smoke-ui-new.ps1 -Agents claude-code -Types ui-react -Levels 4 -Force
  .\smoke-ui-new.ps1 -SandboxRoot c:\users\marty\source\sandbox\govkit-test-v080
#>

[CmdletBinding()]
param(
    [string]$SandboxRoot = $PSScriptRoot,
    [string]$RepoPath    = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string[]]$Agents    = @("claude-code", "codex", "copilot"),
    [string[]]$Types     = @("ui-react", "ui-angular"),
    [string[]]$Levels    = @("3", "4", "5"),
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# ----------------------------------------------------------------------------
# venv bootstrap (shares the same .venv as smoke.ps1 / smoke-ui.ps1)
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
# hello_world_ui feature content (3 spec inputs only)
#
# Mirrors smoke-ui.ps1 so an apply lands in a state where the planning
# skills can be exercised against a real Gherkin spec.
# ----------------------------------------------------------------------------

$featureAcceptance = @'
Feature: Hello World UI Card

  As a developer smoke-testing the govkit install
  I want a minimal greeting card on a page
  So that I can confirm UI scaffolding and validation work end to end

  @e2e
  Scenario: Render the default greeting
    Given the hello card page is loaded
    When the page finishes rendering
    Then the card displays the text "hello, world"

  @e2e @nfr-performance
  Scenario: Page meets the LCP target on a standard connection
    Given the hello card page is loaded on a standard 4G profile
    When Core Web Vitals are measured
    Then Largest Contentful Paint is below 2500ms
'@

$featureNfrs = @'
# Non-Functional Requirements: Hello World UI Card

## Repository Scope

**Scope:** `single-repo`

## Performance
- The hello card page must achieve Largest Contentful Paint under 2500ms on a standard 4G profile
'@

$featureEval = @'
version: 1
feature: hello_world_ui
mode: deterministic
owner: smoke-test

unit_tests:
  enforce_FIRST: true
  minimum_FIRST_average: 4

code_quality:
  enforce_virtues: true
  minimum_virtue_average: 4
'@

function Write-HelloUiFeature {
    param([string]$ProjectRoot)
    $dir = Join-Path $ProjectRoot "features\hello_world_ui"
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
    Set-Content -Path (Join-Path $dir "acceptance.feature") -Value $featureAcceptance -Encoding utf8
    Set-Content -Path (Join-Path $dir "nfrs.md")            -Value $featureNfrs       -Encoding utf8
    Set-Content -Path (Join-Path $dir "eval_criteria.yaml") -Value $featureEval       -Encoding utf8
}

# ----------------------------------------------------------------------------
# Matrix runner
# ----------------------------------------------------------------------------

$projectsRoot = Join-Path $SandboxRoot "projects-ui-new"
New-Item -ItemType Directory -Path $projectsRoot -Force | Out-Null

$results = @()

foreach ($agent in $Agents) {
    foreach ($type in $Types) {
        foreach ($level in $Levels) {
            $name        = "$agent-$type-l$level"
            $projectPath = Join-Path $projectsRoot $name

            Write-Host "================================================================" -ForegroundColor Yellow
            Write-Host " $name (new-path UI)" -ForegroundColor Yellow
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

            # ---- apply (new path: --type ui-react / ui-angular, --ui none) ----
            Write-Host "  govkit apply --agent $agent --type $type --level $level" -ForegroundColor Cyan
            & $venvGovkit apply --agent $agent --type $type --level $level --ui none --ci github --target $projectPath
            $applyExit   = $LASTEXITCODE
            $applyStatus = if ($applyExit -eq 0) { "PASS" } else { "FAIL($applyExit)" }

            # ---- drop hello_world_ui (spec inputs only) for L4+ ----
            if ($applyExit -eq 0 -and $level -ne "3") {
                Write-Host "  writing features/hello_world_ui/" -ForegroundColor Cyan
                Write-HelloUiFeature -ProjectRoot $projectPath
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
}

# ----------------------------------------------------------------------------
# Summary
# ----------------------------------------------------------------------------

Write-Host "================================================================" -ForegroundColor Green
Write-Host " New-Path UI Summary" -ForegroundColor Green
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
Write-Host "All apply steps and L3 validate passed. L4/L5 validate are expected to fail until /ui-architecture-preflight and /ui-spec-planning generate the missing artifacts." -ForegroundColor Green
exit 0
