# tools/finish-issue.ps1 (safe version)
# Purpose: Push current branch, create or locate PR, optionally wait for checks,
#          then attempt to merge (squash). If merge is blocked/conflicted, abort
#          and keep both the issue and branch intact.
# Usage: tools/finish-issue.ps1 -Repo owner/repo [-IssueNumber N] [-WaitForChecks]

[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string] $Repo,
  [int]                                $IssueNumber,
  [switch]                             $WaitForChecks
)

function Fail($msg){ Write-Error $msg; exit 1 }

$ErrorActionPreference     = 'Stop'
$ProgressPreference        = 'SilentlyContinue'

# Ensure we're in a git repo
try { & git rev-parse --is-inside-work-tree | Out-Null } catch { Fail "Not inside a git repository." }

# Current branch
$branch = (& git rev-parse --abbrev-ref HEAD).Trim()
if ([string]::IsNullOrWhiteSpace($branch) -or $branch -eq "HEAD") {
  Fail "Could not determine the current branch."
}
Write-Host "Current branch: $branch"

# Ensure branch is pushed
Write-Host "Pushing '$branch' to origin…"
& git push -u origin $branch
if ($LASTEXITCODE -ne 0) { Fail "Failed to push branch '$branch'." }

# Find or create a PR for this branch
Write-Host "Looking for existing PR for '$branch'…"
$pr = gh pr list -R $Repo --head $branch --state open --json number,title | ConvertFrom-Json
if (-not $pr) {
  Write-Host "No open PR found. Creating one…"
  # If IssueNumber is provided, link it in the body so GitHub can auto-close on merge
  $body = if ($PSBoundParameters.ContainsKey('IssueNumber')) { "Fixes #${IssueNumber}" } else { "" }
  $created = gh pr create -R $Repo --fill --base main --head $branch --body $body --json number,title,url | ConvertFrom-Json
  if (-not $created) { Fail "Failed to create PR for '$branch'." }
  $prNum = $created.number
  Write-Host "Created PR #${prNum} - $($created.title)"
} else {
  $prNum = $pr[0].number
  Write-Host "Found PR #${prNum} - $($pr[0].title)"
}

# Optionally wait for checks to pass
if ($WaitForChecks) {
  Write-Host "Waiting for status checks to complete…"
  gh pr checks $prNum -R $Repo --watch
  if ($LASTEXITCODE -ne 0) {
    Write-Warning "Status checks for PR #${prNum} did not pass or timed out. Aborting merge."
    exit 1
  }
}

# Check mergeability before attempting merge to avoid deleting branches on conflicts
Write-Host "Checking mergeability for PR #$prNum…"
$prInfo = gh pr view $prNum -R $Repo --json mergeable,mergeStateStatus,canMerge,headRefName,state | ConvertFrom-Json

# Normalize fields across gh versions
$mergeable = $null
if ($null -ne $prInfo.mergeable) { $mergeable = [bool]$prInfo.mergeable }
elseif ($null -ne $prInfo.canMerge) { $mergeable = [bool]$prInfo.canMerge }

$mergeState = if ($null -ne $prInfo.mergeStateStatus) { "$($prInfo.mergeStateStatus)" } else { "" }

# Known blocking states include: "CONFLICTING", "BLOCKED", "DRAFT"
if ($mergeable -eq $false -or $mergeState -match 'CONFLICT|BLOCK|DRAFT') {
  Write-Warning @"
Cannot merge PR #$prNum (state: '$mergeState'). The merge request has conflicts or is blocked.
Operation canceled. The issue (if any) and the branch '$branch' have been left intact.
Please resolve conflicts and rerun this command.
"@
  exit 1
}

# Attempt merge (squash) WITHOUT deleting the branch first; we'll delete only on success
Write-Host "Merging PR #$prNum…"
gh pr merge $prNum -R $Repo --squash --admin
if ($LASTEXITCODE -ne 0) {
  Write-Warning @"
Merge of PR #$prNum failed (possibly due to conflicts or required checks).
Operation canceled. The issue (if any) and the branch '$branch' have been left intact.
"@
  exit 1
}

Write-Host "PR #$prNum merged successfully."

# Close linked issue explicitly only after a successful merge (if IssueNumber was provided and still open)
if ($PSBoundParameters.ContainsKey('IssueNumber')) {
  try {
    $issueState = gh issue view $IssueNumber -R $Repo --json state | ConvertFrom-Json
    if ($issueState.state -ne 'CLOSED') {
      Write-Host "Closing issue #$IssueNumber…"
      gh issue close $IssueNumber -R $Repo --comment "Closed via merge of PR #$prNum"
    }
  } catch {
    Write-Warning "Unable to verify/close issue #${IssueNumber}: $($_.Exception.Message)"
  }
}

# Delete remote branch AFTER successful merge
Write-Host "Deleting remote branch '$branch'…"
& git push origin --delete $branch
if ($LASTEXITCODE -ne 0) {
  Write-Warning "Could not delete remote branch '$branch'. You may need to remove it manually."
}

# Delete local branch (switch to main first)
try { & git checkout main | Out-Null } catch {}
try {
  & git branch -D $branch | Out-Null
  Write-Host "Local branch '$branch' deleted."
} catch {
  Write-Warning "Could not delete local branch '$branch': $($_.Exception.Message)"
}
