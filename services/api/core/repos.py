# services/api/repos.py
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    create_engine, MetaData, Table, Column, String, JSON, DateTime,
    select, insert, update, delete as sa_delete, func, ForeignKey, text, inspect
)
from sqlalchemy.engine import Engine
# shared in-memory DB (works in tests and local runs)
from services.api.state import DBS
    
# Use one metadata object for all tables
_PLANS_METADATA = MetaData()
_PLANS_TABLE = Table(
    "plans",
    _PLANS_METADATA,
    Column("id", String, primary_key=True),
    Column("request", String, nullable=False),
    Column("owner", String, nullable=False),
    Column("artifacts", JSON, nullable=False),
    Column("status", String, nullable=False, server_default="new"),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
)

_RUNS_METADATA = MetaData()
_RUNS_TABLE = Table(
    "runs",
    _RUNS_METADATA,
    Column("id", String, primary_key=True),              # run_id
    Column("plan_id", String, nullable=False),
    Column("status", String, nullable=False, server_default="queued"),
    Column("manifest_path", String, nullable=True),
    Column("log_path", String, nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column("started_at", DateTime(timezone=True), nullable=True),
    Column("completed_at", DateTime(timezone=True), nullable=True),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
)

_NOTES_METADATA = MetaData()

_NOTES_TABLE = Table(
    "notes",
    _NOTES_METADATA,
    Column("id", String, primary_key=True),
    Column("data", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

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

def ensure_notes_schema(engine: Engine) -> None:
    """Create the notes schema (idempotent) using our local SQLAlchemy metadata."""
    _NOTES_METADATA.create_all(engine)

def ensure_plans_schema(engine: Engine) -> None:
    _PLANS_METADATA.create_all(engine)

def ensure_runs_schema(engine: Engine) -> None:
    _RUNS_METADATA.create_all(engine)
    
class PlansRepoDB:
    def __init__(self, engine: Engine):
        self.engine = engine
        ensure_plans_schema(engine)

    def create(self, entry: dict) -> dict:
        with self.engine.begin() as conn:
            conn.execute(insert(_PLANS_TABLE).values(**entry))
        return entry

    def get(self, plan_id: str) -> dict | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                select(
                    _PLANS_TABLE.c.id,
                    _PLANS_TABLE.c.request,
                    _PLANS_TABLE.c.owner,
                    _PLANS_TABLE.c.artifacts,
                    _PLANS_TABLE.c.status,
                    _PLANS_TABLE.c.created_at,
                    _PLANS_TABLE.c.updated_at,
                ).where(_PLANS_TABLE.c.id == plan_id)
            ).first()
        if not row:
            return None
        rid, req, owner, arts, status, created_at, updated_at = row
        return {
            "id": rid,
            "request": req,
            "owner": owner,
            "artifacts": arts or {},
            "status": status or "new",
            "created_at": created_at.isoformat() if created_at else None,
            "updated_at": updated_at.isoformat() if updated_at else None,
        }

    def list(self, limit: int = 20, offset: int = 0, **filters):
        q      = (filters.get("q") or "").strip()
        status = (filters.get("status") or "").strip()
        owner  = (filters.get("owner") or "").strip()
        sort   = (filters.get("sort") or "").strip()
        order  = (filters.get("order") or "desc").lower()
    
        # Column detection guard (safe if plans table isn’t there yet)
        try:
            cols = {c["name"] for c in inspect(self.engine).get_columns("plans")}
        except Exception:
            cols = set()
    
        has = cols.__contains__
        allowed_sort = {c for c in (
            "created_at", "request", "owner", "last_run_status", "last_run_at", "id"
        ) if has(c)}
        sort_col = sort if sort in allowed_sort else ("created_at" if has("created_at") else "id")
        dir_sql = "ASC" if order == "asc" else "DESC"
    
        where = ["1=1"]
        params = {"limit": limit, "offset": offset}
        if q:
            qv = f"%{q.lower()}%"
            if has("request") and has("id"):
                where.append("(LOWER(request) LIKE :q OR LOWER(id) LIKE :q)")
                params["q"] = qv
            elif has("request"):
                where.append("LOWER(request) LIKE :q")
                params["q"] = qv
            elif has("id"):
                where.append("LOWER(id) LIKE :q")
                params["q"] = qv
        if status and has("last_run_status"):
            where.append("last_run_status = :status")
            params["status"] = status
        if owner and has("owner"):
            where.append("owner = :owner")
            params["owner"] = owner
    
        where_sql = " AND ".join(where)
        sql_list = f"""
            SELECT *
            FROM plans
            WHERE {where_sql}
            ORDER BY {sort_col} {dir_sql}
            LIMIT :limit OFFSET :offset
        """
        sql_count = f"SELECT COUNT(*) AS c FROM plans WHERE {where_sql}"
    
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(text(sql_list), params).mappings().all()
                total_row = conn.execute(text(sql_count), params).one()
                return rows, total_row.c
        except (OperationalError, ProgrammingError, SQLAlchemyError):
            # During early tests the table/columns may not exist; return empty set.
            return [], 0
 
    def update(self, plan_id: str, fields: dict) -> dict | None:
        if not fields:
            return self.get(plan_id)
        allowed = {"request", "owner", "artifacts", "status"}
        payload = {k: v for k, v in fields.items() if k in allowed}
        if not payload:
            return self.get(plan_id)
        with self.engine.begin() as conn:
            res = conn.execute(
                update(_PLANS_TABLE)
                .where(_PLANS_TABLE.c.id == plan_id)
                .values(**payload)
            )
            # res.rowcount might be 0 if not found
        return self.get(plan_id)

    def update_artifacts(self, plan_id: str, artifacts: dict, merge: bool = True) -> dict | None:
        if merge:
            current = self.get(plan_id)
            if not current:
                return None
            merged = (current.get("artifacts") or {}).copy()
            merged.update(artifacts or {})
            return self.update(plan_id, {"artifacts": merged})
        else:
            return self.update(plan_id, {"artifacts": artifacts or {}})        

class RunsRepoDB:
    def __init__(self, engine: Engine):
        self.engine = engine
        ensure_runs_schema(engine)

    def create(self, run_id: str, plan_id: str) -> dict:
        with self.engine.begin() as conn:
            conn.execute(
                insert(_RUNS_TABLE).values(id=run_id, plan_id=plan_id, status="queued")
            )
        return {"id": run_id, "plan_id": plan_id, "status": "queued"}

    def set_running(self, run_id: str, manifest_path: str, log_path: str):
        with self.engine.begin() as conn:
            conn.execute(
                update(_RUNS_TABLE)
                .where(_RUNS_TABLE.c.id == run_id)
                .where(_RUNS_TABLE.c.status != "cancelled")  # don't resurrect cancelled runs
                .values(
                    status="running",
                    manifest_path=manifest_path,
                    log_path=log_path,
                    started_at=func.now(),
                )
            )

    def set_completed(self, run_id: str, status: str):
        with self.engine.begin() as conn:
            conn.execute(
                update(_RUNS_TABLE)
                .where(_RUNS_TABLE.c.id == run_id)
                .values(status=status, completed_at=func.now())
            )

    def get(self, run_id: str) -> dict | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                select(
                    _RUNS_TABLE.c.id,
                    _RUNS_TABLE.c.plan_id,
                    _RUNS_TABLE.c.status,
                    _RUNS_TABLE.c.manifest_path,
                    _RUNS_TABLE.c.log_path,
                    _RUNS_TABLE.c.created_at,
                    _RUNS_TABLE.c.started_at,
                    _RUNS_TABLE.c.completed_at,
                    _RUNS_TABLE.c.updated_at,
                ).where(_RUNS_TABLE.c.id == run_id)
            ).first()
        if not row:
            return None
        rid, pid, st, man, log, c, s, e, u = row
        return {
            "id": rid, "plan_id": pid, "status": st,
            "manifest_path": man, "log_path": log,
            "created_at": c.isoformat() if c else None,
            "started_at": s.isoformat() if s else None,
            "completed_at": e.isoformat() if e else None,
            "updated_at": u.isoformat() if u else None,
        }

    def list_for_plan(self, plan_id: str) -> list[dict]:
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(
                    _RUNS_TABLE.c.id,
                    _RUNS_TABLE.c.status,
                    _RUNS_TABLE.c.manifest_path,
                    _RUNS_TABLE.c.log_path,
                    _RUNS_TABLE.c.created_at,
                    _RUNS_TABLE.c.started_at,
                    _RUNS_TABLE.c.completed_at,
                )
                .where(_RUNS_TABLE.c.plan_id == plan_id)
                .order_by(_RUNS_TABLE.c.created_at.desc(), _RUNS_TABLE.c.id.asc())
            ).all()
        out = []
        for rid, st, man, log, c, s, e in rows:
            out.append({
                "id": rid, "status": st,
                "manifest_path": man, "log_path": log,
                "created_at": c.isoformat() if c else None,
                "started_at": s.isoformat() if s else None,
                "completed_at": e.isoformat() if e else None,
            })
        return out

