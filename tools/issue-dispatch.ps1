# tools/issue-dispatch.ps1
param(
  [Parameter(Mandatory=$true)][string]$Repo,
  [Parameter(Mandatory=$true)][int]$IssueNumber,
  [switch]$OpenPR,
  [switch]$DockerSmoke
)

$ErrorActionPreference = 'Stop'

# Resolve script folder
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Import the helper module (defines Get-IssueJson, Invoke-ApiUnitTests, etc.)
Import-Module (Join-Path $ScriptRoot 'Agentic.Tools.psm1') -Force

# Sanity check GH CLI
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
  throw "GitHub CLI (gh) not found. Install from https://cli.github.com/ and run 'gh auth login'."
}

# Fetch the issue JSON
$issue = Get-IssueJson -Repo $Repo -IssueNumber $IssueNumber

# Slugify the title to find a matching script in tools/issues
$title = $issue.title
$slug  = ($title -replace '[^a-zA-Z0-9\- ]','').ToLower() -replace '\s+','-'
$issuesDir = Join-Path $ScriptRoot 'issues'
$issueScript = Join-Path $issuesDir "$slug.ps1"

# If no matching script, create from template
if (-not (Test-Path $issueScript)) {
  Write-Host "No script found for '$title' -> $slug. Creating from templateâ€¦"
  $template = Join-Path $issuesDir '_template.ps1'
  if (-not (Test-Path $template)) { throw "Missing template: $template" }
  Copy-Item $template $issueScript
  # Optionally stamp the title into the new script
  (Get-Content $issueScript) -replace '__TITLE__', [Regex]::Escape($title) | Set-Content -Encoding UTF8 $issueScript
}

Write-Host "=== Processing #${IssueNumber}: $title ==="

# Forward the flags to the issue-specific script
& $issueScript `
  -Repo $Repo `
  -IssueNumber $IssueNumber `
  -OpenPR:$OpenPR.IsPresent `
  -DockerSmoke:$DockerSmoke.IsPresent

