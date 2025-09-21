from typing import Dict, List, Optional, Any
from uuid import uuid4

class InMemoryNotesRepo:
    def __init__(self) -> None:
        self._db: Dict[str, Dict[str, Any]] = {}

    def list(self, limit: int = 20, offset: int = 0, **filters):
        q      = (filters.get("q") or "").strip().lower()
        status = (filters.get("status") or "").strip()
        owner  = (filters.get("owner") or "").strip()
        sort   = (filters.get("sort") or "").strip()
        order  = (filters.get("order") or "desc").lower()

        items = list(self._plans)

        if q:
            def matches(p):
                return q in (p.get("request","") or "").lower() or q in (p.get("id","") or "").lower()
            items = [p for p in items if matches(p)]
        if status:
            items = [p for p in items if (p.get("last_run_status") or "") == status]
        if owner:
            items = [p for p in items if (p.get("owner") or "") == owner]

        key_map = {
            "created_at": lambda p: p.get("created_at"),
            "request": lambda p: p.get("request") or "",
            "owner": lambda p: p.get("owner") or "",
            "last_run_status": lambda p: p.get("last_run_status") or "",
            "last_run_at": lambda p: p.get("last_run_at"),
        }
        key_fn = key_map.get(sort, key_map["created_at"])
        reverse = (order != "asc")
        items.sort(key=key_fn, reverse=reverse)

        total = len(items)
        return items[offset:offset+limit], total


    def get(self, id: str) -> Optional[Dict[str, Any]]:
        return self._db.get(id)

    def create(self, item) -> Dict[str, Any]:
        data = item.model_dump() if hasattr(item, "model_dump") else dict(item)
        note = {"id": str(uuid4()), **data}
        self._db[note["id"]] = note
        return note
