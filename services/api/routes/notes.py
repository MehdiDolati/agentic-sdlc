from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
# repo factory import – support package, absolute, and top-level
try:
    from ..repo.factory import notes_repo            # package context
except Exception:
    try:
        from services.api.repo.factory import notes_repo  # absolute package
    except Exception:
        from repo.factory import notes_repo          # top-level (pytest from root)

def require_auth(authorization: Optional[str] = Header(None)):
    if authorization is None or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    return True

router = APIRouter(prefix="/api/notes", tags=["notes"], dependencies=[Depends(require_auth)])

class NotesIn(BaseModel):
    title: str = ""
    content: str = ""

class Notes(NotesIn):
    id: str

_repo = notes_repo()

@router.get("", response_model=List[Notes])
def list_notes():
    return _repo.list()

@router.post("", status_code=status.HTTP_201_CREATED, response_model=Notes)
def create_note(item: NotesIn):
    return _repo.create(item.title, item.content)

@router.get("/{id}", response_model=Notes)
def get_note(id: str):
    found = _repo.get(id)
    if not found:
        raise HTTPException(status_code=404, detail="note not found")
    return found

@router.put("/{id}", response_model=Notes)
def update_note(id: str, item: NotesIn):
    updated = _repo.update(id, item.title, item.content)
    if not updated:
        raise HTTPException(status_code=404, detail="note not found")
    return updated

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(id: str):
    ok = _repo.delete(id)
    if not ok:
        raise HTTPException(status_code=404, detail="note not found")
    return None
