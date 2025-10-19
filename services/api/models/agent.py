from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, ConfigDict, field_serializer

class AgentTemplateBase(BaseModel):
    name: str
    type: str
    description: Optional[str] = None
    config: Optional[Dict] = {}

class AgentTemplateCreate(AgentTemplateBase):
    pass

class AgentTemplateUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict] = None

class AgentTemplate(AgentTemplateBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat() if value else None