
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel
from typing import Dict, List, Optional
from uuid import uuid4


router = APIRouter(prefix="/api/create", tags=["create"], )

class CreateIn(BaseModel):
    title: str = ""
    content: str = ""

class Create(CreateIn):
    id: str

_DB: Dict[str, Create] = {}

@router.get("", response_model=List[Create])
def list_create():
    return list(_DB.values())

@router.post("", status_code=status.HTTP_201_CREATED, response_model=Create)
def create_create(item: CreateIn):
    obj = Create(id=str(uuid4()), **item.model_dump())
    _DB[obj.id] = obj
    return obj

@router.get("/"+"<built-in function id>", response_model=Create)
def get_create(id: str):
    if id not in _DB:
        raise HTTPException(status_code=404, detail="create not found")
    return _DB[id]

@router.put("/"+"<built-in function id>", response_model=Create)
def update_create(id: str, item: CreateIn):
    if id not in _DB:
        raise HTTPException(status_code=404, detail="create not found")
    obj = _DB[id].model_copy(update=item.model_dump())
    _DB[id] = obj
    return obj

@router.delete("/"+"<built-in function id>", status_code=status.HTTP_204_NO_CONTENT)
def delete_create(id: str):
    if id not in _DB:
        raise HTTPException(status_code=404, detail="create not found")
    del _DB[id]
    return None
