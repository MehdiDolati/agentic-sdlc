# services/api/repos.py
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    create_engine, MetaData, Table, Column, String, JSON, DateTime, Boolean,
    select, insert, update, delete as sa_delete, func, ForeignKey, 
    text, inspect, cast, asc, desc, and_, or_, true as sql_true
    
)
from sqlalchemy.exc import OperationalError, ProgrammingError, SQLAlchemyError
from sqlalchemy.engine import Engine
# shared in-memory DB (works in tests and local runs)
from services.api.state import DBS
import uuid
    
# Use one metadata object for all tables
_PROJECTS_METADATA = MetaData()
_PROJECTS_TABLE = Table(
    "projects",
    _PROJECTS_METADATA,
    Column("id", String, primary_key=True),
    Column("title", String, nullable=False),
    Column("description", String, nullable=True),
    Column("owner", String, nullable=False),
    Column("status", String, nullable=False, server_default="new"),
    Column("created_at", DateTime(timezone=True), server_default=text('CURRENT_TIMESTAMP')),
    Column("updated_at", DateTime(timezone=True), server_default=text('CURRENT_TIMESTAMP'), onupdate=text('CURRENT_TIMESTAMP')),
)

_PLANS_METADATA = MetaData()
_PLANS_TABLE = Table(
    "plans",
    _PLANS_METADATA,
    Column("id", String, primary_key=True),
    Column("project_id", String, nullable=False),
    Column("request", String, nullable=False),
    Column("owner", String, nullable=False),
    Column("artifacts", JSON, nullable=False),
    Column("status", String, nullable=False, server_default="new"),
    Column("created_at", DateTime(timezone=True), server_default=text('CURRENT_TIMESTAMP')),
    Column("updated_at", DateTime(timezone=True), server_default=text('CURRENT_TIMESTAMP'), onupdate=text('CURRENT_TIMESTAMP')),
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
    Column("created_at", DateTime(timezone=True), server_default=text('CURRENT_TIMESTAMP')),
    Column("started_at", DateTime(timezone=True), nullable=True),
    Column("completed_at", DateTime(timezone=True), nullable=True),
    Column("updated_at", DateTime(timezone=True), server_default=text('CURRENT_TIMESTAMP'), onupdate=text('CURRENT_TIMESTAMP')),
)

_NOTES_METADATA = MetaData()

_NOTES_TABLE = Table(
    "notes",
    _NOTES_METADATA,
    Column("id", String, primary_key=True),
    Column("data", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=text('CURRENT_TIMESTAMP')),
)


# --- Interaction History Table ---
_HISTORY_METADATA = MetaData()
_HISTORY_TABLE = Table(
    "interaction_history",
    _HISTORY_METADATA,
    Column("id", String, primary_key=True),
    Column("project_id", String, nullable=True),
    Column("prompt", String, nullable=False),
    Column("response", String, nullable=False),
    Column("role", String, nullable=True),  # e.g., 'user', 'assistant'
    Column("metadata", JSON, nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=text('CURRENT_TIMESTAMP')),
)

# Add these table definitions after the existing tables

# --- Repositories Table ---
# ... after your existing table definitions, add the new tables with Boolean fix:

# --- Repositories Table ---
_REPOSITORIES_METADATA = MetaData()
_REPOSITORIES_TABLE = Table(
    "repositories",
    _REPOSITORIES_METADATA,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("url", String, nullable=False),
    Column("api_url", String, nullable=True),  # Added API URL field
    Column("description", String, nullable=True),
    Column("type", String, nullable=False, server_default="git"),  # git, svn, etc.
    Column("branch", String, nullable=True),
    Column("auth_type", String, nullable=True),  # ssh, token, basic, none
    Column("auth_config", JSON, nullable=True),  # Store encrypted credentials
    Column("owner", String, nullable=False),
    Column("is_active", Boolean, nullable=False, server_default=text('true')),  # Fixed Boolean
    Column("last_sync_status", String, nullable=True),
    Column("last_sync_at", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=text('CURRENT_TIMESTAMP')),
    Column("updated_at", DateTime(timezone=True), server_default=text('CURRENT_TIMESTAMP'), onupdate=text('CURRENT_TIMESTAMP')),
)

