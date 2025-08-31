# services/api/planner/prompt_templates.py
from pathlib import Path
from string import Template
from typing import Any, Mapping, List

# Directory that contains the .md templates
_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

def list_templates() -> List[str]:
    """Return available template filenames."""
    if not _TEMPLATES_DIR.exists():
        return []
    return sorted(p.name for p in _TEMPLATES_DIR.glob("*.md"))

def _stringify(value: Any) -> str:
    """Normalize values so lists render as newline-joined bullet lines, etc."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        # each item on its own line, prefixed with "- "
        return "\n".join(f"{x}" for x in value)
    return str(value)

def render_template(name: str, data: Mapping[str, Any]) -> str:
    """Load a template by name and render; raise if a key is missing."""
    path = _TEMPLATES_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")
    text = path.read_text(encoding="utf-8")
    normalized = {k: _stringify(v) for k, v in dict(data).items()}
    # IMPORTANT: .substitute (not .safe_substitute) so tests fail on missing keys
    return Template(text).substitute(**normalized)
