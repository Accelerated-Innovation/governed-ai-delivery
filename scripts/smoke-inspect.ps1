<#
.SYNOPSIS
  Opens previously-applied smoke-test sandboxes for visual inspection.

.DESCRIPTION
  Picks one or more sandbox dirs from any "projects*" directory under
  -SandboxRoot (e.g. scripts/projects/, scripts/projects-ui/,
  scripts/projects-dotnet/) and opens each in Explorer (default), VS Code,
  or as a text tree dump on stdout.

  Companion to smoke.ps1 / smoke-ui.ps1 / smoke-dotnet.ps1 -- run a smoke
  script first to populate the sandboxes, then use this script to inspect
  what govkit installed.

  In "tree" mode all output goes through the success stream so it is safe
  to redirect:
      .\smoke-inspect.ps1 -All -Editor tree > tmp\baseline.txt

  In "explorer" and "code" modes status messages go to the host stream.

.PARAMETER Config
  Exact sandbox name to open (case-insensitive), e.g. "claude-code-l3" or
  "codex-react-l4". Matched against the leaf directory name only -- the
  parent "projects*" dir is searched automatically.

.PARAMETER Pattern
  Wildcard pattern (PowerShell -like syntax) matched against sandbox leaf
  names. Examples: "*ui*-l4", "claude-code-*", "*-l5".

.PARAMETER All
  Open every sandbox under every "projects*" directory in -SandboxRoot.

.PARAMETER Editor
  How to open each selected sandbox:
    explorer (default) -- Invoke-Item; opens a Windows Explorer window per dir
    code               -- launches VS Code via the `code` CLI
    tree               -- prints a Get-ChildItem -Recurse -Force dump to stdout

.PARAMETER SandboxRoot
  Where the sandbox dirs live. Default: this script's directory.
  Override if you redirected smoke output via the smoke scripts' own
  -SandboxRoot parameter (e.g. an external sandbox path).

.EXAMPLE
  .\smoke-inspect.ps1 -Config claude-code-l3

.EXAMPLE
  .\smoke-inspect.ps1 -Pattern "*ui*-l4" -Editor code

.EXAMPLE
  .\smoke-inspect.ps1 -All -Editor tree > tmp\baseline.txt

.EXAMPLE
  .\smoke-inspect.ps1 -Pattern "codex-*" -Editor tree -SandboxRoot c:\users\marty\source\sandbox\govkit-test
#>

[CmdletBinding()]
param(
    [string]$Config,
    [string]$Pattern,
    [switch]$All,
    [ValidateSet("explorer", "code", "tree")]
    [string]$Editor = "explorer",
    [string]$SandboxRoot = $PSScriptRoot
)

$ErrorActionPreference = "Stop"

# ----------------------------------------------------------------------------
# Validate selection -- exactly one of -Config, -Pattern, -All
# ----------------------------------------------------------------------------

$selectors = 0
if ($Config)  { $selectors++ }
if ($Pattern) { $selectors++ }
if ($All)     { $selectors++ }

if ($selectors -eq 0) {
    Write-Error "Specify one of: -Config <name>, -Pattern <wildcard>, or -All. See Get-Help .\smoke-inspect.ps1 -Examples."
    exit 2
}
if ($selectors -gt 1) {
    Write-Error "Use only one of -Config, -Pattern, -All (they are mutually exclusive)."
    exit 2
}

# ----------------------------------------------------------------------------
# Editor preflight
# ----------------------------------------------------------------------------

if ($Editor -eq "code") {
    $codeCmd = Get-Command code -ErrorAction SilentlyContinue
    if (-not $codeCmd) {
        Write-Error "VS Code CLI 'code' not found on PATH. Install it via VS Code's 'Shell Command: Install code command in PATH', or pick a different -Editor."
        exit 3
    }
}

# ----------------------------------------------------------------------------
# Discover sandbox dirs
# ----------------------------------------------------------------------------

