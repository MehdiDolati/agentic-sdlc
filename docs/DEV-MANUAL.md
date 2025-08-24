# Agentic SDLC — Developer Manual

## 0) prerequisites

- Windows + PowerShell 5.1 (or 7), Docker Desktop, Git, GitHub CLI
- Python 3.11 (local dev uses a venv)
- Logged in to GitHub CLI:
```powershell
gh auth login
```

---

## 1) bootstrap & local CI (one-liner)

Use our sanity runner before you push anything.

```powershell
# from repo root
tools\sanity-check.ps1
```

What it does (in order):
1) creates/uses `.venv`, installs `services/api/requirements.txt`
2) runs unit tests: `python -m pytest -q services/api`
3) builds & runs Docker Compose (db, db-init, api)
4) smoke tests the API (`/health`, planner POST, notes CRUD)
5) stops containers

> If anything fails, it explains the fix and exits non-zero.

---

## 2) creating a new issue

Two supported ways:

### A) GitHub UI  
Just open an issue as usual. Use clear titles; labels optional.

### B) GitHub CLI (PowerShell-friendly)
Labels with spaces must be quoted **individually**:
```powershell
$Repo = "YourUserOrOrg/agentic-sdlc"
gh issue create `
  --repo $Repo `
  --title "Blueprint schema (v0) + validator" `
  --body  "Define v0 schema + PRD validator. Include happy-path tests." `
  --label "area:planner" --label "priority:normal"
```

---

## 3) working an issue via dispatcher

Every issue is executed by a **matching script** under `tools/issues/`.

- The dispatcher converts the issue title to a kebab case key and looks for a script:
  - Example: **“Blueprint schema (v0) + validator”** → `tools\issues\blueprint-schema-v0-validator.ps1`
- If not found, it can create one from our template.

Run it:

```powershell
$Repo = "YourUserOrOrg/agentic-sdlc"
tools\issue-dispatch.ps1 -Repo $Repo -IssueNumber 12 -OpenPR -DockerSmoke
```

Flags:
- `-OpenPR` – after local CI passes, create a branch, commit, push, and open a PR.
- `-DockerSmoke` – perform container smoke checks (recommended).

> The dispatcher imports `tools\Agentic.Tools.psm1` where all helper cmdlets live.

---

## 4) writing an issue script

Create `tools/issues/<kebab-title>.ps1`. Minimal template:

```powershell
param(
  [string]$Repo,
  [int]$IssueNumber
)

# 1) create a working branch
$branch = New-WorkBranch -Repo $Repo -IssueNumber $IssueNumber `
          -Prefix "feat" -Slug (Get-IssueSlug -Repo $Repo -IssueNumber $IssueNumber)

# 2) make your changes here
#    - add code / tests / docs

# 3) run local CI (unit + docker smoke)
Invoke-ApiUnitTests         # python -m pytest -q services/api
Invoke-DockerSmoke          # build, up, smoke, down

# 4) stage and commit
Stage-And-Commit -Message "feat: close #$IssueNumber — initial implementation"

# 5) (optional) run semgrep locally; fail if blocking
Invoke-Semgrep -ErrorOnFindings
```

> All helpers above come from `Agentic.Tools.psm1`. Keep script **idempotent**.

---

## 5) closing the loop (PR & issue)

If you ran the dispatcher with `-OpenPR`, it already pushed a branch and opened a PR.  
Otherwise:

```powershell
Open-PullRequest -Repo $Repo -Title "feat: blueprint schema (v0) + validator" -Body "Closes #12"
```

Close the issue on merge, or from CLI:

```powershell
gh issue close $IssueNumber --repo $Repo --comment "Implemented in PR #<id> ✅"
```

---

## 6) repo conventions

- **Issue name → script name**: title → lowercase kebab, strip punctuation.
- **Scripts live** in `tools/issues/`.
- **Helper module**: `tools/Agentic.Tools.psm1`  
  Must export:
  - `Get-IssueJson`, `Get-IssueSlug`
  - `New-WorkBranch`, `Stage-And-Commit`, `Open-PullRequest`
  - `Ensure-Venv`, `Invoke-ApiUnitTests`, `Invoke-DockerSmoke`, `Invoke-Semgrep`
  - `Write-Status`, `Write-ErrorExit` (logging conveniences)

---

## 7) common gotchas (quick fixes)

- **GH CLI can’t find repo**  
  Use the real slug:
  ```powershell
  $Repo = "YourUserOrOrg/agentic-sdlc"
  ```
- **Labels with spaces**  
  Quote **each** value: `--label "area:planner" --label "priority:normal"`
- **PowerShell 5.1 quirks**  
  Avoid `?.Source` (“null conditional”). Use `if (Get-Command ...) { (Get-Command ...).Source }`
- **`.env` formatting** (compose reads plain `KEY=VALUE` per line)  
  DO NOT write PowerShell arrays into `.env`. Use:
  ```
  POSTGRES_DB=appdb
  POSTGRES_USER=app
  POSTGRES_PASSWORD=app
  DB_HOST=db
  DB_PORT=5432
  DB_NAME=appdb
  DB_USER=app
  DB_PASSWORD=app
  ```
- **Port 8080 in use**  
  Change `ports:` in `docker-compose.yml` or free the port.
- **DB init race**  
  We use a `db-init` helper + retry loop; keep it in compose.
- **Local tests say “fastapi not found”**  
  You’re not using the venv. Run:
  ```powershell
  .\.venv\Scripts\Activate.ps1
  python -m pytest -q services/api
  ```
- **PUT /api/notes returns 405**  
  Use the included route signatures from tests; ensure `router.put("/{id}")` exists.

---

## 8) example: add a new issue end-to-end

```powershell
$Repo = "YourUserOrOrg/agentic-sdlc"

# create issue
$issue = gh issue create --repo $Repo `
  --title "Planner: generate OpenAPI + stubs" `
  --body "Extend planner to emit OpenAPI and route stubs; add tests and smoke." `
  --label "area:planner" --label "priority:normal" --json number --jq ".number"

# run it through dispatcher
tools\issue-dispatch.ps1 -Repo $Repo -IssueNumber $issue -OpenPR -DockerSmoke

# final local CI (just to be safe)
tools\sanity-check.ps1
```

---

## 9) CI policy

- Every PR runs:
  1) lint/format (optional, if configured),
  2) unit tests,
  3) semgrep blocking,
  4) container build + smoke.
- Merge only on green. PR must reference the issue (`Closes #N`).

---

## 10) where to put this doc

Commit this as `docs/DEV-MANUAL.md`, and link it from `README.md` under “Contributing”.
