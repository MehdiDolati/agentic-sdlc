from datetime import datetime
from typing import Optional, Dict, List
from pydantic import BaseModel, HttpUrl, ConfigDict

class RepositoryBase(BaseModel):
    url: HttpUrl
    owner: str
    name: str

class RepositoryCreate(RepositoryBase):
    pass

class Repository(RepositoryBase):
    id: str  # Changed from int to str to match UUID-based IDs
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ProjectAgentBase(BaseModel):
    name: str
    type: str
    description: Optional[str] = None
    config: Optional[Dict] = {}
    step_key: Optional[str] = None  # SDLC step this agent is assigned to

class ProjectAgentCreate(BaseModel):
    agent_template_id: int
    name: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = ""
    config: Optional[Dict] = {}
    step_key: Optional[str] = None  # SDLC step this agent is assigned to

class ProjectAgent(ProjectAgentBase):
    id: int
    project_id: str  # Changed to str to match UUID-based project IDs
    agent_template_id: int
    created_at: str  # ISO format datetime string
    updated_at: str  # ISO format datetime string

    model_config = ConfigDict(from_attributes=True)

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    repository_url: Optional[HttpUrl] = None
    repository_owner: Optional[str] = None
    repository_name: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    repository_url: Optional[HttpUrl] = None
    repository_owner: Optional[str] = None
    repository_name: Optional[str] = None

class Project(ProjectBase):
    id: int
    repository_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    agents: List[ProjectAgent] = []
    repository: Optional[Repository] = None

    model_config = ConfigDict(from_attributes=True)

class PlanBase(BaseModel):
    request: str  # Changed from 'name' to match database schema
    artifacts: Optional[str] = None  # Changed from 'description' to match database schema
    size_estimate: int = 1  # Story points or similar size metric
    priority: str = "medium"  # low, medium, high, critical
    priority_order: Optional[int] = None  # For custom ordering within same priority level
    status: str = "pending"  # pending, in_progress, completed, cancelled

class PlanCreate(PlanBase):
    project_id: str

class Plan(PlanBase):
    id: str
    project_id: str
    created_at: str
    updated_at: str
    features: List['Feature'] = []

    model_config = ConfigDict(from_attributes=True)

class FeatureBase(BaseModel):
    name: str
    description: str
    size_estimate: int = 1  # Story points or similar size metric
    priority: str = "medium"  # low, medium, high, critical
    priority_order: Optional[int] = None  # For custom ordering within same priority level
    status: str = "pending"  # pending, in_progress, completed, cancelled

class FeatureCreate(FeatureBase):
    plan_id: str

class Feature(FeatureBase):
    id: str
    plan_id: str
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)

class PriorityChangeBase(BaseModel):
    entity_type: str  # "plan" or "feature"
    entity_id: str
    old_priority: Optional[str] = None
    new_priority: str
    old_priority_order: Optional[int] = None
    new_priority_order: Optional[int] = None
    change_reason: Optional[str] = None

class PriorityChangeCreate(PriorityChangeBase):
    changed_by: Optional[str] = None

class PriorityChange(PriorityChangeBase):
    id: int
    changed_by: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)