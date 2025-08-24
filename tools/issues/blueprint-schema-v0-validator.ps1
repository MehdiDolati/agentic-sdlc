param(
  [string]$Repo,
  [switch]$OpenPR,
  [switch]$DockerSmoke
)

Import-Module "$PSScriptRoot\..\Agentic.Tools.psm1" -Force

$py = Get-VenvPython
Invoke-ApiUnitTests

if ($DockerSmoke) { Invoke-DockerSmoke }

# … do the rest of the issue work …
