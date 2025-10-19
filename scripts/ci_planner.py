#!/usr/bin/env python3
from __future__ import annotations
import json, os, sys
from pathlib import Path
from datetime import datetime, UTC

# Import your app helpers directly (no server needed)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))
import services.api.ui.plans as appmod  # type: ignore

def _read_event(path: str) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}

def main() -> int:
    repo_root = Path.cwd()
    event = _read_event(os.environ.get("GITHUB_EVENT_PATH", ""))

    # Derive a deterministic request text from PR context (fallbacks if run locally)
    pr = event.get("pull_request") or {}
    pr_num = pr.get("number") or os.environ.get("PR_NUMBER") or "local"
    pr_title = pr.get("title") or os.environ.get("PR_TITLE") or "Planner CI Execution"
    owner = (pr.get("user") or {}).get("login") or "ci"
    text = f"PR #{pr_num}: {pr_title}".strip()

    # Build deterministic artifact paths
    ts = datetime.now(UTC).strftime("%Y%m%d")
    slug = appmod._slugify(text)
    artifacts = {
        "openapi": f"docs/api/generated/openapi-{ts}-{slug}.yaml",
        "prd":     f"docs/prd/PRD-{ts}-{slug}.md",
        "adr":     f"docs/adrs/ADR-{ts}-{slug}.md",
        "stories": f"docs/stories/STORIES-{ts}-{slug}.md",
        "tasks":   f"docs/tasks/TASKS-{ts}-{slug}.md",
    }

    # Generate deterministic PRD/OpenAPI (no LLM in CI)
    os.environ["LLM_PROVIDER"] = ""
    prd_md = appmod.render_template("prd.md", {
        "vision": text,
        "users": ["End user", "Admin"],
        "scenarios": ["Create note", "List notes", "Delete note"],
        "metrics": ["Lead time", "Error rate"],
    })
    if "## Stack Summary" not in prd_md:
        prd_md = prd_md.rstrip() + "\n\n## Stack Summary\n- FastAPI\n- SQLite\n"
    if "## Acceptance Gates" not in prd_md:
        prd_md = prd_md.rstrip() + (
            "\n\n## Acceptance Gates\n"
            "- Coverage gate: minimum 80%\n"
            "- Linting passes\n"
            "- All routes return expected codes\n"
        )
    openapi_yaml = appmod._fallback_openapi_yaml()

    # Write artifacts
    repo_root.joinpath(artifacts["prd"]).parent.mkdir(parents=True, exist_ok=True)
    appmod._write_text_file(repo_root / artifacts["prd"], prd_md)
    repo_root.joinpath(artifacts["openapi"]).parent.mkdir(parents=True, exist_ok=True)
    appmod._write_text_file(repo_root / artifacts["openapi"], openapi_yaml)

    # Deterministic placeholders
    for k in ("adr", "stories", "tasks"):
        p = repo_root / artifacts[k]
        p.parent.mkdir(parents=True, exist_ok=True)
    appmod._write_text_file(repo_root / artifacts["adr"], f"# ADR: {text}\n\nStatus: Proposed\nDate: {ts}\n")
    appmod._write_text_file(repo_root / artifacts["stories"], f"# User Stories\n\n- As a user, I can: {text}\n")
    appmod._write_text_file(repo_root / artifacts["tasks"], "# Tasks\n\n- [ ] Implement API skeleton\n- [ ] Add tests\n")

    # Persist plan metadata into the DB (source of truth) + keep index.json for legacy
    plan_id = appmod._new_id("plan")
    engine = appmod._create_engine(appmod._database_url(repo_root))
    appmod.PlansRepoDB(engine).create({
        "id": plan_id, "request": text, "owner": owner, "artifacts": artifacts, "status": "new",
    })
    idx = appmod._load_index(repo_root)
    idx[plan_id] = {
        "id": plan_id, "request": text, "owner": owner, "artifacts": artifacts,
        "status": "new", "created_at": ts, "updated_at": ts,
    }
    appmod._save_index(repo_root, idx)

    # Emit outputs for GitHub Actions
    summary = [
        f"### Planner Execution",
        f"- **plan_id**: `{plan_id}`",
        f"- **request**: {text}",
        f"- **owner**: `{owner}`",
        f"- **PRD**: `{artifacts['prd']}`",
        f"- **OpenAPI**: `{artifacts['openapi']}`",
        f"- **ADR**: `{artifacts['adr']}`",
        f"- **Stories**: `{artifacts['stories']}`",
        f"- **Tasks**: `{artifacts['tasks']}`",
    ]
    if os.getenv("GITHUB_STEP_SUMMARY"):
        Path(os.environ["GITHUB_STEP_SUMMARY"]).write_text("\n".join(summary) + "\n", encoding="utf-8")
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write(f"plan_id={plan_id}\n")
            for k, v in artifacts.items():
                f.write(f"{k}_path={v}\n")

    print(json.dumps({"plan_id": plan_id, "artifacts": artifacts}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
