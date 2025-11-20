# ...existing code...
import pytest
import services.api.core.shared as shared

@pytest.fixture(autouse=True)
def isolate_env_and_cache(monkeypatch):
    # Ensure env vars do not leak into tests
    monkeypatch.delenv("APP_STATE_DIR", raising=False)
    monkeypatch.delenv("REPO_ROOT", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AUTH_ENABLED", raising=False)
    monkeypatch.delenv("AUTH_MODE", raising=False)
    
    # Set up mock LLM provider for all tests
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    
    # Clear the shared module repo-root cache before each test
    if hasattr(shared, "_reset_repo_root_cache_for_tests"):
        shared._reset_repo_root_cache_for_tests()
    yield
    # cleanup after test
    monkeypatch.delenv("APP_STATE_DIR", raising=False)
    monkeypatch.delenv("REPO_ROOT", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AUTH_ENABLED", raising=False)
    monkeypatch.delenv("AUTH_MODE", raising=False)
    if hasattr(shared, "_reset_repo_root_cache_for_tests"):
        shared._reset_repo_root_cache_for_tests()

@pytest.fixture
def repo_root(tmp_path, monkeypatch):
    """
    Fixture that provides a temporary repo root directory and sets it in the environment.
    """
    # Set up the environment
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    
    # Create basic directory structure that might be expected
    (tmp_path / "docs" / "prd").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "api" / "generated").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "plans").mkdir(parents=True, exist_ok=True)
    
    return tmp_path