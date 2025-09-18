import os
import pytest
from services.api.core import shared, settings as cfg

def test_repo_root_cache_and_reset(tmp_path, monkeypatch):
    # Set and cache the path
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    p1 = shared._repo_root()
    # Change env but keep cache -> should remain old until reset
    new_root = tmp_path / "other"
    new_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("REPO_ROOT", str(new_root))
    p2 = shared._repo_root()
    assert str(p2) == str(p1)
    # Reset cache -> picks up new env value
    shared._reset_repo_root_cache_for_tests()
    p3 = shared._repo_root()
    assert str(p3) == str(new_root)

def test_ensure_dir_creates_path(tmp_path):
    target = tmp_path / "x" / "y"
    assert not target.exists()
    # _ensure_dir may be private; call through any public wrapper if present
    fn = getattr(shared, "_ensure_dir", None)
    if fn is None:
        pytest.skip("_ensure_dir not exposed")
    fn(target)
    assert target.exists() and target.is_dir()
