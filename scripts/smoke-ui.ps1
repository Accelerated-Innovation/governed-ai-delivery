<#
.SYNOPSIS
  Smoke-tests govkit across the agent x level x UI-framework matrix.

.DESCRIPTION
  Parallel to smoke.ps1 but exercises the --ui dimension. For each
  (agent, framework, level) combination, creates a fresh sandbox, runs
  `govkit apply --ui <framework>`, drops in a minimal hello_world_ui feature
  for L4+, and runs `govkit validate`.

  L3: validate short-circuits (no per-feature artifacts). The apply itself
      is what proves the UI dimension is wired up correctly at this level.
  L4: full 5-artifact validation against hello_world_ui.
  L5: applies and creates the folder. The hello_world_ui feature is
      deterministic mode and WILL FAIL the L5-specific LLM checks.
      That is the expected behaviour for this smoke harness.

.PARAMETER SandboxRoot
  Where the per-config project folders are created. Default: this script's directory.
  Override with -SandboxRoot to redirect output elsewhere (e.g. an external sandbox dir).

.PARAMETER RepoPath
  Path to the governed-ai-delivery repo (editable install source).
  Default: parent of this script's directory (i.e. the repo root when run from scripts/).

.PARAMETER Agents
  Agents to test. Default: all three (claude-code, codex, copilot).

.PARAMETER Frameworks
  UI frameworks to test. Default: react, angular.

.PARAMETER Levels
  Levels to test. Default: 3, 4, 5.

.PARAMETER Force
  Delete existing sandbox folders before recreating.

.EXAMPLE
  .\smoke-ui.ps1
  .\smoke-ui.ps1 -Agents claude-code -Frameworks react -Levels 4 -Force
  .\smoke-ui.ps1 -SandboxRoot c:\users\marty\source\sandbox\govkit-test
#>

[CmdletBinding()]
param(
    [string]$SandboxRoot  = $PSScriptRoot,
    [string]$RepoPath     = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string[]]$Agents     = @("claude-code", "codex", "copilot"),
    [string[]]$Frameworks = @("react", "angular"),
    [string[]]$Levels     = @("3", "4", "5"),
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
# hello_world_ui feature content (L4 smoke feature)
#
# Tags chosen to satisfy validate.py:
#   - @e2e on every user-facing scenario (UI convention)
#   - @nfr-performance to cover the one populated NFR category
#
# NFR categories deliberately limited to ## Performance because
# check_gherkin_nfr_coverage only enforces tags for categories present in
# its category_to_tag map. Accessibility / Browser Compatibility / Usability
# are not in that map, so they are not part of this smoke check.
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

$featurePlan = @'
# Feature Plan: hello_world_ui

## Objective

- Provide a minimal greeting card rendered on a single page
- Used as a smoke test for govkit UI scaffolding, validation, and CI gates
- Success: both acceptance scenarios pass; LCP under 2500ms

## Scope Boundaries

### In scope
- One page with one static card component displaying "hello, world"

### Out of scope
- Routing, state management, API calls, theming, i18n

### Assumptions
- The page is served from a local dev server during tests

## Evaluation Compliance Summary (MANDATORY)

```yaml
evaluation_prediction:
  first:
    fast:           { score: 5, evidence: "Component tests run in jsdom; no network" }
    isolated:       { score: 5, evidence: "Pure presentational component" }
    repeatable:     { score: 5, evidence: "Deterministic text rendering" }
    self_verifying: { score: 5, evidence: "Assertions on rendered DOM" }
    timely:         { score: 4, evidence: "Tests written before component" }
    average: 4.8
  virtues:
    working:   { score: 5, evidence: "Both acceptance scenarios automated" }
    unique:    { score: 5, evidence: "Single component; no duplication" }
    simple:    { score: 5, evidence: "Static markup, no props" }
    clear:     { score: 5, evidence: "Component name matches behaviour" }
    easy:      { score: 5, evidence: "No dependencies to inject" }
    developed: { score: 5, evidence: "No dead code or TODOs" }
    brief:     { score: 5, evidence: "Minimal surface area" }
    average: 5.0
  thresholds_met: true
```

## Increments

### Increment 1: Render the card

**Goal**
- Add a HelloCard component and mount it on the index page

**Definition of Done**
- Both acceptance scenarios pass
- LCP target met under local Lighthouse run
'@

$featurePreflight = @'
# Architecture Preflight: hello_world_ui

## 1. Artifact Review

- acceptance.feature reviewed: yes
- nfrs.md reviewed: yes
- eval_criteria.yaml exists: yes
- plan.md exists: yes
- Gherkin scenarios cover all populated NFR categories: yes
  - @nfr-performance: yes (1 scenario)

## 2. Standards Referenced

- docs/ui/architecture/MVVM_CONTRACT.md
- docs/backend/evaluation/eval_criteria.md

## 3. Boundary Analysis

- Single presentational component; no view-model or service layer required.

## 4. API Impact

- No backend calls; no API contracts touched.

## 5. Security Impact

- Static content only; no user input, no XSS surface.

## 6. Evaluation Impact

- Mode: deterministic
- Predicted FIRST 4.8 / Virtues 5.0 -- above 4.0 threshold

## 7. ADR Determination

- ADR required: no

## 8. Shared Contract Analysis

- Produces shared artifact: no

## 9. Preflight Conclusion

- Architecture, security, evaluation alignment: compliant
- Final status: Approved for planning
'@

function Write-HelloUiFeature {
    param([string]$ProjectRoot)
    $dir = Join-Path $ProjectRoot "features\hello_world_ui"
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

$projectsRoot = Join-Path $SandboxRoot "projects-ui"
New-Item -ItemType Directory -Path $projectsRoot -Force | Out-Null

$results = @()

foreach ($agent in $Agents) {
    foreach ($framework in $Frameworks) {
        foreach ($level in $Levels) {
            $name        = "$agent-$framework-l$level"
            $projectPath = Join-Path $projectsRoot $name

            Write-Host "================================================================" -ForegroundColor Yellow
            Write-Host " $name" -ForegroundColor Yellow
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
            Write-Host "  govkit apply --agent $agent --level $level --ui $framework" -ForegroundColor Cyan
            & $venvGovkit apply --agent $agent --level $level --type api --ui $framework --ci github --target $projectPath
            $applyExit   = $LASTEXITCODE
            $applyStatus = if ($applyExit -eq 0) { "PASS" } else { "FAIL($applyExit)" }

            # ---- drop hello_world_ui for L4+ ----
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
Write-Host " UI Summary" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
$results | Format-Table -AutoSize

$failed = $results | Where-Object { $_.Apply -like "FAIL*" -or ($_.Validate -like "FAIL*" -and $_.Config -notlike "*-l5") }
if ($failed) {
    Write-Host "Some configs failed (L5 validate-fails are expected for this smoke feature)." -ForegroundColor Red
    exit 1
}
Write-Host "All apply steps and L3/L4 validates passed. L5 validate is expected to fail until the smoke feature is extended with LLM artifacts." -ForegroundColor Green
exit 0
