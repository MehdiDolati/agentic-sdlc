#!/usr/bin/env python
import argparse
import os
import re
import sys
import subprocess
from pathlib import Path

try:
    import yaml
except Exception as e:
    print("PyYAML not installed. Run: pip install -r tools/requirements.txt", file=sys.stderr)
    raise

ROUTES_DIR = Path("services/api/routes")
TESTS_DIR = Path("services/api/tests")
APP_PATH = Path("services/api/app.py")
MANUAL_PATH = Path("docs/manuals/USER_MANUAL.md")
CHANGELOG_PATH = Path("CHANGELOG.md")

def load_spec(spec_path: Path) -> dict:
    with open(spec_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def infer_resource_from_paths(paths: dict) -> str:
    for p in paths.keys():
        if p.startswith("/api/") and "{" not in p and "}" not in p:
            seg = p[len("/api/"):].strip("/")
            if seg:
                return seg
    first = next(iter(paths.keys()))
    if first.startswith("/"):
        first = first[1:]
    return first.split("/")[1] if "/" in first else first

def spec_requires_bearer(spec: dict) -> bool:
    comps = (spec.get("components") or {}).get("securitySchemes") or {}
    return "bearerAuth" in comps

def create_route_content(resource: str, require_auth: bool) -> str:
    singular = resource[:-1] if resource.endswith("s") else resource
    auth_dep_line = "dependencies=[Depends(require_auth)], " if require_auth else ""
    auth_helper = """
from typing import Optional
from fastapi import Header, HTTPException
def require_auth(authorization: Optional[str] = Header(None)):
    if authorization is None or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    return True
""" if require_auth else ""

    return f"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel
from typing import Dict, List, Optional
from uuid import uuid4

{auth_helper}
router = APIRouter(prefix="/api/{resource}", tags=["{resource}"], {auth_dep_line})

class {singular.capitalize()}In(BaseModel):
    title: str = ""
    content: str = ""

class {singular.capitalize()}({singular.capitalize()}In):
    id: str

_DB: Dict[str, {singular.capitalize()}] = {{}}

@router.get("", response_model=List[{singular.capitalize()}])
def list_{resource}():
    return list(_DB.values())

@router.post("", status_code=status.HTTP_201_CREATED, response_model={singular.capitalize()})
def create_{singular}(item: {singular.capitalize()}In):
    obj = {singular.capitalize()}(id=str(uuid4()), **item.model_dump())
    _DB[obj.id] = obj
    return obj

@router.get("/"+"{id}", response_model={singular.capitalize()})
def get_{singular}(id: str):
    if id not in _DB:
        raise HTTPException(status_code=404, detail="{singular} not found")
    return _DB[id]

@router.put("/"+"{id}", response_model={singular.capitalize()})
def update_{singular}(id: str, item: {singular.capitalize()}In):
    if id not in _DB:
        raise HTTPException(status_code=404, detail="{singular} not found")
    obj = _DB[id].model_copy(update=item.model_dump())
    _DB[id] = obj
    return obj

@router.delete("/"+"{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_{singular}(id: str):
    if id not in _DB:
        raise HTTPException(status_code=404, detail="{singular} not found")
    del _DB[id]
    return None
"""

def ensure_router_in_app(resource: str):
    Path("services/api/__init__.py").write_text("", encoding="utf-8")
    app_src = APP_PATH.read_text(encoding="utf-8")
    import_block = f"""
try:
    from .routes.{resource} import router as {resource}_router
except ImportError:
    from routes.{resource} import router as {resource}_router
"""
    include_line = f"app.include_router({resource}_router)\n"

    if f"routes.{resource} import router as {resource}_router" not in app_src:
        parts = app_src.split("app = FastAPI", 1)
        if len(parts) == 2:
            head, tail = parts
            head = head + import_block + "app = FastAPI" + tail
            app_src = head
        else:
            app_src = import_block + app_src
    if include_line not in app_src:
        if "\n@app.get" in app_src:
            app_src = app_src.replace("\n@app.get", f"\n{include_line}\n@app.get", 1)
        else:
            app_src = app_src + "\n" + include_line
    APP_PATH.write_text(app_src, encoding="utf-8")

def create_test_content(resource: str, require_auth: bool) -> str:
    hdrs = 'headers={"Authorization": "Bearer test"}' if require_auth else ""
    comma = "," if hdrs else ""
    return f"""
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_{resource}_crud_flow():

    r = client.get("/api/{resource}/" + _id{comma} {hdrs})
    assert r.status_code == 200
    assert r.json() == []

    r = client.post("/api/{resource}"{comma} {hdrs}, json={{"title": "t", "content": "c"}})
    assert r.status_code == 201
    created = r.json()
    _id = created["id"]

    r = client.get("/api/{resource}/" + _id{comma} {hdrs})
    assert r.status_code == 200
    assert r.json()["title"] == "t"

    r = client.put("/api/{resource}/" + _id{comma} {hdrs}, json={"title": "t2", "content": "c2"})
    assert r.status_code == 200
    assert r.json()["title"] == "t2"

    r = client.delete("/api/{resource}/" + _id{comma} {hdrs})
    assert r.status_code == 204

    r = client.get("/api/{resource}/" + _id{comma} {hdrs})
    assert r.status_code == 404
"""

    hdrs = 'headers={"Authorization": "Bearer test"}' if require_auth else ""
    comma = "," if hdrs else ""
    return f"""
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_{resource}_crud_flow():
    r = client.get("/api/{resource}"{comma} {hdrs})
    assert r.status_code == 200
    assert r.json() == []

    r = client.post("/api/{resource}"{comma} {hdrs}, json={{"title": "t", "content": "c"}})
    assert r.status_code == 201
    created = r.json()
    _id = created["id"]

    r = client.get(f"/api/{resource}/{{_id}}"{comma} {hdrs})
    assert r.status_code == 200
    assert r.json()["title"] == "t"

    r = client.put(f"/api/{resource}/{{_id}}"{comma} {hdrs}, json={{"title": "t2", "content": "c2"}})
    assert r.status_code == 200
    assert r.json()["title"] == "t2"

    r = client.delete(f"/api/{resource}/{{_id}}"{comma} {hdrs})
    assert r.status_code == 204

    r = client.get(f"/api/{resource}/{{_id}}"{comma} {hdrs})
    assert r.status_code == 404
"""

def update_manual_and_changelog(resource: str):
    MANUAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    prev = MANUAL_PATH.read_text(encoding="utf-8") if MANUAL_PATH.exists() else "# User Manual\n"
    add = f"""
## {resource.capitalize()} endpoints
- `GET /api/{resource}`
- `POST /api/{resource}`
- `GET /api/{resource}/{{id}}`
- `PUT /api/{resource}/{{id}}`
- `DELETE /api/{resource}/{{id}}`
"""
    if add not in prev:
        MANUAL_PATH.write_text(prev + add, encoding="utf-8")

    ch = CHANGELOG_PATH.read_text(encoding="utf-8") if CHANGELOG_PATH.exists() else "# Changelog\n"
    entry = f"- feat({resource}): scaffolded CRUD API and tests\n"
    if entry not in ch:
        CHANGELOG_PATH.write_text(ch + entry, encoding="utf-8")

def maybe_git(actions: dict, enable_git: bool, open_pr: bool, branch: str):
    if not enable_git:
        return
    def run(cmd):
        subprocess.check_call(cmd, shell=True)
    try:
        run("git rev-parse --is-inside-work-tree")
    except subprocess.CalledProcessError:
        run("git init")
    try:
        run(f'git checkout -b {branch}')
    except subprocess.CalledProcessError:
        run(f'git checkout {branch}')
    run("git add .")
    run(f'git commit -m "feat: scaffold {actions.get("resource","resource")} API and tests"')
    if open_pr:
        try:
            run("git push -u origin HEAD")
            title = f'feat({actions.get("resource")}): scaffold API + tests'
            body = f'Auto-generated from spec: {actions.get("spec")}'
            run(f'gh pr create --title "{title}" --body "{body}"')
        except subprocess.CalledProcessError:
            print("Note: skipping PR (missing remote or gh not configured).", file=sys.stderr)

def main():
    ap = argparse.ArgumentParser(description="Dev Agent: scaffold FastAPI routes/tests from OpenAPI")
    ap.add_argument("--spec", required=True, help="Path to OpenAPI YAML file")
    ap.add_argument("--resource", help="Resource name (if not provided, derived from spec)")
    ap.add_argument("--git", action="store_true", help="Create branch and commit changes")
    ap.add_argument("--pr", action="store_true", help="Open a PR with gh CLI (requires --git)")
    args = ap.parse_args()

    spec_path = Path(args.spec)
    spec = load_spec(spec_path)
    resource = args.resource or infer_resource_from_paths(spec.get("paths", {}))
    require_auth = spec_requires_bearer(spec)

    ROUTES_DIR.mkdir(parents=True, exist_ok=True)
    route_file = ROUTES_DIR / f"{resource}.py"
    route_file.write_text(create_route_content(resource, require_auth), encoding="utf-8")

    ensure_router_in_app(resource)

    test_file = TESTS_DIR / f"test_{resource}_routes.py"
    test_file.write_text(create_test_content(resource, require_auth), encoding="utf-8")

    update_manual_and_changelog(resource)

    actions = {"resource": resource, "spec": str(spec_path)}
    print({"generated": {"route": str(route_file), "test": str(test_file), "resource": resource}, "auth_required": require_auth})

    if args.git:
        branch = f"feat/{resource}-scaffold"
        maybe_git(actions, enable_git=True, open_pr=args.pr, branch=branch)

if __name__ == "__main__":
    main()
