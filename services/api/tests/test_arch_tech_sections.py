from pathlib import Path
from fastapi.testclient import TestClient
from services.api.app import app
from services.api.core.shared import _create_engine, _database_url, _new_id
from services.api.core.repos import PlansRepoDB

client = TestClient(app)

def _seed_plan(tmp_path: Path, vision="Arch/Tech"):
    plan_id = _new_id("plan")
    engine = _create_engine(_database_url(tmp_path))
    PlansRepoDB(engine).create({
        "id": plan_id,
        "request": vision,
        "owner": "ui",
        "artifacts": {},  # start empty; routes must tolerate and create rels
        "status": "new",
    })
    return plan_id

def test_arch_generate_and_edit(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))
    pid = _seed_plan(tmp_path)
    # generate
    r = client.post(f"/ui/plans/{pid}/architecture/generate")
    assert r.status_code == 200
    assert "Architecture Overview" in r.text
    # edit
    r2 = client.post(f"/ui/plans/{pid}/artifacts/architecture/edit", data={"content": "# Arch\n\nA"})
    assert r2.status_code == 200
    assert "Arch" in r2.text

def test_techspec_generate_and_upload(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))
    pid = _seed_plan(tmp_path)
    r = client.post(f"/ui/plans/{pid}/techspec/generate")
    assert r.status_code == 200
    assert "Technology Stack" in r.text
    # upload text file
    files = {"file": ("spec.md", "# Tech\n\nB", "text/markdown")}
    r2 = client.post(f"/ui/plans/{pid}/techspec/upload", files=files)
    assert r2.status_code == 200
    assert "Tech" in r2.text
