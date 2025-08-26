[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$Repo,
  [Parameter(Mandatory=$true)][int]$IssueNumber,
  [Parameter(Mandatory=$true)][string]$Title,
  [Parameter()][string]$Body = "",
  [switch]$OpenPR,
  [switch]$DockerSmoke
)

Write-Host ">>> Running issue script for #${IssueNumber}: $Title"

# … your work (tests/changes/commits) …

if ($OpenPR) {
  $head = (git rev-parse --abbrev-ref HEAD).Trim()
  # (Optional) scrub dangerous CLI-looking lines from body so gh isn’t confused:
  $BodyString = if ($null -eq $Body) { "" } else { [string]$Body }
  # also tolerate Windows newlines in the regex:
  $safeBody = [regex]::Replace($BodyString, '(^|\r?\n)\s*--\w+.*', '')
  Ensure-PrBodyHasClose -Repo $Repo -HeadBranch $head -IssueNumber $IssueNumber -Title $Title -Body $safeBody
}
