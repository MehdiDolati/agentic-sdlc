# services/api/orchestrator/runner.py
from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass, field
from difflib import unified_diff
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


@dataclass
class StepResult:
    type: str
    ok: bool
    changed: bool
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


def _ensure_parent(path: Path, dry_run: bool) -> None:
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)


def _read_text_if_exists(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _unified(a: str, b: str, path: str) -> str:
    diff = unified_diff(
        a.splitlines(True),
        b.splitlines(True),
        fromfile=f"{path} (before)",
        tofile=f"{path} (after)",
        lineterm=""
    )
    return "".join(diff)


def step_write_file(step: Dict[str, Any], *, cwd: Path, dry_run: bool) -> StepResult:
    """
    step = {
        "type": "write_file",
        "path": "docs/example.txt",
        "content": "hello",
        # optional
        "overwrite": True|False (default True)
    }
    """
    path = cwd / step["path"]
    content = step.get("content", "")
    overwrite = step.get("overwrite", True)

    before = _read_text_if_exists(path)
    exists = path.exists()
    if exists and not overwrite and before != content:
        return StepResult(
            type="write_file",
            ok=False,
            changed=False,
            stderr="File exists and overwrite=False.",
            details={"path": str(path), "exists": True},
        )

    changed = (before != content)
    result = StepResult(
        type="write_file",
        ok=True,
        changed=changed,
        details={
            "path": str(path),
            "bytes": len(content.encode("utf-8")),
            "preview_diff": _unified(before, content, str(path)) if changed else "",
            "exists_before": exists,
        },
    )

    if not dry_run and changed:
        _ensure_parent(path, dry_run)
        path.write_text(content, encoding="utf-8")

    return result


def step_patch_file(step: Dict[str, Any], *, cwd: Path, dry_run: bool) -> StepResult:
    """
    Simple find/replace patcher.

    step = {
        "type": "patch_file",
        "path": "services/api/app.py",
        "find": "old text",
        "replace": "new text",
        # optional
        "count": 0  # 0 = replace all (default), otherwise max number of replacements
    }
    """
    path = cwd / step["path"]
    find = step.get("find")
    replace = step.get("replace", "")
    count = int(step.get("count", 0))

    if find is None:
        return StepResult(
            type="patch_file",
            ok=False,
            changed=False,
            stderr="Missing 'find' value.",
            details={"path": str(path)},
        )

    before = _read_text_if_exists(path)
    if before == "" and not path.exists():
        return StepResult(
            type="patch_file",
            ok=False,
            changed=False,
            stderr="File not found.",
            details={"path": str(path)},
        )

    if count and count > 0:
        after = before.replace(find, replace, count)
    else:
        after = before.replace(find, replace)

    changed = (after != before)
    result = StepResult(
        type="patch_file",
        ok=True,
        changed=changed,
        details={
            "path": str(path),
            "replacements": (0 if not changed else (before.count(find) if count == 0 else min(before.count(find), count))),
            "preview_diff": _unified(before, after, str(path)) if changed else "",
        },
    )

    if not dry_run and changed:
        path.write_text(after, encoding="utf-8")

    return result


def step_run_cmd(step: Dict[str, Any], *, cwd: Path, dry_run: bool) -> StepResult:
    """
    step = {
        "type": "run_cmd",
        "cmd": "pytest -q",
        # optional
        "shell": False,  # default False; if True runs via shell
        "env": {"FOO": "1"},
        "timeout": 600
    }
    """
    raw = step["cmd"]
    shell = bool(step.get("shell", False))
    env_extra = step.get("env") or {}
    timeout = int(step.get("timeout", 600))

    if dry_run:
        # do not execute, just report
        return StepResult(
            type="run_cmd",
            ok=True,
            changed=False,
            exit_code=None,
            stdout="",
            stderr="",
            details={"planned_cmd": raw, "shell": shell, "cwd": str(cwd), "timeout": timeout, "env": env_extra},
        )

    env = os.environ.copy()
    env.update({str(k): str(v) for k, v in env_extra.items()})

    if shell:
        cmd = raw
    else:
        # split for exec form
        cmd = shlex.split(raw)

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            shell=shell,
            timeout=timeout,
        )
        return StepResult(
            type="run_cmd",
            ok=(proc.returncode == 0),
            changed=True,  # running a command is a side effect
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            details={"cmd": raw, "shell": shell},
        )
    except subprocess.TimeoutExpired as ex:
        return StepResult(
            type="run_cmd",
            ok=False,
            changed=False,
            exit_code=None,
            stdout=ex.stdout or "",
            stderr=(ex.stderr or "") + f"\n[timeout after {timeout}s]",
            details={"cmd": raw, "shell": shell},
        )


def run_steps(steps: Iterable[Dict[str, Any]], *, cwd: str | Path = ".", dry_run: bool = False) -> List[StepResult]:
    """
    Execute a sequence of steps. Stops on hard failure for file ops; continues for run_cmd.
    Returns list of StepResult.
    """
    root = Path(cwd)
    results: List[StepResult] = []

    for step in steps:
        t = step.get("type")
        if t == "write_file":
            res = step_write_file(step, cwd=root, dry_run=dry_run)
            results.append(res)
            if not res.ok:
                break
        elif t == "patch_file":
            res = step_patch_file(step, cwd=root, dry_run=dry_run)
            results.append(res)
            if not res.ok:
                break
        elif t == "run_cmd":
            res = step_run_cmd(step, cwd=root, dry_run=dry_run)
            results.append(res)
        else:
            results.append(StepResult(type=str(t), ok=False, changed=False, stderr="Unknown step type."))

    return results
