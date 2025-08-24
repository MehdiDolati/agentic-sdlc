# Agentic SDLC

An **Autonomous Agentic Software Development Lifecycle (SDLC) System** that automates planning, code generation, testing, and delivery.  
The core vision is to **automate the entire SDLC** end-to-end — generating not only requirements and plans, but also the full source code of the final product.

---

## 🚀 Features
- **Automated Planning** — Blueprint schema and validators for PRDs.
- **Code Generation** — Generate initial implementations from specifications.
- **CI/CD Automation** — Pre-push checks with local smoke tests.
- **Infrastructure as Code** — Reproducible development with Docker and Docker Compose.
- **Agentic Workflow** — Issues drive automation, with per-issue PowerShell dispatch scripts.

---

## 📦 Project Structure
```plaintext
services/api/      # FastAPI service
services/api/tests # Unit & smoke tests
tools/             # PowerShell automation scripts
docs/              # PRDs and supporting docs
```

---

## 🛠️ Local Development

### 1. Clone the repo
```powershell
git clone https://github.com/MehdiDolati/agentic-sdlc.git
cd agentic-sdlc
```

### 2. Setup Python virtual environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r services/api/requirements.txt
```

### 3. Run the local CI sanity check
We provide a batch/PowerShell script that:
- Mounts Docker,
- Installs requirements in `.venv`,
- Runs unit tests,
- Runs smoke tests.

```powershell
tools\local-ci.ps1
```

Only push after this script passes ✅

---

## 🧪 Running Tests
### Unit tests
```powershell
python -m pytest -q services/api
```

### Smoke tests in Docker
```powershell
docker compose up --build --exit-code-from api
```

---

## 🔄 Workflow with Issues
1. Create a GitHub issue describing the feature/task.  
2. Dispatch it locally:
   ```powershell
   tools\issue-dispatch.ps1 -Repo "MehdiDolati/agentic-sdlc" -IssueNumber <N> -OpenPR -DockerSmoke
   ```
3. Work through the generated script under `tools/issues/`.
4. Run local CI and Docker smoke tests.
5. Once all pass, push changes and close the issue.

For details, see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 📐 Architecture
See [ARCHITECTURE.md](ARCHITECTURE.md) for:
- System design
- Module responsibilities
- Data flows (planner → repo → API → tests)

---

## 🤝 Contributing
- Follow [CONTRIBUTING.md](CONTRIBUTING.md) for workflow and coding guidelines.
- Always ensure **local CI passes** before opening a PR.
- Issues are the single source of truth — all development is tied to them.

---

## 📄 License
MIT
