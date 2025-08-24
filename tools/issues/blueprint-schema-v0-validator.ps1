[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$Repo,
  [Parameter(Mandatory=$true)][int]$IssueNumber,
  [Parameter(Mandatory=$true)][string]$Title,
  [Parameter(Mandatory=$false)][string]$Body,
  [switch]$OpenPR,
  [switch]$DockerSmoke
)

Import-Module "$PSScriptRoot\..\Agentic.Tools.psm1" -Force

$py = Get-VenvPython
Invoke-ApiUnitTests

if ($DockerSmoke) { Invoke-DockerSmoke }

# … do the rest of the issue work …
