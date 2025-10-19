from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from services.api.models.agent import AgentTemplate, AgentTemplateCreate, AgentTemplateUpdate
from services.api.core.db import agent_templates

class AgentTemplateRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, template: AgentTemplateCreate) -> AgentTemplate:
        new_template = template.dict()
        result = self.db.execute(agent_templates.insert().values(**new_template))
        self.db.commit()
        return self.get(result.lastrowid)

    def get(self, template_id: int) -> Optional[AgentTemplate]:
        query = select([agent_templates]).where(agent_templates.c.id == template_id)
        result = self.db.execute(query).first()
        return AgentTemplate(**result) if result else None

    def list_all(self) -> List[AgentTemplate]:
        query = select([agent_templates])
        results = self.db.execute(query).fetchall()
        return [AgentTemplate(**row) for row in results]

    def update(self, template_id: int, template: AgentTemplateUpdate) -> Optional[AgentTemplate]:
        update_data = template.dict(exclude_unset=True)
        if not update_data:
            return self.get(template_id)

        query = agent_templates.update().where(agent_templates.c.id == template_id).values(**update_data)
        result = self.db.execute(query)
        self.db.commit()
        return self.get(template_id) if result.rowcount > 0 else None

    def delete(self, template_id: int) -> bool:
        query = agent_templates.delete().where(agent_templates.c.id == template_id)
        result = self.db.execute(query)
        self.db.commit()
        return result.rowcount > 0