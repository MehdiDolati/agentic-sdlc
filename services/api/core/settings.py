from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict

# Defaults live here. Keep keys stable; UI depends on them.
_DEFAULTS: Dict[str, Any] = {
    "planner_mode": "single",              # "single" | "multi"
    "default_provider": "none",            # "none" | "openai" | "anthropic" | "azure" | "local"
    "api_base_url": "",                    # optional override
    "auth_enabled": False,                 # toggle auth (simple gate used elsewhere)
    "multi_agent_enabled": False,          # feature toggle for multi-agent UI/paths
    "github_token": "",                    # Personal access token (classic or fine-grained)
    "github_repo": "",                     # "owner/repo"
    "github_default_branch": "main",       # default base branch
}

def _settings_path(state_dir: Path) -> Path:
    return state_dir / "settings.json"

def load_settings(state_dir: Path) -> Dict[str, Any]:
    p = _settings_path(state_dir)
    if not p.exists():
        return _DEFAULTS.copy()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        # merge unknown keys conservatively
        out = _DEFAULTS.copy()
        out.update({k: v for k, v in (data or {}).items() if k in _DEFAULTS})
        return out
    except Exception:
        # corrupted file → return defaults (fail-safe)
        return _DEFAULTS.copy()

def save_settings(state_dir: Path, cfg: Dict[str, Any]) -> Dict[str, Any]:
    # write atomically
    p = _settings_path(state_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    # only persist known keys
    payload = _DEFAULTS.copy()
    payload.update({k: v for k, v in (cfg or {}).items() if k in _DEFAULTS})
    p.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload

def update_settings(state_dir: Path, partial: Dict[str, Any]) -> Dict[str, Any]:
    current = load_settings(state_dir)
    current.update({k: v for k, v in (partial or {}).items() if k in _DEFAULTS})
    return save_settings(state_dir, current)
