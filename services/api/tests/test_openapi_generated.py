from fastapi.testclient import TestClient
from app import app
import yaml
import importlib
from pathlib import Path

client = TestClient(app)

def test_openapi_is_generated_with_paths_and_auth(tmp_path: Path, monkeypatch, repo_root):
    r = client.post("/requests", json={"text": "Build a notes service with auth"})
    assert r.status_code == 200
    data = r.json()
    openapi_rel = data["artifacts"]["openapi"]

    # Correct path to 'services/docs'
    openapi_path = repo_root / openapi_rel
    assert openapi_path.exists()

    spec = yaml.safe_load(openapi_path.read_text(encoding="utf-8"))
    assert "/api/notes" in spec.get("paths", {})
    comps = spec.get("components", {}).get("securitySchemes", {})
    assert "bearerAuth" in comps
