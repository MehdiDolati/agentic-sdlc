# Contributing Guide

Welcome to the **Autonomous Agentic SDLC System**.  
This document explains how developers should contribute, test, and interact with the system.

---

## Prerequisites
- **Windows + PowerShell 5+** (or PowerShell 7+ if available)
- **Docker Desktop**
- **Python 3.11** (with `venv`)
- **GitHub CLI (`gh`)** (authenticated with your account)

---

## Workflow Overview
This repo uses an **issue-driven workflow**:
1. **Create an issue** describing the task.  
2. **Dispatch the issue** via PowerShell, which:  
   - Generates/executes a script in `tools/issues/`  
   - Runs local CI (tests, smoke tests, static analysis)  
   - Optionally opens a PR if successful  
3. **Close the issue** once validated.

---

## Creating Issues
You can use GitHub’s web UI or CLI.

Example (CLI):
```powershell
gh issue create --repo MehdiDolati/agentic-sdlc `
  --title "Blueprint schema (v0) + validator" `
  --body "Define schema, write validator, add tests." `
  --label "area:orchestrator,priority:normal"
```

---

## Dispatching Issues
Run the dispatcher to execute the issue script:

```powershell
tools/issue-dispatch.ps1 -Repo "MehdiDolati/agentic-sdlc" `
  -IssueNumber 1 -OpenPR -DockerSmoke
```

Flags:
- `-OpenPR` → Automatically opens a PR after success.
- `-DockerSmoke` → Runs Dockerized smoke tests.

---

## Local CI (Sanity Check)
Before pushing, always run:

```powershell
tools/local-ci.ps1
```

This script will:
- Mount docker & ensure services start
- Load `.venv` and install requirements
- Run unit tests and smoke tests
- Run semgrep static analysis

If all checks pass, you are safe to push.

---

## Extending the System
- Add new automation under `tools/issues/<slug>.ps1`
- Follow the naming convention: slug is derived from issue title (lowercase, hyphens).
- Ensure your script calls `Invoke-LocalCI` at the end.

---

## Closing Issues
Once an issue’s PR is merged and CI is green, close it:

```powershell
gh issue close <number> --comment "Resolved in PR #<PR number>"
```

---

# Dev Workflow (Issues → Branch → PR → Merge)

This project includes **automation** to take an open GitHub issue, run local tests/smoke, open a PR with a proper `Closes #N` footer, apply labels, and optionally wait/merge when green — **one command**.

## Prereqs

- **GitHub CLI** (`gh`) installed and authenticated:
  ```powershell
  gh auth login
  gh auth status
