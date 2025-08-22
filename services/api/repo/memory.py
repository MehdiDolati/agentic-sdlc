from typing import Dict, Any, List, Optional
from uuid import uuid4

class InMemoryNotesRepo:
    def __init__(self) -> None:
        self._db: Dict[str, Dict[str, Any]] = {}

    def list(self) -> List[Dict[str, Any]]:
        return list(self._db.values())

    def create(self, title: str, content: str) -> Dict[str, Any]:
        _id = str(uuid4())
        obj = {"id": _id, "title": title, "content": content}
        self._db[_id] = obj
        return obj

    def get(self, id: str) -> Optional[Dict[str, Any]]:
        return self._db.get(id)

    def update(self, id: str, title: str, content: str) -> Optional[Dict[str, Any]]:
        if id not in self._db:
            return None
        obj = {**self._db[id], "title": title, "content": content}
        self._db[id] = obj
        return obj

    def delete(self, id: str) -> bool:
        return self._db.pop(id, None) is not None
