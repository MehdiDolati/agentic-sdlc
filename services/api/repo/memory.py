from typing import Dict, List, Optional, Any
from uuid import uuid4

class InMemoryNotesRepo:
    def __init__(self) -> None:
        self._db: Dict[str, Dict[str, Any]] = {}

    def list(self) -> List[Dict[str, Any]]:
        return list(self._db.values())

    def get(self, id: str) -> Optional[Dict[str, Any]]:
        return self._db.get(id)

    def create(self, item) -> Dict[str, Any]:
        data = item.model_dump() if hasattr(item, "model_dump") else dict(item)
        note = {"id": str(uuid4()), **data}
        self._db[note["id"]] = note
        return note
