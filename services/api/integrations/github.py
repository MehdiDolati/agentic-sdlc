from __future__ import annotations
import base64
import json
from typing import Dict, Any, List, Tuple, Optional
import requests

class GH:
    def __init__(self, token: str, repo: str):
        if not token or not repo or "/" not in repo:
            raise ValueError("GitHub token/repo not configured")
        self.token = token
        self.repo = repo
        self.api = f"https://api.github.com/repos/{repo}"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }

    # --- Issues ---
    def create_issue(self, title: str, body: str = "", labels: Optional[List[str]] = None) -> Dict[str, Any]:
        payload = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        r = requests.post(f"{self.api}/issues", headers=self.headers, json=payload, timeout=30)
        r.raise_for_status()
        return r.json()

    # --- Branch ---
    def ensure_branch(self, base: str, new_branch: str) -> Dict[str, Any]:
        # get base sha
        r = requests.get(f"{self.api}/git/ref/heads/{base}", headers=self.headers, timeout=30)
        r.raise_for_status()
        base_sha = r.json()["object"]["sha"]
        # create ref
        payload = {"ref": f"refs/heads/{new_branch}", "sha": base_sha}
        r = requests.post(f"{self.api}/git/refs", headers=self.headers, json=payload, timeout=30)
        if r.status_code not in (200, 201):  # already exists?
            # if exists, GET ref to confirm
            r2 = requests.get(f"{self.api}/git/ref/heads/{new_branch}", headers=self.headers, timeout=30)
            r2.raise_for_status()
            return r2.json()
        return r.json()

    # --- Commit files (create a tree/commit/update ref) ---
    def upsert_files(self, branch: str, files: List[Tuple[str, str]], message: str) -> Dict[str, Any]:
        # 1) get latest commit sha on branch
        r = requests.get(f"{self.api}/git/ref/heads/{branch}", headers=self.headers, timeout=30)
        r.raise_for_status()
        latest_sha = r.json()["object"]["sha"]
        r = requests.get(f"{self.api}/git/commits/{latest_sha}", headers=self.headers, timeout=30)
        r.raise_for_status()
        base_tree = r.json()["tree"]["sha"]

        # 2) create blobs
        blobs = []
        for path, content in files:
            rb = requests.post(
                f"{self.api}/git/blobs",
                headers=self.headers,
                json={"content": content, "encoding": "utf-8"},
                timeout=30,
            )
            rb.raise_for_status()
            blobs.append((path, rb.json()["sha"]))

        # 3) create tree
        tree_entries = [{"path": p, "mode": "100644", "type": "blob", "sha": sha} for (p, sha) in blobs]
        rt = requests.post(
            f"{self.api}/git/trees",
            headers=self.headers,
            json={"base_tree": base_tree, "tree": tree_entries},
            timeout=30,
        )
        rt.raise_for_status()
        tree_sha = rt.json()["sha"]

        # 4) create commit
        rc = requests.post(
            f"{self.api}/git/commits",
            headers=self.headers,
            json={"message": message, "tree": tree_sha, "parents": [latest_sha]},
            timeout=30,
        )
        rc.raise_for_status()
        commit_sha = rc.json()["sha"]

        # 5) move ref
        ru = requests.patch(
            f"{self.api}/git/refs/heads/{branch}",
            headers=self.headers,
            json={"sha": commit_sha, "force": False},
            timeout=30,
        )
        ru.raise_for_status()
        return {"commit": commit_sha}

    # --- PR ---
    def open_pr(self, head: str, base: str, title: str, body: str = "") -> Dict[str, Any]:
        payload = {"title": title, "head": head, "base": base, "body": body}
        r = requests.post(f"{self.api}/pulls", headers=self.headers, json=payload, timeout=30)
        r.raise_for_status()
        return r.json()
