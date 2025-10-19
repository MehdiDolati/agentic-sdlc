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

class ProjectAgentCreate(BaseModel):
    agent_template_id: int
    name: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = ""
    config: Optional[Dict] = {}

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