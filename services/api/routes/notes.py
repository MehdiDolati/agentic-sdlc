from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel
from typing import Optional, List

try:
    from ..repo.factory import notes_repo
except ModuleNotFoundError:
    from services.api.repo.factory import notes_repo

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

@router.get("", response_model=List[Notes])
def list_notes():
    return notes_repo.list()

@router.post("", status_code=status.HTTP_201_CREATED, response_model=Notes)
def create_note(item: NotesIn):
    return notes_repo.create(item)

@router.get("/{id}", response_model=Notes)
def get_note(id: str):
    n = notes_repo.get(id)
    if not n:
        raise HTTPException(status_code=404, detail="note not found")
    return n
