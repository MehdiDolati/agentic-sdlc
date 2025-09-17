from pathlib import Path
from fastapi.testclient import TestClient
from services.api.app import app
from services.api.core.shared import _create_engine, _database_url, _new_id
from services.api.core.repos import PlansRepoDB

client = TestClient(app, raise_server_exceptions=False)

def _seed_plan(tmp_path: Path) -> str:
    pid = _new_id("plan")
    eng = _create_engine(_database_url(tmp_path))
    (tmp_path / f"docs/tasks/{pid}.md").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / f"docs/tasks/{pid}.md").write_text("- [ ] task one\n", encoding="utf-8")
    PlansRepoDB(eng).create({"id": pid,"request":"gh","owner":"ui","artifacts":{"tasks":f"docs/tasks/{pid}.md"},"status":"new"})
    return pid

def test_bulk_issues_not_configured(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))
    # Ensure missing token/repo
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPO", raising=False)
    pid = _seed_plan(tmp_path)
    r = client.post(f"/ui/plans/{pid}/board/bulk_issues", data={"kind":"tasks","only_open":"on"}, headers={"HX-Request":"true"})
    assert r.status_code in (200, 400, 404)  # returns table with flash error
    assert 'id="flash"' in r.text

def test_bulk_issues_http_unauthorized(monkeypatch, tmp_path: Path):
    # Configure fake repo/token, but force HTTPError
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    monkeypatch.setenv("GITHUB_REPO", "o/r")
    import services.api.integrations.github as gh
    class FakeGH(gh.GH):
        def __init__(self,*a,**k): pass
        def create_issue(self, *a, **k):
            from requests import Response
            from requests.exceptions import HTTPError
            resp = Response(); resp.status_code = 401
            raise HTTPError("unauthorized", response=resp)
    monkeypatch.setattr(gh, "GH", FakeGH)
    pid = _seed_plan(tmp_path)
    r = client.post(f"/ui/plans/{pid}/board/bulk_issues", data={"kind":"tasks","only_open":"on"}, headers={"HX-Request":"true"})
    assert r.status_code == 401
    assert 'id="flash"' in r.text
