#!/usr/bin/env python
import argparse
import os
import sys
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    import yaml
except Exception as e:
    print("PyYAML not installed. Run: pip install -r tools/requirements.txt", file=sys.stderr)
    raise

def load_team_profile(root: Path) -> float:
    cfg = root / "configs" / "TEAM_PROFILE.yaml"
    if not cfg.exists():
        return 0.8
    data = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
    return float((data.get("policies") or {}).get("coverage_gate", 0.8))

def parse_coverage_xml(xml_path: Path) -> float:
    tree = ET.parse(str(xml_path))
    root = tree.getroot()
    rate = root.attrib.get("line-rate")
    if rate is None:
        lines_valid = int(root.attrib.get("lines-valid", "0"))
        lines_covered = int(root.attrib.get("lines-covered", "0"))
        return (lines_covered / lines_valid) if lines_valid else 0.0
    return float(rate)

def ensure_coverage_xml(repo_root: Path, xml_out: Path) -> None:
    if xml_out.exists():
        return
    cmd = "coverage run -m pytest -q"
    subprocess.check_call(cmd, shell=True, cwd=str(repo_root / "services" / "api"))
    xml_out.parent.mkdir(parents=True, exist_ok=True)
    cmd_xml = f"coverage xml -o {xml_out}"
    subprocess.check_call(cmd_xml, shell=True, cwd=str(repo_root / "services" / "api"))

def main():
    ap = argparse.ArgumentParser(description="QA Agent: enforce coverage gate from TEAM_PROFILE.yaml")
    ap.add_argument("--threshold", type=float, help="Override coverage threshold (0..1)")
    ap.add_argument("--xml", type=str, help="Path to existing coverage.xml (optional)")
    ap.add_argument("--strict", action="store_true", help="Exit non-zero if below threshold")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    gate = args.threshold if args.threshold is not None else load_team_profile(repo_root)
    xml_path = Path(args.xml) if args.xml else (repo_root / "reports" / "coverage.xml")

    ensure_coverage_xml(repo_root, xml_path)
    cov = parse_coverage_xml(xml_path)

    ok = cov >= gate
    print({"coverage": cov, "gate": gate, "pass": ok, "xml": str(xml_path)})
    if args.strict and not ok:
        sys.exit(1)

if __name__ == "__main__":
    main()
