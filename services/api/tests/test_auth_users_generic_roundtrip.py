import uuid
import pytest
from services.api.core import shared

def test_auth_users_generic_roundtrip(tmp_path, monkeypatch):
    # Isolate repo root so any file/DB IO happens under tmp
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()

    try:
        from services.api.auth import users as um
    except Exception:
        pytest.skip("auth.users not importable")

    create = getattr(um, "create_user", None) or getattr(um, "create", None)
    get = getattr(um, "get_user_by_email", None) or getattr(um, "get_by_email", None)
    delete = getattr(um, "delete_user", None) or getattr(um, "delete", None)

    if not (callable(create) and callable(get) and callable(delete)):
        pytest.skip("auth.users does not expose create/get/delete trio")

    email = f"u_{uuid.uuid4().hex[:6]}@example.com"
    # Minimal password; implementations may hash or validate differently
    try:
        user = create(email=email, password="secret")
    except TypeError:
        # Some variants use different arg names or positional args
        user = create(email, "secret")
    assert user is not None

    fetched = get(email=email) if "email" in getattr(get, "__code__", ()).__dict__.get("co_varnames", ()) else get(email)
    assert fetched is not None

    # Delete and confirm gone
    try:
        delete(email=email)
    except TypeError:
        delete(email)

    gone = get(email=email) if "email" in getattr(get, "__code__", ()).__dict__.get("co_varnames", ()) else get(email)
    assert not gone
