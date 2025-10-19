from typing import List
from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from services.api.core.db import agent_templates
from services.api.core.shared import _create_engine, _database_url, _repo_root
from services.api.models.agent import AgentTemplate, AgentTemplateCreate, AgentTemplateUpdate
from datetime import datetime, UTC

router = APIRouter(tags=["agents"])

def _get_engine():
    """Get database engine."""
    return _create_engine(_database_url(_repo_root()))

@router.get("/agents", response_model=List[AgentTemplate])
def list_agent_templates():
    try:
        engine = _get_engine()
        with Session(engine) as session:
            stmt = select(agent_templates)
            results = session.execute(stmt).fetchall()
            
            templates = []
            for row in results:
                r = row._mapping
                templates.append(AgentTemplate(
                    id=r["id"],
                    name=r["name"],
                    type=r["type"],
                    description=r["description"],
                    config=r["config"] or {},
                    created_at=r["created_at"],
                    updated_at=r["updated_at"]
                ))
            return templates
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list agent templates: {str(e)}")

@router.post("/agents", response_model=AgentTemplate)
def create_agent_template(template: AgentTemplateCreate):
    try:
        engine = _get_engine()
        with Session(engine) as session:
            insert_data = {
                "name": template.name,
                "type": template.type,
                "description": template.description,
                "config": template.config or {},
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC)
            }
            
            result = session.execute(
                agent_templates.insert().values(**insert_data)
            )
            session.commit()
            
            # Fetch the created template
            template_id = result.inserted_primary_key[0]
            stmt = select(agent_templates).where(agent_templates.c.id == template_id)
            row = session.execute(stmt).first()
            r = row._mapping
            
            return AgentTemplate(
                id=r["id"],
                name=r["name"],
                type=r["type"],
                description=r["description"],
                config=r["config"] or {},
                created_at=r["created_at"],
                updated_at=r["updated_at"]
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create agent template: {str(e)}")

@router.get("/agents/{template_id}", response_model=AgentTemplate)
def get_agent_template(template_id: int):
    try:
        engine = _get_engine()
        with Session(engine) as session:
            stmt = select(agent_templates).where(agent_templates.c.id == template_id)
            row = session.execute(stmt).first()
            
            if not row:
                raise HTTPException(status_code=404, detail="Agent template not found")
            
            r = row._mapping
            return AgentTemplate(
                id=r["id"],
                name=r["name"],
                type=r["type"],
                description=r["description"],
                config=r["config"] or {},
                created_at=r["created_at"],
                updated_at=r["updated_at"]
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent template: {str(e)}")

@router.put("/agents/{template_id}", response_model=AgentTemplate)
def update_agent_template(template_id: int, template: AgentTemplateUpdate):
    try:
        engine = _get_engine()
        with Session(engine) as session:
            # Check if exists
            stmt = select(agent_templates).where(agent_templates.c.id == template_id)
            existing = session.execute(stmt).first()
            
            if not existing:
                raise HTTPException(status_code=404, detail="Agent template not found")
            
            # Build update data
            update_data = {"updated_at": datetime.now(UTC)}
            if template.name is not None:
                update_data["name"] = template.name
            if template.type is not None:
                update_data["type"] = template.type
            if template.description is not None:
                update_data["description"] = template.description
            if template.config is not None:
                update_data["config"] = template.config
            
            # Update
            from sqlalchemy import update
            stmt = (
                update(agent_templates)
                .where(agent_templates.c.id == template_id)
                .values(**update_data)
            )
            session.execute(stmt)
            session.commit()
            
            # Fetch updated
            stmt = select(agent_templates).where(agent_templates.c.id == template_id)
            row = session.execute(stmt).first()
            r = row._mapping
            
            return AgentTemplate(
                id=r["id"],
                name=r["name"],
                type=r["type"],
                description=r["description"],
                config=r["config"] or {},
                created_at=r["created_at"],
                updated_at=r["updated_at"]
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update agent template: {str(e)}")

@router.delete("/agents/{template_id}")
def delete_agent_template(template_id: int):
    try:
        engine = _get_engine()
        with Session(engine) as session:
            # Check if exists
            stmt = select(agent_templates).where(agent_templates.c.id == template_id)
            existing = session.execute(stmt).first()
            
            if not existing:
                raise HTTPException(status_code=404, detail="Agent template not found")
            
            # Delete
            from sqlalchemy import delete
            stmt = delete(agent_templates).where(agent_templates.c.id == template_id)
            session.execute(stmt)
            session.commit()
            
            return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete agent template: {str(e)}")