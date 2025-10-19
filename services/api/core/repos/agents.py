# services/api/core/repos/agents.py

from typing import Dict, List, Any, Optional
from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session
from datetime import datetime, UTC

from services.api.core.db import agent_templates
from services.api.core.shared import _create_engine, _database_url, _repo_root


class AgentsRepoDB:
    """Repository for agents (using agent_templates table)."""
    
    def __init__(self, engine):
        self.engine = engine
    
    def create(self, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new agent."""
        with Session(self.engine) as session:
            # Map the expected fields to agent_templates schema
            insert_data = {
                "name": agent_data.get("name"),
                "type": agent_data.get("agent_type", "unknown"),
                "description": agent_data.get("description", ""),
                "config": agent_data.get("config", {}),
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC)
            }
            
            result = session.execute(
                agent_templates.insert().values(**insert_data)
            )
            session.commit()
            
            # Return with id
            return {
                "id": str(result.inserted_primary_key[0]),
                **insert_data
            }
    
    def get(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get a single agent by ID."""
        with Session(self.engine) as session:
            stmt = select(agent_templates).where(agent_templates.c.id == agent_id)
            result = session.execute(stmt).first()
            
            if result:
                return dict(result._mapping)
            return None
    
    def list(self, 
             limit: int = 100,
             offset: int = 0,
             agent_type: Optional[str] = None,
             owner: Optional[str] = None,
             status: Optional[str] = None) -> tuple[List[Dict[str, Any]], int]:
        """List agents with optional filters. Returns (agents, total_count)."""
        with Session(self.engine) as session:
            # Get total count first
            count_stmt = select(agent_templates)
            if agent_type:
                count_stmt = count_stmt.where(agent_templates.c.type == agent_type)
            total = session.execute(count_stmt).fetchall()
            total_count = len(total)
            
            # Get paginated results
            stmt = select(agent_templates)
            
            # Apply filters if provided
            if agent_type:
                stmt = stmt.where(agent_templates.c.type == agent_type)
            
            stmt = stmt.limit(limit).offset(offset)
            results = session.execute(stmt).fetchall()
            
            return ([dict(row._mapping) for row in results], total_count)
    
    def update(self, agent_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an agent."""
        with Session(self.engine) as session:
            # Map fields
            mapped_data = {}
            if "name" in update_data:
                mapped_data["name"] = update_data["name"]
            if "agent_type" in update_data:
                mapped_data["type"] = update_data["agent_type"]
            if "description" in update_data:
                mapped_data["description"] = update_data["description"]
            if "config" in update_data:
                mapped_data["config"] = update_data["config"]
            
            mapped_data["updated_at"] = datetime.now(UTC)
            
            stmt = (
                update(agent_templates)
                .where(agent_templates.c.id == agent_id)
                .values(**mapped_data)
            )
            
            session.execute(stmt)
            session.commit()
            
            return self.get(agent_id)
    
    def delete(self, agent_id: str) -> bool:
        """Delete an agent."""
        with Session(self.engine) as session:
            stmt = delete(agent_templates).where(agent_templates.c.id == agent_id)
            result = session.execute(stmt)
            session.commit()
            
            return result.rowcount > 0


class AgentRunsRepoDB:
    """Placeholder for agent runs repository."""
    
    def __init__(self, engine):
        self.engine = engine
    
    def create(self, run_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new agent run."""
        # Placeholder implementation
        return {"id": "placeholder", **run_data}
    
    def list(self, **filters) -> List[Dict[str, Any]]:
        """List agent runs."""
        # Placeholder implementation
        return []
