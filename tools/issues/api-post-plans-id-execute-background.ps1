[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$Repo,
  [Parameter(Mandatory=$true)][int]$IssueNumber,
  [Parameter(Mandatory=$true)][string]$Title,
  [Parameter()][string]$Body = "",
  [switch]$OpenPR,
  [switch]$DockerSmoke
)

Write-Host (">>> Running issue script for #{0}: {1}" -f $IssueNumber, $Title)


# … your work (tests/changes/commits) …

if ($OpenPR) {
  $head = (git rev-parse --abbrev-ref HEAD).Trim()
  # (Optional) scrub dangerous CLI-looking lines from body so gh isn’t confused:
  $bodyOrEmpty = if ($null -ne $Body) { $Body } else { "" }
  $safeBody    = [regex]::Replace($bodyOrEmpty, '(^|\n)\s*--\w+.*', '')
  Ensure-PrBodyHasClose -Repo $Repo -HeadBranch $head -IssueNumber $IssueNumber -Title $Title -Body $safeBody
}
