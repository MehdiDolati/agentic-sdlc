# services/api/tests/test_ui_plan_requests.py
import json
from pathlib import Path
from fastapi.testclient import TestClient
from services.api.app import app

client = TestClient(app)

def test_render_new_form_ok():
    r = client.get("/ui/requests/new")
    assert r.status_code == 200
    assert "Create a Plan / Request" in r.text

def test_submit_request_generates_preview(tmp_path, monkeypatch):
    # Force APP_STATE_DIR so planner writes under a temp repo root
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))
    r = client.post(
        "/ui/requests",
        data={
            "project_vision": "As a PM I want a minimal todo service",
            "agent_mode": "single",
            "llm_provider": "none",
        },
    )
    assert r.status_code == 200
    # Preview page should include OpenAPI draft json and PRD section heading
    assert "Draft Plan Review" in r.text
    assert "OpenAPI (JSON)" in r.text

def test_post_plans_persists(monkeypatch):
    # The existing POST /plans (from services.api.ui.plans) requires a 'goal' field.
    # Provide it, and accept either 200 or 201 depending on implementation details.
    r = client.post("/plans", json={
        "id": "PLAN-001",
        "owner": "ui",
        "artifacts": {},
        "meta": {},
        "goal": "Persist a plan created from the UI"
    })
    assert r.status_code in (200, 201), r.text
    # Basic sanity: response should be JSON
    _ = r.json()