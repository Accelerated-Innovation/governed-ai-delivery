<#
.SYNOPSIS
  End-to-end smoke test for govkit's extension-pack discovery + validation flow,
  driven by the real `extensions/agentic-skills/` pack in this repo.

.DESCRIPTION
  Builds a throwaway target project, copies the agentic-skills extension into
  it, and walks through the scenarios the user-facing extension feature is
  expected to handle:

    1. Baseline           — apply + validate with no extensions/ folder
    2. Discovery          — apply detects and reports the extension
    3. Valid validate     — `govkit validate` shows PASS for agentic-skills
    4. Valid validate --strict — PASS in strict mode too
    5. Broken contract path (warn) — WARN line, exit 0 in default mode
    6. Broken contract path (strict) — FAIL line, exit 1 in --strict mode
    7. Undeclared overlap — strip relates_to and confirm overlap heuristic fires
    8. No-extensions regression — remove extensions/ and confirm silent

  Each scenario prints what it ran, what it expected, and what it observed,
  then a summary table is printed at the end. The script exits 0 only when
  every scenario passes.

.PARAMETER SandboxRoot
  Where the venv lives. Default: this script's directory (scripts/).

.PARAMETER ProjectPath
  The throwaway target project govkit applies to. Default: $SandboxRoot\extensions-smoke.
  Override to redirect the sandbox elsewhere (e.g. an external scratch dir).

.PARAMETER RepoPath
  Path to the governed-ai-delivery repo (editable install source).
  Default: parent of this script's directory.

.PARAMETER Force
  Delete an existing sandbox before recreating.

.EXAMPLE
  .\smoke-extensions.ps1
  .\smoke-extensions.ps1 -Force
  .\smoke-extensions.ps1 -ProjectPath c:\users\marty\source\sandbox\govtest_0524 -Force
#>

[CmdletBinding()]
param(
    [string]$SandboxRoot = $PSScriptRoot,
    [string]$ProjectPath = (Join-Path $PSScriptRoot "extensions-smoke"),
    [string]$RepoPath    = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# ----------------------------------------------------------------------------
# venv bootstrap (shared with smoke.ps1's pattern)
# ----------------------------------------------------------------------------

$venvDir    = Join-Path $SandboxRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$venvGovkit = Join-Path $venvDir "Scripts\govkit.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating venv at $venvDir" -ForegroundColor Cyan
    python -m venv $venvDir
}

# Always refresh — picks up pyproject.toml dep changes (e.g. pyyaml) on existing venvs.
Write-Host "Installing/refreshing govkit (editable) from $RepoPath" -ForegroundColor Cyan
& $venvPython -m pip install --quiet --upgrade pip
& $venvPython -m pip install --quiet -e $RepoPath

# Sanity check the new pyyaml runtime dep is importable.
& $venvPython -c "import yaml" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: pyyaml not importable in venv after install — bootstrap broken." -ForegroundColor Red
    exit 1
}

$installedVersion = (& $venvPython -c "from importlib.metadata import version; print(version('govkit'))").Trim()
Write-Host "govkit version: $installedVersion" -ForegroundColor Cyan
Write-Host ""

$env:GOVKIT_NO_MIGRATION_WARNING = "1"
$env:GOVKIT_NO_SHAPE_MIGRATION_WARNING = "1"

# ----------------------------------------------------------------------------
# Sandbox setup
# ----------------------------------------------------------------------------

$projectPath  = $ProjectPath
$sourceExt    = Join-Path $RepoPath    "extensions\agentic-skills"
$targetExtDir = Join-Path $projectPath "extensions\agentic-skills"

if (Test-Path $projectPath) {
    if ($Force) {
        Write-Host "Removing existing sandbox $projectPath" -ForegroundColor DarkGray
        Remove-Item -Recurse -Force $projectPath
    } else {
        Write-Host "SKIP -- $projectPath exists. Re-run with -Force to recreate." -ForegroundColor DarkYellow
        exit 0
    }
}
New-Item -ItemType Directory -Path $projectPath -Force | Out-Null

if (-not (Test-Path $sourceExt)) {
    Write-Host "FAIL: reference extension not found at $sourceExt" -ForegroundColor Red
    exit 1
}

# ----------------------------------------------------------------------------
# Scenario helpers
# ----------------------------------------------------------------------------

$results = @()

