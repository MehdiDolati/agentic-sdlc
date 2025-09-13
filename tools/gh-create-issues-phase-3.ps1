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
	  @{ title = "User authentication workflow"
		 body  = "Build pages for registration and login that call /auth/register and /auth/login and store the returned bearer token in a cookie or local storage. Display the logged-in user’s email in the navbar and provide logout functionality. Prevent access to plan creation and execution pages unless authenticated."
		 labels= @("type:feature","area:ui","priority:normal") },
	  @{ title = "Plan/request creation interface"
		 body  = "Create a form where a user can enter the project vision, select single vs multi-agent mode and choose an LLM provider. On submit, call the /requests endpoint to generate artefacts and display the draft PRD/OpenAPI for review. Allow the user to assign a Plan ID and persist the plan via POST /plans."
		 labels= @("type:feature","area:ui","priority:normal") },
	  @{ title = "Plan list enhancements"
		 body  = "Replace the current server-rendered list with a more interactive component using pagination, search, sorting and filtering (by owner, status, etc.). Provide a 'New Plan' button linking to the plan creation form. Include run status indicators or last run date for each plan."
		 labels= @("type:feature","area:ui","priority:normal") },
	  @{ title = "Plan detail actions"
		 body  = "Add controls on the plan detail page to run the plan (POST /plans/{plan_id}/execute) and show run progress/logs. Display links to the generated files (PRD, ADR, tasks, stories, OpenAPI) and add editing capabilities so the user can make manual adjustments before saving back to disk. Provide buttons to download artefacts or copy them to the clipboard."
		 labels= @("type:feature","area:ui","priority:normal") },
	  @{ title = "Run management views"
		 body  = "Implement a list of runs per plan (with status, creation time and actions such as cancel). Create a run detail view that streams log events using polling or server-sent events and shows the manifest JSON."
		 labels= @("type:feature","area:ui","priority:normal") },
	  @{ title = "Task/story management board"
		 body  = "Parse the generated tasks and stories files into a structured list or kanban board. Let users mark tasks as completed, edit them and, optionally, bulk-create issues on a connected repository (see GitHub integration). Persist these updates back to the tasks/stories files or a database."
		 labels= @("type:feature","area:ui","priority:normal") },
	  @{ title = "Integration with GitHub for issues/branches"
		 body  = "Extend the backend and UI to authenticate with GitHub on behalf of the user and create issues from tasks or stories. Offer an option to create a feature branch, commit generated artefacts, and open a pull request. Surface the branch and issue links in the UI."
		 labels= @("type:feature","area:integration","priority:normal") },
	  @{ title = "Architecture and technology specification"
		 body  = "Add support for generating or uploading high-level architecture designs and technology stack decisions. Create dedicated pages to edit and view these documents and integrate them into the plan detail view. Consider leveraging LLM prompts to assist in drafting architecture sections."
		 labels= @("type:feature","area:ui","priority:normal") },
	  @{ title = "Settings & environment controls"
		 body  = "Provide a settings page where users can configure planner mode, default LLM provider, API base URL, etc. Expose toggles for enabling/disabling authentication and multi-agent mode."
		 labels= @("type:feature","area:ui","priority:normal") },
	  @{ title = "Error handling & user feedback"
		 body  = "Implement consistent flash messages or modals for success/failure when API calls fail (e.g. plan not found). Ensure the UI gracefully handles 404/500 responses and invalid inputs."
		 labels= @("type:feature","area:ui","priority:normal") }
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