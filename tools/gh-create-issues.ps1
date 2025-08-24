# tools/gh-create-issues.ps1
param(
  [string]$Repo,                  # optional: "owner/name". If omitted, auto-detect from git remote.
  [switch]$DryRun,                # optional: show what would run
  [hashtable[]]$Issues            # optional: array of @{ title=...; body=...; labels=@(...) }
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Require-Cmd($name) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    throw "Required command '$name' not found. Please install it and retry."
  }
}

Require-Cmd gh
Require-Cmd git

# Ensure you're authenticated (will prompt if needed)
$null = gh auth status 2>$null
if ($LASTEXITCODE -ne 0) { gh auth login }

function Get-GitHubRepoSlug {
  $url = git config --get remote.origin.url 2>$null
  if (-not $url) { return $null }
  if ($url -match 'github\.com[:/](?<owner>[^/]+)/(?<repo>[^/.]+)') {
    return "$($matches.owner)/$($matches.repo)"
  }
  return $null
}

if (-not $Repo) { $Repo = Get-GitHubRepoSlug }
if (-not $Repo) { throw "Could not detect owner/repo. Pass -Repo 'owner/name' or run inside the repo clone." }

# Verify repo is reachable
gh repo view $Repo 1>$null 2>$null

# Ensure labels exist
$desiredLabels = @{
  "type:feature"      = "0E8A16"
  "type:bug"          = "D73A4A"
  "priority:normal"   = "C2E0C6"
  "priority:high"     = "B60205"
  "area:orchestrator" = "1D76DB"
  "area:planner"      = "5319E7"
  "area:api"          = "A2EEEF"
  "security"          = "BFDADC"
}

$existing = @()
try {
  $existing = (gh label list --repo $Repo --limit 200 --json name | ConvertFrom-Json).name
} catch { $existing = @() }

foreach ($kv in $desiredLabels.GetEnumerator()) {
  if ($existing -notcontains $kv.Key) {
    if ($DryRun) {
      Write-Host "[dry-run] would create label '$($kv.Key)'" -ForegroundColor Yellow
    } else {
      gh label create $kv.Key --repo $Repo --color $kv.Value | Out-Null
    }
  }
}

# Default issues if none passed in
if (-not $Issues -or $Issues.Count -eq 0) {
# Next batch of issues
	$issues = @(
	  @{ title = "Planner: prompt templates + test fixtures"
		 body  = "Introduce reusable Jinja-style prompts for PRD, OpenAPI, and file plan. Add golden tests."
		 labels= @("type:feature","area:planner","priority:normal") }

	  @{ title = "Planner: OpenAPI generator function"
		 body  = "From PRD/blueprint, emit OpenAPI (paths, schemas, security). Cover with unit tests."
		 labels= @("type:feature","area:planner","priority:high") }

	  @{ title = "Planner: artifact index + plan metadata"
		 body  = "Persist plan.json with steps, artifacts, timestamps; list-/detail endpoints consume it."
		 labels= @("type:feature","area:planner","priority:normal") }

	  @{ title = "Planner: code skeleton emitter"
		 body  = "Generate minimal FastAPI route stubs and tests from OpenAPI. Guardrails to avoid overwrites."
		 labels= @("type:feature","area:planner","priority:high") }

	  @{ title = "Orchestrator: step runner (write_file, patch_file, run_cmd)"
		 body  = "Implement core step types + dry-run mode. Capture stdout/stderr/exit codes."
		 labels= @("type:feature","area:orchestrator","priority:high") }

	  @{ title = "Orchestrator: execution logs + artifact manifest"
		 body  = "Stream step logs; store per-plan execution log and produced artifacts list."
		 labels= @("type:feature","area:orchestrator","priority:normal") }

	  @{ title = "Orchestrator: timeouts, retries, and cancellation"
		 body  = "Per-step timeout + retry/backoff; cancel running plan safely."
		 labels= @("type:feature","area:orchestrator","priority:normal") }

	  @{ title = "API: POST /plans/{id}/execute (background)"
		 body  = "Kick off orchestrator run; return 202 and a status URL; add polling endpoint."
		 labels= @("type:feature","area:api","priority:high") }

	  @{ title = "API: plans pagination + filters"
		 body  = "Support page/size, sort by created_at, filter by status."
		 labels= @("type:feature","area:api","priority:normal") }

	  @{ title = "Notes repo: switch to DB-backed repo"
		 body  = "Replace in-memory notes with Postgres implementation. Add migration + tests."
		 labels= @("type:feature","area:api","priority:normal") }

	  @{ title = "Compose hardening: read-only root FS (db, db-init)"
		 body  = "Add read_only: true where possible and tmpfs for writable paths; adjust startup scripts."
		 labels= @("security","area:api","priority:high") }

	  @{ title = "Compose hardening: no-new-privileges (db, db-init)"
		 body  = "security_opt: no-new-privileges:true for all services."
		 labels= @("security","area:api","priority:high") }

	  @{ title = "CI: fast pre-push script (lint, tests, smoke)"
		 body  = "Wire pre-push hook to run local-lint-and-test.ps1; fail fast on regressions."
		 labels= @("type:feature","area:api","priority:normal") }
	)
}

foreach ($i in $Issues) {
  $title  = [string]$i.title
  $body   = if ($i.ContainsKey('body'))   { [string]$i.body }   else { "" }
  $labels = if ($i.ContainsKey('labels')) { ($i.labels) -join "," } else { "" }

  if ($DryRun) {
    Write-Host "[dry-run] gh issue create --repo $Repo --title `"$title`" --label $labels" -ForegroundColor Yellow
  } else {
    gh issue create --repo $Repo --title $title --body $body --label $labels
  }
}