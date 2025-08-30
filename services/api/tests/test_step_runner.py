# services/api/tests/test_step_runner.py
from pathlib import Path
from services.api.orchestrator.runner import run_steps, step_write_file, step_patch_file, step_run_cmd

def test_write_file_and_patch(tmp_path: Path):
    steps = [
        {"type": "write_file", "path": "a.txt", "content": "hello\n"},
        {"type": "patch_file", "path": "a.txt", "find": "hello", "replace": "hi"},
    ]
    res = run_steps(steps, cwd=tmp_path, dry_run=False)
    assert all(r.ok for r in res)
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "hi\n"

def test_dry_run_no_side_effects(tmp_path: Path):
    steps = [
        {"type": "write_file", "path": "b.txt", "content": "x"},
        {"type": "run_cmd", "cmd": "echo hi"},
    ]
    res = run_steps(steps, cwd=tmp_path, dry_run=True)
    assert all(r.ok for r in res)
    assert not (tmp_path / "b.txt").exists()  # dry-run should not write

def test_run_cmd_captures_output(tmp_path: Path):
    steps = [{"type": "run_cmd", "cmd": "python -c \"print('ok')\""}]
    res = run_steps(steps, cwd=tmp_path, dry_run=False)
    assert res[0].ok
    assert "ok" in res[0].stdout

def test_patch_missing_file(tmp_path: Path):
    res = step_patch_file({"type":"patch_file","path":"missing.txt","find":"a","replace":"b"}, cwd=tmp_path, dry_run=False)
    assert not res.ok
    assert "not found" in res.stderr.lower()