function Add-Result {
    param([string]$Name, [string]$Status, [string]$Detail = "")
    $script:results += [pscustomobject]@{ Scenario = $Name; Status = $Status; Detail = $Detail }
    $color = if ($Status -eq "PASS") { "Green" } else { "Red" }
    Write-Host "  -> $Status" -ForegroundColor $color
    if ($Detail) { Write-Host "     $Detail" -ForegroundColor DarkGray }
    Write-Host ""
}

function Invoke-Govkit {
    param([string[]]$ArgList)
    $raw = & $venvGovkit @ArgList 2>&1 | Out-String
    # Strip ANSI color codes (validate.py wraps PASS/FAIL/WARN in escape sequences)
    $output = [regex]::Replace($raw, "`e\[[0-9;]*m", "")
    return @{ Output = $output; ExitCode = $LASTEXITCODE }
}

function Write-Section {
    param([string]$Title)
    Write-Host "================================================================" -ForegroundColor Yellow
    Write-Host " $Title" -ForegroundColor Yellow
    Write-Host "================================================================" -ForegroundColor Yellow
}

function Copy-Extension {
    if (Test-Path $targetExtDir) { Remove-Item -Recurse -Force $targetExtDir }
    Copy-Item -Recurse $sourceExt $targetExtDir
}

# ----------------------------------------------------------------------------
# Scenario 1 — baseline apply + validate with no extensions/
# ----------------------------------------------------------------------------

Write-Section "1. Baseline: apply + validate, no extensions present"

$apply = Invoke-Govkit @("apply", "--agent", "claude-code", "--level", "3", "--type", "api", "--ci", "github", "--target", $projectPath)
Write-Host $apply.Output

if ($apply.ExitCode -eq 0 -and $apply.Output -notmatch "Extensions detected") {
    Add-Result "1. Apply baseline (no extensions)" "PASS" "apply succeeded; no extensions reported"
} else {
    Add-Result "1. Apply baseline (no extensions)" "FAIL" "exit=$($apply.ExitCode); unexpected 'Extensions detected' output"
}

$validate = Invoke-Govkit @("validate", "--target", $projectPath, "--level", "3")
Write-Host $validate.Output

if ($validate.ExitCode -eq 0 -and $validate.Output -notmatch "govkit validate . extensions") {
    Add-Result "1b. Validate baseline (no extensions)" "PASS" "validate exit 0; no extensions section"
} else {
    Add-Result "1b. Validate baseline (no extensions)" "FAIL" "exit=$($validate.ExitCode); unexpected extensions section"
}

# ----------------------------------------------------------------------------
# Scenario 2 — apply with extension present reports discovery
# ----------------------------------------------------------------------------

Write-Section "2. Discovery: apply reports the agentic-skills extension"

Copy-Extension
$apply2 = Invoke-Govkit @("apply", "--agent", "claude-code", "--level", "3", "--type", "api", "--ci", "github", "--target", $projectPath)
Write-Host $apply2.Output

if ($apply2.ExitCode -eq 0 -and $apply2.Output -match "Extensions detected" -and $apply2.Output -match "agentic-skills v0\.1\.0") {
    Add-Result "2. Apply discovers extension" "PASS" "apply printed 'Extensions detected: agentic-skills v0.1.0'"
} else {
    Add-Result "2. Apply discovers extension" "FAIL" "exit=$($apply2.ExitCode); apply did not report agentic-skills"
}

# ----------------------------------------------------------------------------
# Scenario 3 — validate shows PASS for the valid extension
# ----------------------------------------------------------------------------

Write-Section "3. Valid validate (default mode)"

$validate3 = Invoke-Govkit @("validate", "--target", $projectPath, "--level", "3")
Write-Host $validate3.Output

if ($validate3.ExitCode -eq 0 -and $validate3.Output -match "PASS\s+agentic-skills v0\.1\.0") {
    Add-Result "3. Validate valid extension (default)" "PASS" "PASS line shown; exit 0"
} else {
    Add-Result "3. Validate valid extension (default)" "FAIL" "exit=$($validate3.ExitCode); expected PASS line"
}

# ----------------------------------------------------------------------------
# Scenario 4 — validate --strict also passes for the valid extension
# ----------------------------------------------------------------------------

Write-Section "4. Valid validate (--strict)"

$validate4 = Invoke-Govkit @("validate", "--target", $projectPath, "--level", "3", "--strict")
Write-Host $validate4.Output

if ($validate4.ExitCode -eq 0 -and $validate4.Output -match "PASS\s+agentic-skills v0\.1\.0") {
    Add-Result "4. Validate valid extension (--strict)" "PASS" "strict mode also passes; exit 0"
} else {
    Add-Result "4. Validate valid extension (--strict)" "FAIL" "exit=$($validate4.ExitCode)"
}

