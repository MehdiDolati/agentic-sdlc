# services/api/executor.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List, Set
import yaml

def _latest_openapi(repo_root: Path) -> Path | None:
    gen = repo_root / "docs" / "api" / "generated"
    if not gen.exists():
        return None
    candidates = sorted(gen.glob("openapi-*.yaml"))
    return candidates[-1] if candidates else None

def execute_plan(plan: Dict[str, Any], repo_root: Path) -> Dict[str, Any]:
    """
    MVP: read the plan's OpenAPI (or latest if missing), parse /api/* paths,
    and return which resources would be scaffolded.
    """
    openapi_path = plan.get("openapi_path")
    if openapi_path:
        path = Path(openapi_path)
        if not path.is_absolute():
            path = (repo_root / openapi_path).resolve()
    else:
        path = _latest_openapi(repo_root)

    if not path or not path.exists():
        return {"status": "no_openapi_found", "resources": [], "openapi_path": None}

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    paths: Dict[str, Any] = data.get("paths") or {}

    resources: List[str] = []
    seen: Set[str] = set()
    for p in paths.keys():
        # expect patterns like /api/notes, /api/notes/{id}, /api/create, etc.
        if p.startswith("/api/"):
            parts = [seg for seg in p.split("/") if seg and not seg.startswith("{")]
            if len(parts) >= 2:
                res = parts[1]
                if res not in seen:
                    seen.add(res)
                    resources.append(res)

    # Future step: actually write route modules/templates.
    return {
        "status": "ok",
        "openapi_path": str(path),
        "resources": resources,
    }
