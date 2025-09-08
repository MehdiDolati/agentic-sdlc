from __future__ import annotations
import json, os, time, uuid, threading
from pathlib import Path
from typing import Any, Dict, Optional

_LOCK = threading.Lock()

def _now() -> int:
    return int(time.time())

def _default_db() -> Dict[str, Any]:
    return {"version": 1, "users": []}

class FileUserStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._save(_default_db())

    def _load(self) -> Dict[str, Any]:
        with _LOCK:
            if not self.path.exists():
                return _default_db()
            txt = self.path.read_text(encoding="utf-8")
            return json.loads(txt) if txt.strip() else _default_db()

    def _save(self, db: Dict[str, Any]) -> None:
        with _LOCK:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(db, indent=2), encoding="utf-8")
            os.replace(tmp, self.path)

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        db = self._load()
        for u in db["users"]:
            if u["email"].lower() == email.lower():
                return u
        return None

    def get_by_id(self, uid: str) -> Optional[Dict[str, Any]]:
        db = self._load()
        for u in db["users"]:
            if u["id"] == uid:
                return u
        return None

    def create(self, email: str, password_hash: str) -> Dict[str, Any]:
        if self.get_by_email(email):
            raise ValueError("email-already-exists")
        user = {
            "id": f"u_{uuid.uuid4().hex[:12]}",
            "email": email,
            "password_hash": password_hash,
            "created_at": _now(),
        }
        db = self._load()
        db["users"].append(user)
        self._save(db)
        return user
