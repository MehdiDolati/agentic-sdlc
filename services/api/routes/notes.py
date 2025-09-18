# services/api/routes/notes.py  — drop-in replace

import os
from pathlib import Path
from typing import Dict, Optional, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# SQLAlchemy
from sqlalchemy import (
    MetaData, Table, Column, String, JSON, DateTime, func,
    insert, select, update as sa_update, delete as sa_delete, create_engine
)
from sqlalchemy.engine import Engine

# Reuse only repo root from shared
try:
    from services.api.core.shared import _repo_root as _repo_root
except Exception:
    from ..core.shared import _repo_root as _repo_root

# shared in-memory DB (works in tests and local runs)
try:
    from .state import DBS
except ImportError:
    from state import DBS


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


_DB: Dict[str, Any] = DBS.setdefault("notes", {})

# ---------- Notes DB (Postgres/SQLite via SQLAlchemy) ----------

_NOTES_METADATA = MetaData()

_NOTES_TABLE = Table(
    "notes",
    _NOTES_METADATA,
    Column("id", String, primary_key=True),
    Column("data", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)


def _database_url(repo_root: Path) -> str:
    """
    Prefer DATABASE_URL if set; otherwise use a local SQLite file under the repo root.
    Keep it simple and avoid additional helpers to prevent import churn.
    """
    env = os.getenv("DATABASE_URL")
    if env:
        return env
    db_path = (repo_root / "notes.db").resolve()
    return f"sqlite+pysqlite:///{db_path}"


def _create_engine(url: str) -> Engine:
    return create_engine(url, future=True, echo=False)


def ensure_notes_schema(engine: Engine) -> None:
    _NOTES_METADATA.create_all(engine)


class NotesRepoDB:
    def __init__(self, engine: Engine):
        self.engine = engine
        ensure_notes_schema(engine)

    def list(self) -> list[dict]:
        with self.engine.connect() as conn:
            rows = conn.execute(select(_NOTES_TABLE.c.id, _NOTES_TABLE.c.data)).all()
            return [{"id": rid, **(payload or {})} for rid, payload in rows]

    def create(self, payload: dict) -> dict:
        nid = uuid4().hex[:8]
        to_store = dict(payload or {})
        with self.engine.begin() as conn:
            conn.execute(insert(_NOTES_TABLE).values(id=nid, data=to_store))
        return {"id": nid, **to_store}

    def get(self, note_id: str) -> dict | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                select(_NOTES_TABLE.c.id, _NOTES_TABLE.c.data).where(_NOTES_TABLE.c.id == note_id)
            ).first()
            if not row:
                return None
            rid, payload = row
            return {"id": rid, **(payload or {})}

    def update(self, note_id: str, payload: dict) -> dict | None:
        to_store = dict(payload or {})
        with self.engine.begin() as conn:
            res = conn.execute(
                sa_update(_NOTES_TABLE)
                .where(_NOTES_TABLE.c.id == note_id)
                .values(data=to_store)
            )
            if res.rowcount == 0:
                return None
        return {"id": note_id, **to_store}

    def delete(self, note_id: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(sa_delete(_NOTES_TABLE).where(_NOTES_TABLE.c.id == note_id))


# Initialize repo at import (keeps previous behavior)
_DB_ENGINE = _create_engine(_database_url(_repo_root()))
_NOTES_REPO = NotesRepoDB(_DB_ENGINE)

# -------------------- Routes (router-based) --------------------

@router.get("")
def api_notes_list():
    return _NOTES_REPO.list()


@router.post("", status_code=201)
def api_notes_create(payload: Dict[str, Any]):
    return _NOTES_REPO.create(payload)


@router.get("/{note_id}")
def api_notes_get(note_id: str):
    doc = _NOTES_REPO.get(note_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Note not found")
    return doc


@router.put("/{note_id}")
def api_notes_put(note_id: str, payload: Dict[str, Any]):
    doc = _NOTES_REPO.update(note_id, payload)
    if not doc:
        raise HTTPException(status_code=404, detail="Note not found")
    return doc


@router.delete("/{note_id}", status_code=204)
def api_notes_delete(note_id: str):
    _NOTES_REPO.delete(note_id)
    return JSONResponse(status_code=204, content=None)


# Auto-mount on main app if present (preserves old @app.* behavior)
try:
    from services.api.app import app as _app  # type: ignore
    _app.include_router(router)
except Exception:
    pass
