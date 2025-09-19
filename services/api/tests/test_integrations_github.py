import types
import requests
import pytest
from services.api.integrations.github import GH


def _resp(status=200, json=None):
    r = requests.Response()
    r.status_code = status
    r._content = (b"{}" if json is None else str.encode(__import__("json").dumps(json)))
    return r


def test_ctor_validation():
    with pytest.raises(ValueError):
        GH("", "")
    with pytest.raises(ValueError):
        GH("token", "badrepoformat")
    # ok
    GH("t", "o/r")


def test_ensure_branch_create_and_already_exists(monkeypatch):
    gh = GH("t", "o/r")
    calls = []

    def fake_get(url, headers=None, timeout=None):
        calls.append(("GET", url))
        if url.endswith("/git/ref/heads/main"):
            return _resp(200, {"object": {"sha": "base"}})
        if url.endswith("/git/commits/base"):
            return _resp(200, {"tree": {"sha": "tree"}})
        if url.endswith("/git/ref/heads/feat"):
            return _resp(200, {"object": {"sha": "exists"}})
        return _resp(200, {})

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(("POST", url))
        # first call creates ref; return 201 → created
        if url.endswith("/git/refs"):
            return _resp(201, {"ref": "refs/heads/feat"})
        return _resp(200, {})

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(requests, "post", fake_post)

    created = gh.ensure_branch("main", "feat")
    assert created.get("ref") == "refs/heads/feat"

    # Now simulate "already exists" by making POST /git/refs return non-201
    def post_exists(url, headers=None, json=None, timeout=None):
        calls.append(("POST", url))
        if url.endswith("/git/refs"):
            return _resp(422, {"message": "already exists"})
        return _resp(200, {})

    monkeypatch.setattr(requests, "post", post_exists)
    existed = gh.ensure_branch("main", "feat")
    # falls back to GET ref
    assert existed["object"]["sha"] == "exists"


def test_upsert_files_and_open_pr(monkeypatch):
    gh = GH("t", "o/r")
    calls = []

    def fake_get(url, headers=None, timeout=None):
        calls.append(("GET", url))
        if url.endswith("/git/ref/heads/feat"):
            return _resp(200, {"object": {"sha": "latest"}})
        if url.endswith("/git/commits/latest"):
            return _resp(200, {"tree": {"sha": "tree"}})
        return _resp(200, {})

    blob_counter = {"n": 0}

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(("POST", url))
        if url.endswith("/git/blobs"):
            blob_counter["n"] += 1
            return _resp(201, {"sha": f"blob{blob_counter['n']}"})
        if url.endswith("/git/trees"):
            return _resp(201, {"sha": "treesha"})
        if url.endswith("/git/commits"):
            return _resp(201, {"sha": "commitsha"})
        if url.endswith("/pulls"):
            return _resp(201, {"number": 7})
        return _resp(200, {})

    def fake_patch(url, headers=None, json=None, timeout=None):
        calls.append(("PATCH", url))
        return _resp(200, {"ok": True})

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(requests, "patch", fake_patch)

    up = gh.upsert_files("feat", [("a.txt", "A"), ("b.txt", "B")], "msg")
    assert up["commit"] == "commitsha"

    pr = gh.open_pr("feat", "main", "title", "body")
    assert pr["number"] == 7


def test_github_http_error_bubbles(monkeypatch):
    gh = GH("t", "o/r")

    def bad_post(url, headers=None, json=None, timeout=None):
        r = _resp(401, {"message": "bad auth"})
        raise requests.HTTPError(response=r)

    monkeypatch.setattr(requests, "post", bad_post)
    with pytest.raises(requests.HTTPError):
        gh.create_issue("x")
