#!/usr/bin/env python3

import os
import sys
from pathlib import Path

# Add the project root to Python path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root / "services"))
sys.path.insert(0, str(repo_root))

print(f"Working directory: {os.getcwd()}")
print(f"Script location: {Path(__file__).parent}")

# Test if we can find the user stories
from services.api.core.shared import _repo_root
import glob

print(f"Repo root: {_repo_root()}")
stories_dir = _repo_root() / "docs" / "stories"
print(f"Stories dir exists: {stories_dir.exists()}")

if stories_dir.exists():
    pattern = str(stories_dir / "*proj-20251029141049-plan-05cd1d*")
    matching_files = glob.glob(pattern)
    print(f"Matching files: {matching_files}")
    
    if matching_files:
        import json
        latest_file = max(matching_files, key=os.path.getmtime)
        print(f"Latest file: {latest_file}")
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"User stories count: {len(data.get('user_stories', []))}")