# --- Agents Table ---
_AGENTS_METADATA = MetaData()
_AGENTS_TABLE = Table(
    "agents",
    _AGENTS_METADATA,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("description", String, nullable=True),
    Column("agent_type", String, nullable=False),  # code_analyzer, test_runner, deployer, etc.
    Column("config", JSON, nullable=False),  # Agent-specific configuration
    Column("status", String, nullable=False, server_default="inactive"),  # active, inactive, error
    Column("last_heartbeat", DateTime(timezone=True), nullable=True),
    Column("capabilities", JSON, nullable=True),  # What this agent can do
    Column("owner", String, nullable=False),
    Column("is_public", Boolean, nullable=False, server_default=text('false')),  # Fixed Boolean
    Column("created_at", DateTime(timezone=True), server_default=text('CURRENT_TIMESTAMP')),
    Column("updated_at", DateTime(timezone=True), server_default=text('CURRENT_TIMESTAMP'), onupdate=text('CURRENT_TIMESTAMP')),
)

# --- Agent Runs Table (for tracking agent executions) ---
_AGENT_RUNS_METADATA = MetaData()
_AGENT_RUNS_TABLE = Table(
    "agent_runs",
    _AGENT_RUNS_METADATA,
    Column("id", String, primary_key=True),
    Column("agent_id", String, nullable=False),
    Column("project_id", String, nullable=True),
    Column("plan_id", String, nullable=True),
    Column("status", String, nullable=False, server_default="queued"),
    Column("input_data", JSON, nullable=True),
    Column("output_data", JSON, nullable=True),
    Column("started_at", DateTime(timezone=True), nullable=True),
    Column("completed_at", DateTime(timezone=True), nullable=True),
    Column("error_message", String, nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=text('CURRENT_TIMESTAMP')),
    Column("updated_at", DateTime(timezone=True), server_default=text('CURRENT_TIMESTAMP'), onupdate=text('CURRENT_TIMESTAMP')),
)

# ---------- Interaction History DB (Postgres/SQLite via SQLAlchemy) ----------
def ensure_history_schema(engine: Engine) -> None:
    _HISTORY_METADATA.create_all(engine)

class InteractionHistoryRepoDB:
    def __init__(self, engine: Engine):
        ensure_history_schema(engine)
        self.engine = engine

    def add(self, entry: dict) -> None:
        with self.engine.begin() as conn:
            if "id" not in entry:
                entry["id"] = str(uuid.uuid4())
            conn.execute(insert(_HISTORY_TABLE).values(**entry))

    def list_by_project(self, project_id: str) -> list[dict]:
        with self.engine.begin() as conn:
            result = conn.execute(
                select(_HISTORY_TABLE).where(_HISTORY_TABLE.c.project_id == project_id)
            )
            return [dict(row) for row in result.mappings()]

    def list_all(self) -> list[dict]:
        with self.engine.begin() as conn:
            result = conn.execute(select(_HISTORY_TABLE))
            return [dict(row) for row in result.mappings()]

# A single metadata object for our schema
_NOTES_METADATA = MetaData()

# Table: notes
_NOTES_TABLE = Table(
    "notes",
    _NOTES_METADATA,
    Column("id", String, primary_key=True),          # short hex id
    Column("data", JSON, nullable=False),            # the payload you POST/PUT (e.g., {"text": "...", ...})
    Column("created_at", DateTime(timezone=True), server_default=text('CURRENT_TIMESTAMP')),
)

def ensure_notes_schema(engine: Engine) -> None:
    """Create the notes schema (idempotent) using our local SQLAlchemy metadata."""
    _NOTES_METADATA.create_all(engine)

def ensure_plans_schema(engine: Engine) -> None:
    _PLANS_METADATA.create_all(engine)

def ensure_runs_schema(engine: Engine) -> None:
    _RUNS_METADATA.create_all(engine)

def ensure_projects_schema(engine: Engine) -> None:
    _PROJECTS_METADATA.create_all(engine)

