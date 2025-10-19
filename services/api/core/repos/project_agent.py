from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from services.api.models.project import ProjectAgent, ProjectAgentCreate
from services.api.core.db import project_agents

class ProjectAgentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, project_id: int, agent: ProjectAgentCreate) -> ProjectAgent:
        new_agent = {
            "project_id": project_id,
            "agent_type": agent.agent_type,
            "agent_name": agent.agent_name,
            "agent_description": agent.agent_description,
            "is_active": True
        }
        result = self.db.execute(project_agents.insert().values(**new_agent))
        self.db.commit()
        return self.get(result.lastrowid)

    def get(self, agent_id: int) -> Optional[ProjectAgent]:
        query = select([project_agents]).where(project_agents.c.id == agent_id)
        result = self.db.execute(query).first()
        return ProjectAgent(**result) if result else None

    def get_by_project(self, project_id: int) -> List[ProjectAgent]:
        query = select([project_agents]).where(project_agents.c.project_id == project_id)
        results = self.db.execute(query).fetchall()
        return [ProjectAgent(**row) for row in results]

    def update(self, agent_id: int, agent_data: dict) -> Optional[ProjectAgent]:
        query = project_agents.update().where(project_agents.c.id == agent_id).values(**agent_data)
        self.db.execute(query)
        self.db.commit()
        return self.get(agent_id)

    def delete(self, agent_id: int) -> bool:
        query = project_agents.delete().where(project_agents.c.id == agent_id)
        result = self.db.execute(query)
        self.db.commit()
        return result.rowcount > 0