from fastapi.testclient import TestClient
from services.api.app import app
from pathlib import Path
import importlib

client = TestClient(app)

def test_prd_contains_stack_summary_and_gates(repo_root):
    r = client.post("/requests", json={"text": "Build a notes service with auth"})
    assert r.status_code == 200
    data = r.json()
    prd_rel = data["artifacts"]["prd"]

    # Correct path to 'services/docs'
    prd_path = repo_root / prd_rel
    content = prd_path.read_text(encoding="utf-8")

    assert "## Stack Summary (Selected)" in content
    assert "Language:" in content
    assert "Backend Framework:" in content
    assert "Coverage gate:" in content