# Schema creation functions - place these AFTER all table definitions
def ensure_repositories_schema(engine: Engine) -> None:
    _REPOSITORIES_METADATA.create_all(engine)

def ensure_agents_schema(engine: Engine) -> None:
    _AGENTS_METADATA.create_all(engine)

def ensure_agent_runs_schema(engine: Engine) -> None:
    _AGENT_RUNS_METADATA.create_all(engine)

class RepositoriesRepoDB:
    def __init__(self, engine: Engine):
        self.engine = engine
        ensure_repositories_schema(engine)
    
    def create(self, entry: dict) -> dict:
        with self.engine.begin() as conn:
            if "id" not in entry:
                entry["id"] = uuid.uuid4().hex[:8]
            conn.execute(insert(_REPOSITORIES_TABLE).values(**entry))
        return entry
    
    def get(self, repo_id: str) -> dict | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                select(_REPOSITORIES_TABLE).where(_REPOSITORIES_TABLE.c.id == repo_id)
            ).first()
            if not row:
                return None
            return dict(row._mapping)
    
    def list(self, limit: int = 20, offset: int = 0, **filters) -> tuple[list[dict], int]:
        owner = filters.get("owner")
        is_active = filters.get("is_active")
        repo_type = filters.get("type")
        
        try:
            with self.engine.connect() as conn:
                where_clauses = [sql_true()]
                
                if owner:
                    where_clauses.append(_REPOSITORIES_TABLE.c.owner == owner)
                
                if is_active is not None:
                    where_clauses.append(_REPOSITORIES_TABLE.c.is_active == is_active)
                
                if repo_type:
                    where_clauses.append(_REPOSITORIES_TABLE.c.type == repo_type)
                
                where_clause = and_(*where_clauses)
                
                # Get total count
                count_stmt = select(func.count()).select_from(_REPOSITORIES_TABLE).where(where_clause)
                total = conn.execute(count_stmt).scalar_one()
                
                # Get paginated results
                list_stmt = (
                    select(_REPOSITORIES_TABLE)
                    .where(where_clause)
                    .order_by(desc(_REPOSITORIES_TABLE.c.updated_at))
                    .limit(limit)
                    .offset(offset)
                )
                
                rows = conn.execute(list_stmt).mappings().all()
                return [dict(row) for row in rows], int(total)
                
        except Exception:
            return [], 0
    
    def update(self, repo_id: str, fields: dict) -> dict | None:
        if not fields:
            return self.get(repo_id)
        
        allowed_fields = {"name", "url", "api_url", "description", "type", "branch", "auth_type", "auth_config", "is_active", "last_sync_status", "last_sync_at"}
        payload = {k: v for k, v in fields.items() if k in allowed_fields}
        
        if not payload:
            return self.get(repo_id)
        
        with self.engine.begin() as conn:
            conn.execute(
                update(_REPOSITORIES_TABLE)
                .where(_REPOSITORIES_TABLE.c.id == repo_id)
                .values(**payload)
            )
        return self.get(repo_id)
    
    def delete(self, repo_id: str) -> bool:
        with self.engine.begin() as conn:
            result = conn.execute(
                sa_delete(_REPOSITORIES_TABLE).where(_REPOSITORIES_TABLE.c.id == repo_id)
            )
            return result.rowcount > 0