class NotesRepoDB:
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

    def update_artifacts(self, plan_id: str, artifacts: dict):
        """Minimal partial update for the artifacts JSON field."""
        with self.engine.begin() as conn:
            conn.execute(
                plans_table.update()
                .where(plans_table.c.id == plan_id)
                .values(artifacts=artifacts)
            )
            return self.get(plan_id)        

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
                update(_NOTES_TABLE)
                .where(_NOTES_TABLE.c.id == note_id)
                .values(data=to_store)
                .returning(_NOTES_TABLE.c.id, _NOTES_TABLE.c.data)
            ).first()
        if not res:
            return None
        rid, data = res
        return {"id": rid, **(data or {})}

    def delete(self, note_id: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(sa_delete(_NOTES_TABLE).where(_NOTES_TABLE.c.id == note_id))

def list(self, q=None, sort=None, order=None, limit=20, offset=0, status=None, owner=None):
    sql = "SELECT * FROM plans WHERE 1=1"
    params = {}

    if q:
        sql += " AND (request ILIKE %(q)s OR id ILIKE %(q)s)"
        params["q"] = f"%{q}%"

    if status:
        sql += " AND last_run_status = %(status)s"
        params["status"] = status

    if owner:
        sql += " AND owner = %(owner)s"
        params["owner"] = owner

    # sorting
    allowed = {"created_at", "request", "owner", "last_run_status", "last_run_at"}
    if sort in allowed:
        dir = "ASC" if (order or "").lower() == "asc" else "DESC"
        sql += f" ORDER BY {sort} {dir}"
    else:
        sql += " ORDER BY created_at DESC"

    sql += " LIMIT %(limit)s OFFSET %(offset)s"
    params["limit"] = limit
    params["offset"] = offset

    # run + fetch total separately or via window func, depending on your current impl            