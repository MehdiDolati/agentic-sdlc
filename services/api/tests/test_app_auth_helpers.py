from __future__ import annotations

from starlette.requests import Request

from services.api.app import (
    AUTH_SECRET,
    _authed_user_id,
    _b64u,
    _b64u_decode,
    _extract_bearer_from_request,
)
from services.api.auth.tokens import create_token


def _request_with(headers: dict[str, str] | None = None, cookies: dict[str, str] | None = None) -> Request:
    header_items: list[tuple[bytes, bytes]] = []
    if headers:
        header_items.extend((key.lower().encode("latin-1"), value.encode("latin-1")) for key, value in headers.items())
    if cookies:
        cookie_header = "; ".join(f"{key}={value}" for key, value in cookies.items())
        header_items.append((b"cookie", cookie_header.encode("latin-1")))
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": header_items,
    }
    return Request(scope)


def test_authed_user_id_with_authorization_header() -> None:
    token = create_token(AUTH_SECRET, "user-123", "user@example.com")
    request = _request_with({"Authorization": f"Bearer {token}"})

    assert _authed_user_id(request) == "user-123"


def test_authed_user_id_cookie_fallback() -> None:
    token = create_token(AUTH_SECRET, "cookie-user", "cookie@example.com")
    request = _request_with(cookies={"session": token})

    assert _authed_user_id(request) == "cookie-user"


def test_authed_user_id_invalid_token_returns_none() -> None:
    request = _request_with({"Authorization": "Bearer not-a-valid-token"})

    assert _authed_user_id(request) is None


def test_extract_bearer_from_request_prefers_header_then_cookie_then_none() -> None:
    header_token = create_token(AUTH_SECRET, "header", "header@example.com")
    cookie_token = create_token(AUTH_SECRET, "cookie", "cookie@example.com")

    header_request = _request_with({"Authorization": f"Bearer {header_token}"})
    assert _extract_bearer_from_request(header_request) == header_token

    cookie_request = _request_with(cookies={"session": cookie_token})
    assert _extract_bearer_from_request(cookie_request) == cookie_token

    empty_request = _request_with()
    assert _extract_bearer_from_request(empty_request) is None


def test_b64u_round_trip_including_padding_case() -> None:
    original = b"agentic-sdlc"
    encoded = _b64u(original)
    assert _b64u_decode(encoded) == original

    needs_padding = b"padme"
    encoded_padding = _b64u(needs_padding)
    assert _b64u_decode(encoded_padding) == needs_padding
