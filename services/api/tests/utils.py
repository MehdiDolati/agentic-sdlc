# services/api/tests/utils.py
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from starlette.testclient import TestClient

from services.api.app import app
from services.api.core import shared

# PlanStore is lightweight and file-based; good for seeding test data quickly.
try:
    from services.api.storage.plan_store import PlanStore  # our simple JSON store
    _HAS_PLANSTORE = True
except Exception:
    _HAS_PLANSTORE = False
    PlanStore = None  # type: ignore[assignment]


def _client() -> TestClient:
    """Return a TestClient bound to the real app (no server exceptions)."""
    return TestClient(app, raise_server_exceptions=False)


def _route_exists(path: str, method: str = "GET") -> bool:
    """Check if (path, method) is mounted on the FastAPI app."""
    m = method.upper()
    for r in app.routes:
        rp = getattr(r, "path", "") or getattr(r, "path_format", "")
        methods = getattr(r, "methods", set()) or set()
        if rp == path and (m in methods or not methods):
            return True
    return False


def _retarget_store(tmp_path: Path) -> None:
    """
    Point repo-rooted file IO into a test temp directory.
    Use this if a test didn’t already set REPO_ROOT.
    """
    os.environ["REPO_ROOT"] = str(tmp_path)
    shared._reset_repo_root_cache_for_tests()


def _seed_plan(
    tmp_path: Path,
    *,
    owner: str = "owner1",
    status: str = "open",
    text: str = "build something great",
    artifacts: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Create a minimal plan on disk so /ui/plans and related routes have something to render.
    Prefers PlanStore (file JSON) to avoid DB coupling.
    """
    os.environ["REPO_ROOT"] = str(tmp_path)
    shared._reset_repo_root_cache_for_tests()
    artifacts = artifacts or {}

    pid = f"p_{uuid.uuid4().hex[:6]}"
    plan = {
        "id": pid,
        "owner": owner,
        "status": status,
        # many views look at free-text fields under meta/request or similar
        "meta": {"request": text},
        "artifacts": artifacts,  # e.g. {"prd": "# Title", "tasks": "- [ ] do x"}
    }

    # If PlanStore is available, persist there; otherwise, fall back to a simple file.
    if _HAS_PLANSTORE and PlanStore is not None:
        store_dir = Path(tmp_path) / "docs" / "plans"
        store = PlanStore(root_dir=store_dir)
        store.save(plan)
    else:
        # Fallback: write JSON next to where UI typically reads plan docs
        plans_dir = Path(tmp_path) / "docs" / "plans"
        plans_dir.mkdir(parents=True, exist_ok=True)
        # filename shape is not strictly required by UI for listing; keep it simple:
        (plans_dir / f"{pid}.json").write_text(__import__("json").dumps(plan), encoding="utf-8")

    return plan