# ----------------------------------------------------------------------------
# Scenario 5 — broken contract path warns in default mode (exit 0)
# ----------------------------------------------------------------------------

Write-Section "5. Broken contract path warns (default mode, exit 0)"

$contract = Join-Path $targetExtDir "docs\backend\architecture\AGENT_RUNTIME_CONTRACT.md"
$contractMoved = "$contract.bak"
Move-Item $contract $contractMoved

$validate5 = Invoke-Govkit @("validate", "--target", $projectPath, "--level", "3")
Write-Host $validate5.Output

if ($validate5.ExitCode -eq 0 -and $validate5.Output -match "WARN\s+agentic-skills" -and $validate5.Output -match "AGENT_RUNTIME_CONTRACT\.md") {
    Add-Result "5. Broken path (default)" "PASS" "WARN shown; exit 0 preserved"
} else {
    Add-Result "5. Broken path (default)" "FAIL" "exit=$($validate5.ExitCode); expected WARN for AGENT_RUNTIME_CONTRACT.md"
}

# ----------------------------------------------------------------------------
# Scenario 6 — same break under --strict produces FAIL + exit 1
# ----------------------------------------------------------------------------

Write-Section "6. Broken contract path fails (--strict, exit 1)"

$validate6 = Invoke-Govkit @("validate", "--target", $projectPath, "--level", "3", "--strict")
Write-Host $validate6.Output

if ($validate6.ExitCode -eq 1 -and $validate6.Output -match "FAIL\s+agentic-skills") {
    Add-Result "6. Broken path (--strict)" "PASS" "FAIL shown; exit 1"
} else {
    Add-Result "6. Broken path (--strict)" "FAIL" "exit=$($validate6.ExitCode); expected FAIL + exit 1"
}

Move-Item $contractMoved $contract

# ----------------------------------------------------------------------------
# Scenario 7 — undeclared overlap warns when relates_to is stripped
# ----------------------------------------------------------------------------

Write-Section "7. Undeclared overlap warns (relates_to removed)"

# Apply core L5 doc so the overlap heuristic has a core file to match against.
& $venvGovkit apply --agent claude-code --level 5 --type api --ci github --target $projectPath | Out-Null

$manifestPath = Join-Path $targetExtDir "manifest.yaml"
$originalManifest = Get-Content -Raw -Path $manifestPath
# Strip the relates_to block (indented under contract_sets[0]) up to the next top-level key (agent_guidance:).
$strippedManifest = $originalManifest -replace "(?ms)^    relates_to:.*?(?=^agent_guidance:)", ""
Set-Content -Path $manifestPath -Value $strippedManifest -Encoding utf8

$validate7 = Invoke-Govkit @("validate", "--target", $projectPath, "--level", "5")
Write-Host $validate7.Output

if ($validate7.Output -match "overlaps core" -and $validate7.Output -match "relates_to") {
    Add-Result "7. Undeclared overlap" "PASS" "overlap WARN with relates_to remedy shown"
} else {
    Add-Result "7. Undeclared overlap" "FAIL" "expected overlap WARN mentioning relates_to"
}

Set-Content -Path $manifestPath -Value $originalManifest -Encoding utf8

# ----------------------------------------------------------------------------
# Scenario 8 — no-extensions regression after removing extensions/
# ----------------------------------------------------------------------------

Write-Section "8. No-extensions regression after removal"

Remove-Item -Recurse -Force (Join-Path $projectPath "extensions")
$validate8 = Invoke-Govkit @("validate", "--target", $projectPath, "--level", "5")
Write-Host $validate8.Output

# Note: at L5 with no features yet, validate exits 1 because no features/ exists in the sandbox.
# What we're testing here is that extensions section does NOT appear when extensions/ is gone.
if ($validate8.Output -notmatch "govkit validate . extensions" -and $validate8.Output -notmatch "ModuleNotFoundError") {
    Add-Result "8. No-extensions regression" "PASS" "no extensions section after removal"
} else {
    Add-Result "8. No-extensions regression" "FAIL" "extensions section or import error present"
}

# ----------------------------------------------------------------------------
# Summary
# ----------------------------------------------------------------------------

Write-Section "Summary"
$results | Format-Table -AutoSize

$failed = ($results | Where-Object { $_.Status -ne "PASS" }).Count
if ($failed -gt 0) {
    Write-Host "$failed scenario(s) FAILED" -ForegroundColor Red
    exit 1
}
Write-Host "All $($results.Count) scenarios PASSED" -ForegroundColor Green
exit 0
