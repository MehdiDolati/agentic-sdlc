# Architecture Overview

This document describes the architecture of the **Autonomous Agentic SDLC System**.

---

## High-Level Design
The system automates the **entire SDLC**:
- From **requirements capture** (issues, PRDs)
- To **code generation** (API scaffolds, CRUD)
- To **testing** (unit, smoke, CI gates)
- To **delivery** (PR automation, validation)

---

## Components
### 1. API Service
- Built with **FastAPI**
- Exposes endpoints for planner, notes, health
- Connects to **PostgreSQL** DB
- Runs under **Uvicorn** in Docker

### 2. Planner
- Generates:
  - PRD (Product Requirements Document)
  - ADR (Architecture Decision Record)
  - User Stories & Tasks
  - OpenAPI schema

### 3. Dev Agent
- Consumes OpenAPI schema
- Generates:
  - CRUD scaffolds
  - Unit tests
  - Pull Requests

### 4. QA Agent
- Runs coverage checks (`pytest + coverage`)
- Blocks merges below threshold
- Runs **Semgrep** security scans

---

## Tooling
- **PowerShell automation**
  - `tools/local-ci.ps1` → run local tests before push
  - `tools/issue-dispatch.ps1` → map issues → scripts
- **GitHub Issues as Work Units**
  - Each issue maps to a script in `tools/issues/`
  - Dispatcher ensures issue is executed consistently

---

## Data Flow
1. Developer opens a GitHub issue
2. Dispatcher picks script → executes
3. Local CI validates results
4. On success → PR created
5. On merge → issue closed

---

## Future Roadmap
- More sophisticated PRD → Code pipelines
- AI-assisted refactoring & code review
- Multi-service orchestration
