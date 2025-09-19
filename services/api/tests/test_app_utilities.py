from pathlib import Path
from typing import Any, Dict

import pytest
from starlette.requests import Request

from services.api.app import _ci_or_pytest, _ensure_dir, _user_from_http


def _make_request(
    headers: Dict[str, str] | None = None, cookies: Dict[str, str] | None = None
) -> Request:
    raw_headers = []
    headers = headers or {}
    for key, value in headers.items():
        raw_headers.append((key.lower().encode("latin-1"), value.encode("latin-1")))
    if cookies:
        cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())
        raw_headers.append((b"cookie", cookie_header.encode("latin-1")))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": raw_headers,
    }

    async def receive() -> Dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive=receive)


@pytest.mark.parametrize("env_var", ["CI", "PYTEST_CURRENT_TEST"])
def test_ci_or_pytest_env_detection(
    monkeypatch: pytest.MonkeyPatch, env_var: str
) -> None:
    # Clear both environment variables for the duration of the test
    for key in ("CI", "PYTEST_CURRENT_TEST"):
        monkeypatch.delenv(key, raising=False)

    assert _ci_or_pytest() is False

    monkeypatch.setenv(env_var, "1")
    assert _ci_or_pytest() is True


def test_ensure_dir_creates_path(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "dir"
    assert not target.exists()

    _ensure_dir(target)

    assert target.exists() and target.is_dir()


def test_user_from_http_defaults_to_public() -> None:
    request = _make_request()

    user = _user_from_http(request)

    assert user == {"id": "public", "email": "public@example.com"}


def test_user_from_http_authenticated(monkeypatch: pytest.MonkeyPatch) -> None:
    request = _make_request(headers={"Authorization": "Bearer token"})

    payload = {"uid": "user-123", "email": "User@Example.COM"}
    monkeypatch.setattr("services.api.app.read_token", lambda secret, token: payload)

    user = _user_from_http(request)

    assert user == {"id": "user-123", "email": "user@example.com"}
