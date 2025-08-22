
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel
from typing import Dict, List, Optional
from uuid import uuid4


from typing import Optional
from fastapi import Header, HTTPException
def require_auth(authorization: Optional[str] = Header(None)):
    if authorization is None or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    return True

router = APIRouter(prefix="/api/notes", tags=["notes"], dependencies=[Depends(require_auth)], )

class NoteIn(BaseModel):
    title: str = ""
    content: str = ""

class Note(NoteIn):
    id: str

_DB: Dict[str, Note] = {}

@router.get("", response_model=List[Note])
def list_notes():
    return list(_DB.values())

@router.post("", status_code=status.HTTP_201_CREATED, response_model=Note)
def create_note(item: NoteIn):
    obj = Note(id=str(uuid4()), **item.model_dump())
    _DB[obj.id] = obj
    return obj

@router.get("/"+"<built-in function id>", response_model=Note)
def get_note(id: str):
    if id not in _DB:
        raise HTTPException(status_code=404, detail="note not found")
    return _DB[id]

@router.put("/"+"<built-in function id>", response_model=Note)
def update_note(id: str, item: NoteIn):
    if id not in _DB:
        raise HTTPException(status_code=404, detail="note not found")
    obj = _DB[id].model_copy(update=item.model_dump())
    _DB[id] = obj
    return obj

@router.delete("/"+"<built-in function id>", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(id: str):
    if id not in _DB:
        raise HTTPException(status_code=404, detail="note not found")
    del _DB[id]
    return None
