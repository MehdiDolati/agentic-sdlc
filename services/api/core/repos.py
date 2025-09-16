# services/api/repos.py
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    create_engine, MetaData, Table, Column, String, JSON, DateTime,
    select, insert, update as sa_update, delete as sa_delete, func, ForeignKey
)
from sqlalchemy.engine import Engine

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

    def list(self) -> list[dict]:
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(
                    _PLANS_TABLE.c.id,
                    _PLANS_TABLE.c.request,
                    _PLANS_TABLE.c.owner,
                    _PLANS_TABLE.c.artifacts,
                    _PLANS_TABLE.c.status,
                    _PLANS_TABLE.c.created_at,
                    _PLANS_TABLE.c.updated_at,
                )
                .order_by(_PLANS_TABLE.c.created_at.desc(), _PLANS_TABLE.c.id.asc())
            ).all()
        out = []
        for (rid, req, owner, arts, status, created_at, updated_at) in rows:
            out.append({
                "id": rid,
                "request": req,
                "owner": owner,
                "artifacts": arts or {},
                "status": status or "new",
                "created_at": created_at.isoformat() if created_at else None,
                "updated_at": updated_at.isoformat() if updated_at else None,
            })
        return out

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
                sa_update(_RUNS_TABLE)
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
                sa_update(_RUNS_TABLE)
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
                sa_update(_NOTES_TABLE)
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