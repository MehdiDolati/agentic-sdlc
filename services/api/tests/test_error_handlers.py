from pathlib import Path
from fastapi.testclient import TestClient
from services.api.app import app

client = TestClient(app, raise_server_exceptions=False)

def test_htmx_404_flash(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))
    r = client.get("/ui/plans/NOPE/sections/prd", headers={"HX-Request": "true"})
    assert r.status_code == 404
    assert 'id="flash"' in r.text

def test_htmx_500_flash(monkeypatch, tmp_path: Path):
    import services.api.ui.plans as ui_plans
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))
    # boom in repo.get
    orig = ui_plans.PlansRepoDB.get
    def boom(self, *_a, **_k): raise RuntimeError("kaboom")
    try:
        from fastapi.testclient import TestClient
        monkeypatch.setattr(ui_plans.PlansRepoDB, "get", boom)
        client2 = TestClient(app, raise_server_exceptions=False)
        r = client2.get("/ui/plans/XYZ/sections/tasks", headers={"HX-Request": "true"})
        assert r.status_code == 500
        assert 'id="flash"' in r.text
    finally:
        monkeypatch.setattr(ui_plans.PlansRepoDB, "get", orig)