class AgentsRepoDB:
    def __init__(self, engine: Engine):
        self.engine = engine
        ensure_agents_schema(engine)
    
    def create(self, entry: dict) -> dict:
        with self.engine.begin() as conn:
            if "id" not in entry:
                entry["id"] = uuid.uuid4().hex[:8]
            conn.execute(insert(_AGENTS_TABLE).values(**entry))
        return entry
    
    def get(self, agent_id: str) -> dict | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                select(_AGENTS_TABLE).where(_AGENTS_TABLE.c.id == agent_id)
            ).first()
            if not row:
                return None
            return dict(row._mapping)
    
    def list(self, limit: int = 20, offset: int = 0, **filters) -> tuple[list[dict], int]:
        owner = filters.get("owner")
        agent_type = filters.get("agent_type")
        status = filters.get("status")
        is_public = filters.get("is_public")
        
        try:
            with self.engine.connect() as conn:
                where_clauses = [sql_true()]
                
                if owner:
                    where_clauses.append(_AGENTS_TABLE.c.owner == owner)
                
                if agent_type:
                    where_clauses.append(_AGENTS_TABLE.c.agent_type == agent_type)
                
                if status:
                    where_clauses.append(_AGENTS_TABLE.c.status == status)
                
                if is_public is not None:
                    if is_public:
                        where_clauses.append(_AGENTS_TABLE.c.is_public == True)
                    else:
                        where_clauses.append(or_(
                            _AGENTS_TABLE.c.is_public == False,
                            _AGENTS_TABLE.c.owner == owner
                        ))
                
                where_clause = and_(*where_clauses)
                
                # Get total count
                count_stmt = select(func.count()).select_from(_AGENTS_TABLE).where(where_clause)
                total = conn.execute(count_stmt).scalar_one()
                
                # Get paginated results
                list_stmt = (
                    select(_AGENTS_TABLE)
                    .where(where_clause)
                    .order_by(desc(_AGENTS_TABLE.c.updated_at))
                    .limit(limit)
                    .offset(offset)
                )
                
                rows = conn.execute(list_stmt).mappings().all()
                return [dict(row) for row in rows], int(total)
                
        except Exception:
            return [], 0
    
    def update(self, agent_id: str, fields: dict) -> dict | None:
        if not fields:
            return self.get(agent_id)
        
        allowed_fields = {"name", "description", "agent_type", "config", "status", "last_heartbeat", "capabilities", "is_public"}
        payload = {k: v for k, v in fields.items() if k in allowed_fields}
        
        if not payload:
            return self.get(agent_id)
        
        with self.engine.begin() as conn:
            conn.execute(
                update(_AGENTS_TABLE)
                .where(_AGENTS_TABLE.c.id == agent_id)
                .values(**payload)
            )
        return self.get(agent_id)
    
    def delete(self, agent_id: str) -> bool:
        with self.engine.begin() as conn:
            result = conn.execute(
                sa_delete(_AGENTS_TABLE).where(_AGENTS_TABLE.c.id == agent_id)
            )
            return result.rowcount > 0

class AgentRunsRepoDB:
    def __init__(self, engine: Engine):
        self.engine = engine
        ensure_agent_runs_schema(engine)
    
    def create(self, entry: dict) -> dict:
        with self.engine.begin() as conn:
            if "id" not in entry:
                entry["id"] = uuid.uuid4().hex[:8]
            conn.execute(insert(_AGENT_RUNS_TABLE).values(**entry))
        return entry
    
    def get(self, run_id: str) -> dict | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                select(_AGENT_RUNS_TABLE).where(_AGENT_RUNS_TABLE.c.id == run_id)
            ).first()
            if not row:
                return None
            return dict(row._mapping)
    
    def list(self, limit: int = 20, offset: int = 0, **filters) -> tuple[list[dict], int]:
        agent_id = filters.get("agent_id")
        project_id = filters.get("project_id")
        plan_id = filters.get("plan_id")
        status = filters.get("status")
        
        try:
            with self.engine.connect() as conn:
                where_clauses = [sql_true()]
                
                if agent_id:
                    where_clauses.append(_AGENT_RUNS_TABLE.c.agent_id == agent_id)
                
                if project_id:
                    where_clauses.append(_AGENT_RUNS_TABLE.c.project_id == project_id)
                
                if plan_id:
                    where_clauses.append(_AGENT_RUNS_TABLE.c.plan_id == plan_id)
                
                if status:
                    where_clauses.append(_AGENT_RUNS_TABLE.c.status == status)
                
                where_clause = and_(*where_clauses)
                
                # Get total count
                count_stmt = select(func.count()).select_from(_AGENT_RUNS_TABLE).where(where_clause)
                total = conn.execute(count_stmt).scalar_one()
                
                # Get paginated results
                list_stmt = (
                    select(_AGENT_RUNS_TABLE)
                    .where(where_clause)
                    .order_by(desc(_AGENT_RUNS_TABLE.c.created_at))
                    .limit(limit)
                    .offset(offset)
                )
                
                rows = conn.execute(list_stmt).mappings().all()
                return [dict(row) for row in rows], int(total)
                
        except Exception:
            return [], 0
    
    def update(self, run_id: str, fields: dict) -> dict | None:
        if not fields:
            return self.get(run_id)
        
        allowed_fields = {"status", "input_data", "output_data", "started_at", "completed_at", "error_message"}
        payload = {k: v for k, v in fields.items() if k in allowed_fields}
        
        if not payload:
            return self.get(run_id)
        
        with self.engine.begin() as conn:
            conn.execute(
                update(_AGENT_RUNS_TABLE)
                .where(_AGENT_RUNS_TABLE.c.id == run_id)
                .values(**payload)
            )
        return self.get(run_id)

