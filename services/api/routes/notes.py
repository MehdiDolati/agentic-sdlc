from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from uuid import uuid4

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

# A single metadata object for our schema
_NOTES_METADATA = MetaData()

# Table: notes
_NOTES_TABLE = Table(
    "notes",
    _NOTES_METADATA,
    Column("id", String, primary_key=True),          # short hex id
    Column("data", JSON, nullable=False),            # the payload you POST/PUT (e.g., {"text": "...", ...})
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

def _database_url(repo_root: Path) -> str:
    """
    DATABASE_URL if set, otherwise a local SQLite DB under ./docs/notes.db
    Examples:
      - postgresql+psycopg://user:pass@localhost:5432/notesdb
      - sqlite+pysqlite:///C:/path/to/notes.db  (Windows)
      - sqlite+pysqlite:////home/runner/work/.../notes.db  (Linux)
    """
    env = os.getenv("DATABASE_URL")
    if env:
        return env
    # default to a file-backed SQLite DB under docs for dev/test
    return f"sqlite+pysqlite:///{(_docs_root(_repo_root()) / 'notes.db').resolve()}"

def _create_engine(url: str) -> Engine:
    # echo=False keeps logs quiet; switch to True to debug SQL in dev
    return create_engine(url, future=True, echo=False)

def ensure_notes_schema(engine: Engine) -> None:
    """
    Lightweight migration: create tables if they don't exist.
    Works for SQLite and Postgres (JSONB is handled by SQLAlchemy).
    """
    _NOTES_METADATA.create_all(engine)

class NotesRepoDB:
    """A tiny repository that stores the entire note payload as JSON under 'data'."""
    def __init__(self, engine: Engine):
        self.engine = engine
        ensure_notes_schema(engine)

    def list(self) -> list[dict]:
        with self.engine.connect() as conn:
            rows = conn.execute(select(_NOTES_TABLE.c.id, _NOTES_TABLE.c.data)).all()
            return [{"id": rid, **(payload or {})} for rid, payload in rows]

    def create(self, payload: dict) -> dict:
        nid = uuid.uuid4().hex[:8]
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

# Initialize the repo (Postgres if DATABASE_URL is set; otherwise local SQLite)
_DB_ENGINE = _create_engine(_database_url(_repo_root()))
_NOTES_REPO = NotesRepoDB(_DB_ENGINE)

# ----------------------------------------------------------------

# ----- Notes (DB-backed) ------------------------------------------------------

@app.get("/api/notes")
def api_notes_list():
    return _NOTES_REPO.list()

@app.post("/api/notes", status_code=201)
def api_notes_create(payload: Dict[str, Any]):
    return _NOTES_REPO.create(payload)

@app.get("/api/notes/{note_id}")
def api_notes_get(note_id: str):
    doc = _NOTES_REPO.get(note_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Note not found")
    return doc

@app.put("/api/notes/{note_id}")
def api_notes_put(note_id: str, payload: Dict[str, Any]):
    doc = _NOTES_REPO.update(note_id, payload)
    if not doc:
        raise HTTPException(status_code=404, detail="Note not found")
    return doc

@app.delete("/api/notes/{note_id}", status_code=204)
def api_notes_delete(note_id: str):
    _NOTES_REPO.delete(note_id)
    return JSONResponse(status_code=204, content=None)

# -----------------------------------------------------------------------------