if (-not (Test-Path $SandboxRoot)) {
    Write-Error "SandboxRoot does not exist: $SandboxRoot"
    exit 4
}

$projectsRoots = Get-ChildItem -Directory -Path $SandboxRoot -Filter "projects*" -ErrorAction SilentlyContinue
if (-not $projectsRoots) {
    Write-Error "No 'projects*' directories under $SandboxRoot. Run smoke.ps1 / smoke-ui.ps1 / smoke-dotnet.ps1 first."
    exit 5
}

$allSandboxes = foreach ($root in $projectsRoots) {
    Get-ChildItem -Directory -Path $root.FullName -ErrorAction SilentlyContinue |
        ForEach-Object {
            [pscustomobject]@{
                Name   = $_.Name
                Label  = "$($root.Name)/$($_.Name)"
                Dir    = $_
            }
        }
}

if (-not $allSandboxes) {
    Write-Error "Found 'projects*' directories under $SandboxRoot but they are empty. Run a smoke script first."
    exit 5
}

# ----------------------------------------------------------------------------
# Filter
# ----------------------------------------------------------------------------

$selected = if ($All) {
    $allSandboxes
} elseif ($Config) {
    $allSandboxes | Where-Object { $_.Name -eq $Config }
} elseif ($Pattern) {
    $allSandboxes | Where-Object { $_.Name -like $Pattern }
}

if (-not $selected) {
    $available = ($allSandboxes | ForEach-Object { $_.Label } | Sort-Object) -join "`n  "
    Write-Error "No sandbox matched the selection.`nAvailable:`n  $available"
    exit 6
}

# ----------------------------------------------------------------------------
# Tree printer (success-stream output so `>` redirection works)
# ----------------------------------------------------------------------------

function Write-SandboxTree {
    param(
        [Parameter(Mandatory)] [System.IO.DirectoryInfo]$Root,
        [Parameter(Mandatory)] [string]$Label
    )

    Write-Output ""
    Write-Output "================================================================"
    Write-Output " $Label"
    Write-Output "   $($Root.FullName)"
    Write-Output "================================================================"

    $items = Get-ChildItem -Path $Root.FullName -Recurse -Force -ErrorAction SilentlyContinue |
        Sort-Object FullName

    if (-not $items) {
        Write-Output "  (empty)"
        return
    }

    $rootLen = $Root.FullName.Length
    foreach ($item in $items) {
        $rel    = $item.FullName.Substring($rootLen).TrimStart('\', '/')
        $depth  = ($rel -split '[\\/]').Length - 1
        $indent = '  ' * $depth
        $leaf   = $item.Name
        if ($item.PSIsContainer) {
            Write-Output "$indent$leaf/"
        } else {
            $size = $item.Length
            Write-Output ("{0}{1}  ({2} bytes)" -f $indent, $leaf, $size)
        }
    }
}

# ----------------------------------------------------------------------------
# Open each selected sandbox
# ----------------------------------------------------------------------------

$count = ($selected | Measure-Object).Count

if ($Editor -ne "tree" -and $count -gt 5) {
    Write-Host "About to open $count sandboxes in '$Editor'. Ctrl+C to cancel." -ForegroundColor Yellow
}

foreach ($s in $selected) {
    switch ($Editor) {
        "explorer" {
            Write-Host "explorer: $($s.Label)" -ForegroundColor Cyan
            Invoke-Item -Path $s.Dir.FullName
        }
        "code" {
            Write-Host "code: $($s.Label)" -ForegroundColor Cyan
            & code $s.Dir.FullName
        }
        "tree" {
            Write-SandboxTree -Root $s.Dir -Label $s.Label
        }
    }
}

if ($Editor -eq "tree") {
    Write-Output ""
    Write-Output "================================================================"
    Write-Output " $count sandbox(es) inspected"
    Write-Output "================================================================"
} else {
    Write-Host ""
    Write-Host "Opened $count sandbox(es)." -ForegroundColor Green
}

exit 0
