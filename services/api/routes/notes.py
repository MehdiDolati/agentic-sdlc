# services/api/routes/notes.py
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel
from typing import Dict, List, Optional
from uuid import uuid4

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

_DB: Dict[str, Notes] = {}

@router.get("", response_model=List[Notes])
def list_notes():
    return list(_DB.values())

@router.post("", status_code=status.HTTP_201_CREATED, response_model=Notes)
def create_note(item: NotesIn):
    obj = Notes(id=str(uuid4()), **item.model_dump())
    _DB[obj.id] = obj
    return obj

@router.get("/{id}", response_model=Notes)
def get_note(id: str):
    if id not in _DB:
        raise HTTPException(status_code=404, detail="note not found")
    return _DB[id]

@router.put("/{id}", response_model=Notes)
def update_note(id: str, item: NotesIn):
    if id not in _DB:
        raise HTTPException(status_code=404, detail="note not found")
    obj = _DB[id].model_copy(update=item.model_dump())
    _DB[id] = obj
    return obj

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(id: str):
    if id not in _DB:
        raise HTTPException(status_code=404, detail="note not found")
    del _DB[id]
    return None
