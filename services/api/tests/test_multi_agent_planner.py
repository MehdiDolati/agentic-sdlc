from __future__ import annotations

from pathlib import Path
from fastapi.testclient import TestClient
import importlib
import os
import services.api.app as appmod
import pytest
import services.api.core.shared as shared

def _setup_app(tmp_path: Path):
    import services.api.app as app_module
    importlib.reload(app_module)
    app_module.app.state.repo_root = str(tmp_path)
    return app_module.app

def test_multi_agent_generates_prd_openapi_adr(tmp_path, monkeypatch):
    # enable multi-agent
    monkeypatch.setenv("PLANNER_MODE", "multi")
    # deterministic path (no LLM needed)
    monkeypatch.setenv("LLM_PROVIDER", "")
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()

    app = _setup_app(tmp_path)
    # Override auth dependency so we don't rely on /login
    app.dependency_overrides[appmod.get_current_user] = lambda: {
        "id": "u_test",
        "email": "agent@example.com",
    }
    client = TestClient(app)
    r = client.post("/requests", json={"text": "Search on notes list"})
    assert r.status_code == 200
    j = r.json()
    artifacts = j.get("artifacts") or {}
    assert "prd" in artifacts and "openapi" in artifacts and "adr" in artifacts

    # Files exist on disk
    repo_root = shared._repo_root()
    prd_p = repo_root / artifacts["prd"]
    oas_p = repo_root / artifacts["openapi"]
    adr_p = repo_root / artifacts["adr"]
    assert prd_p.exists() and oas_p.exists() and adr_p.exists()

    # Quick content sanity (keep assertions light to avoid brittleness)
    prd_txt = prd_p.read_text(encoding="utf-8")
    oas_txt = oas_p.read_text(encoding="utf-8")
    adr_txt = adr_p.read_text(encoding="utf-8")

    assert "## Stack Summary" in prd_txt
    assert "openapi:" in oas_txt.splitlines()[0]
    assert ("## Decision" in adr_txt) or ("Status:" in adr_txt and "Date:" in adr_txt)

    # cleanup module to avoid cross-test state
    import sys
    sys.modules.pop("services.api.app", None)
