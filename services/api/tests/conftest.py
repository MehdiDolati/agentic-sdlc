import os, sys
from pathlib import Path
import importlib, sys, pytest, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

@pytest.fixture(autouse=True)
def repo_root(tmp_path, monkeypatch):
    # If your tests expect a "repo/" subdir, decide it here:
    root = tmp_path / "repo"          # or just tmp_path
    root.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("REPO_ROOT", str(root))

    # Reload the module that caches the repo root
    import services.api.core.shared as shared
    importlib.reload(shared)

    return root

@pytest.fixture(autouse=True)
def repo_root(tmp_path, monkeypatch):
    root = tmp_path  # or tmp_path / "repo", but be consistent
    monkeypatch.setenv("REPO_ROOT", str(root))
    # Nuke any stray DATABASE_URL too (seen suites bitten by this)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    # Reload shared FIRST
    import services.api.core.shared as shared
    importlib.reload(shared)
    shared._reset_repo_root_cache_for_tests()

    # Reload anything that might have from-imported shared
    for m in [
        "services.api.core.repos",
        "services.api.ui.plans",
        "services.api.app",
    ]:
        if m in sys.modules:
            importlib.reload(sys.modules[m])

    # Ensure the db dir exists proactively (defense-in-depth)
    (root / "docs" / "plans").mkdir(parents=True, exist_ok=True)
    return root