class ProjectsRepoDB:
    def __init__(self, engine: Engine):
        self.engine = engine
        ensure_projects_schema(engine)
    
    def create(self, entry: dict) -> dict:
        with self.engine.begin() as conn:
            conn.execute(insert(_PROJECTS_TABLE).values(**entry))
        return entry
    
    def get(self, project_id: str) -> dict | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                select(
                    _PROJECTS_TABLE.c.id,
                    _PROJECTS_TABLE.c.title,
                    _PROJECTS_TABLE.c.description,
                    _PROJECTS_TABLE.c.owner,
                    _PROJECTS_TABLE.c.status,
                    _PROJECTS_TABLE.c.created_at,
                    _PROJECTS_TABLE.c.updated_at,
                ).where(_PROJECTS_TABLE.c.id == project_id)
            ).first()
        if not row:
            return None
        pid, title, description,  owner, status, created_at, updated_at = row
        return {
            "id": pid,
            "title": title,
            "description": description,
            "owner": owner,
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

        try:
            with self.engine.connect() as conn:
                metadata = MetaData()
                # reflect only the 'plans' table using the live connection
                try:
                    metadata.reflect(bind=conn, only=["projects"])
                    projects = metadata.tables.get("projects")
                    if projects is None:
                        return [], 0
                except Exception:
                    # If reflection fails (table missing), return empty result
                    return [], 0

                cols = set(projects.c.keys())
                has = cols.__contains__
                allowed_sort = {c for c in (
                    "created_at", "title", "description", "owner", "last_run_status", "last_run_at", "id"
                ) if has(c)}

                # choose sort column
                if sort in allowed_sort and sort in projects.c:
                    sort_col = projects.c[sort]
                elif "created_at" in cols and "created_at" in projects.c:
                    sort_col = projects.c["created_at"]
                elif "id" in cols and "id" in projects.c:
                    sort_col = projects.c["id"]
                else:
                    return [], 0

                order_by = asc(sort_col) if order == "asc" else desc(sort_col)

                where_clauses = [sql_true()]

                if q:
                    qv = f"%{q.lower()}%"
                    q_clauses = []
                    if "id" in cols and "id" in projects.c:
                        q_clauses.append(func.lower(cast(projects.c.id, String)).like(qv))
                    if q_clauses:
                        where_clauses.append(or_(*q_clauses))

                if status and "last_run_status" in cols and "last_run_status" in projects.c:
                    where_clauses.append(projects.c.last_run_status == status)

                if owner and "owner" in cols and "owner" in projects.c:
                    where_clauses.append(projects.c.owner == owner)

                where_clause = and_(*where_clauses)

                list_stmt = (
                    select(projects)
                    .where(where_clause)
                    .order_by(order_by)
                    .limit(limit)
                    .offset(offset)
                )

                count_stmt = select(func.count()).select_from(projects).where(where_clause)

                rows = conn.execute(list_stmt).mappings().all()
                total = conn.execute(count_stmt).scalar_one()
                return rows, int(total)

        except (OperationalError, ProgrammingError, SQLAlchemyError):
            return [], 0
        
    def update(self, project_id: str, fields: dict) -> dict | None:
        if not fields:
            return self.get(project_id)
        allowed = {"title", "description", "owner", "artifacts", "status"}
        payload = {k: v for k, v in fields.items() if k in allowed}
        if not payload:
            return self.get(project_id)
        with self.engine.begin() as conn:
            res = conn.execute(
                update(_PROJECTS_TABLE)
                .where(_PROJECTS_TABLE.c.id == project_id)
                .values(**payload)
            )
            # res.rowcount might be 0 if not found
        return self.get(project_id)
    
class PlansRepoDB:
    def __init__(self, engine: Engine):
        self.engine = engine
        ensure_plans_schema(engine)

    def create(self, entry: dict) -> dict:
        # Ensure a project exists and a project_id is set; create a default project on-the-fly
        pid = (entry or {}).get("project_id")
        if not pid:
            # Create or reuse a deterministic project id based on plan id if present
            import uuid
            plan_id = (entry or {}).get("id") or uuid.uuid4().hex[:8]
            pid = f"proj-{plan_id}"
            # Best-effort: ensure the projects table exists and insert a minimal project row
            try:
                ProjectsRepoDB(self.engine).create({
                    "id": pid,
                    "title": (entry or {}).get("request") or plan_id,
                    "description": (entry or {}).get("request") or "",
                    "owner": (entry or {}).get("owner") or "ui",
                    "status": (entry or {}).get("status") or "new",
                })
            except Exception:
                # If project creation fails, still proceed with setting the id; DB will enforce if truly missing
                pass
            entry = dict(entry or {})
            entry["project_id"] = pid
        with self.engine.begin() as conn:
            conn.execute(insert(_PLANS_TABLE).values(**entry))
        return entry

    def get(self, plan_id: str) -> dict | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                select(
                    _PLANS_TABLE.c.id,
                    _PLANS_TABLE.c.project_id,
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
        rid, pid, req, owner, arts, status, created_at, updated_at = row
        return {
            "id": rid,
            "project_id": pid,
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

        try:
            with self.engine.connect() as conn:
                metadata = MetaData()
                # reflect only the 'plans' table using the live connection
                try:
                    metadata.reflect(bind=conn, only=["plans"])
                    plans = metadata.tables.get("plans")
                    if plans is None:
                        return [], 0
                except Exception:
                    # If reflection fails (table missing), return empty result
                    return [], 0

                cols = set(plans.c.keys())
                has = cols.__contains__
                allowed_sort = {c for c in (
                    "created_at", "request", "owner", "last_run_status", "last_run_at", "id"
                ) if has(c)}

                # choose sort column
                if sort in allowed_sort and sort in plans.c:
                    sort_col = plans.c[sort]
                elif "created_at" in cols and "created_at" in plans.c:
                    sort_col = plans.c["created_at"]
                elif "id" in cols and "id" in plans.c:
                    sort_col = plans.c["id"]
                else:
                    return [], 0

                order_by = asc(sort_col) if order == "asc" else desc(sort_col)

                where_clauses = [sql_true()]

                if q:
                    qv = f"%{q.lower()}%"
                    q_clauses = []
                    if "request" in cols and "request" in plans.c:
                        q_clauses.append(func.lower(plans.c.request).like(qv))
                    if "id" in cols and "id" in plans.c:
                        q_clauses.append(func.lower(cast(plans.c.id, String)).like(qv))
                    if q_clauses:
                        where_clauses.append(or_(*q_clauses))

                if status and "last_run_status" in cols and "last_run_status" in plans.c:
                    where_clauses.append(plans.c.last_run_status == status)

                if owner and "owner" in cols and "owner" in plans.c:
                    where_clauses.append(plans.c.owner == owner)

                where_clause = and_(*where_clauses)

                list_stmt = (
                    select(plans)
                    .where(where_clause)
                    .order_by(order_by)
                    .limit(limit)
                    .offset(offset)
                )

                count_stmt = select(func.count()).select_from(plans).where(where_clause)

                rows = conn.execute(list_stmt).mappings().all()
                total = conn.execute(count_stmt).scalar_one()
                return rows, int(total)

        except (OperationalError, ProgrammingError, SQLAlchemyError):
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
        # This method is not applicable to Notes; leaving a safe no-op for compatibility
        return None        

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