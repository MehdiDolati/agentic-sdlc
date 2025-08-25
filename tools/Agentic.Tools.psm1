# tools/Agentic.Tools.psm1  (PowerShell 5.1 compatible)

function Get-RepoRoot {
  $here = Split-Path -Parent $PSCommandPath
  return (Resolve-Path (Join-Path $here "..")).Path
}

function Get-VenvPython {
  [CmdletBinding()]
  param()

  $repoRoot = Get-RepoRoot
  $venvDir  = Join-Path $repoRoot ".venv"
  $pyExe    = Join-Path $venvDir "Scripts\python.exe"

  if (-not (Test-Path $pyExe)) {
    Write-Host "[venv] creating" -ForegroundColor Cyan

    # PowerShell 5.1 compatible way to find python
    $pyCmd = $null
    try {
      $gc = Get-Command python -ErrorAction Stop
      $pyCmd = $gc.Source
    } catch {
      try {
        $gc = Get-Command py -ErrorAction Stop
        $pyCmd = $gc.Source
      } catch {
        throw "Could not find a Python launcher ('python' or 'py') on PATH."
      }
    }

    & $pyCmd -m venv $venvDir
    if ($LASTEXITCODE -ne 0) { throw "python -m venv failed" }
  }

  Write-Host "[venv] upgrading pip" -ForegroundColor Cyan
  $null = & $pyExe -m pip install --upgrade pip

  Write-Host "[deps] installing requirements" -ForegroundColor Cyan
  $req = Join-Path $repoRoot "services\api\requirements.txt"
  if (-not (Test-Path $req)) { throw "Missing requirements file: $req" }
  $null = & $pyExe -m pip install -r $req

  return $pyExe
}

function Invoke-ApiUnitTests {
  [CmdletBinding()]
  param(
    [switch]$Coverage
  )
  $repoRoot = Get-RepoRoot
  $pyExe = Get-VenvPython

  Push-Location $repoRoot
  try {
    if ($Coverage) {
      Write-Host "[tests] coverage + pytest" -ForegroundColor Cyan
      & $pyExe -m coverage run -m pytest -q services/api
      if ($LASTEXITCODE -ne 0) { throw "Unit tests failed" }
      & $pyExe -m coverage report -m
    } else {
      Write-Host "[tests] pytest" -ForegroundColor Cyan
      & $pyExe -m pytest -q services/api
      if ($LASTEXITCODE -ne 0) { throw "Unit tests failed" }
    }
  } finally {
    Pop-Location
  }
}

function Invoke-DockerSmoke {
  [CmdletBinding()]
  param(
    [string]$ComposeFile = "docker-compose.yml"
  )
  $repoRoot = Get-RepoRoot
  Push-Location $repoRoot
  try {
    Write-Host "[docker] compose build+up" -ForegroundColor Cyan
    $null = docker compose -f $ComposeFile up --build -d
    if ($LASTEXITCODE -ne 0) { throw "docker compose up failed" }

    # simple smoke: hit health endpoint via container network
    Start-Sleep -Seconds 3
    Write-Host "[smoke] GET http://localhost:8080/health" -ForegroundColor Cyan
    try {
      $resp = Invoke-WebRequest -UseBasicParsing -Uri "http://localhost:8080/health" -TimeoutSec 10
      if ($resp.StatusCode -ne 200) { throw "Health returned $($resp.StatusCode)" }
    } catch {
      throw "Smoke test failed: $_"
    }
  } finally {
    Write-Host "[docker] compose down" -ForegroundColor Cyan
    $null = docker compose -f $ComposeFile down
    Pop-Location
  }
}

function Get-IssueJson {
    param(
        [Parameter(Mandatory = $true)][string]$Repo,
        [Parameter(Mandatory = $true)][int]$IssueNumber
    )

    try {
        # Only PS5-safe constructs (no ?. operator)
        $raw = gh issue view $IssueNumber -R $Repo --json number,title,body,labels 2>$null
        if (-not $raw) { throw "Empty response from gh" }

        $issue = $raw | ConvertFrom-Json
        if (-not $issue) { throw "Failed to parse JSON" }

        # Normalize labels to simple array of names
        if ($issue.labels) {
            $issue | Add-Member -NotePropertyName labelNames -NotePropertyValue (@($issue.labels | ForEach-Object { $_.name }))
        } else {
            $issue | Add-Member -NotePropertyName labelNames -NotePropertyValue @()
        }

        return $issue
    }
    catch {
        throw "Get-IssueJson failed for $Repo#$IssueNumber. $_"
    }
}

function Get-IssueSlug {
    param([Parameter(Mandatory=$true)][string]$Title)

    $slug = $Title.Trim().ToLowerInvariant()
    $slug = $slug -replace '[^a-z0-9]+','-'      # collapse non-alnum to hyphen
    $slug = $slug -replace '(^-|-$)',''          # trim leading/trailing hyphens
    if (-not $slug) { $slug = "issue-$([DateTime]::UtcNow.ToString('yyyyMMddHHmmss'))" }
    return $slug
}

Export-ModuleMember -Function Get-IssueJson
Export-ModuleMember -Function Get-RepoRoot,Get-VenvPython,Invoke-ApiUnitTests,Invoke-DockerSmoke
