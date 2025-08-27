from pathlib import Path

import pytest

from planner.prompt_templates import render_template, list_templates

FIX_DIR = Path(__file__).resolve().parent / "fixtures" / "planner"

def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8").strip()

def test_templates_discoverable():
    files = list_templates()
    assert "system.md" in files
    assert "task_breakdown.md" in files
    assert "prd.md" in files

def test_system_template_matches_golden():
    rendered = render_template("system.md", {
        "project_name": "Agentic SDLC",
        "goal": "Generate autonomous planning tasks",
    }).strip()
    expected = read_text(FIX_DIR / "system.golden")
    assert rendered == expected

def test_task_breakdown_template_matches_golden():
    rendered = render_template("task_breakdown.md", {
        "goal": "Generate autonomous planning tasks",
        "context": "This repository automates SDLC activities.",
        "nfrs": ["Deterministic", "Observable"],
    }).strip()
    expected = read_text(FIX_DIR / "task_breakdown.golden")
    assert rendered == expected

def test_prd_template_matches_golden():
    rendered = render_template("prd.md", {
        "vision": "Enable a minimal, auditable, autonomous SDLC loop",
        "users": ["Platform engineer", "Project lead"],
        "scenarios": ["Auto create branches and PRs", "Enforce tests and checks"],
        "metrics": ["PR cycle time", "% automated merges"],
    }).strip()
    expected = read_text(FIX_DIR / "prd.golden")
    assert rendered == expected

@pytest.mark.parametrize("missing_key", ["goal","project_name"])
def test_missing_context_keys_fail_fast(missing_key):
    ctx = {"goal": "X", "project_name": "Y"}
    ctx.pop(missing_key)
    with pytest.raises(Exception):
        render_template("system.md", ctx)
