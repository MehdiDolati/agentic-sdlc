from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.orm import Session
from services.api.models.project import Project, ProjectCreate, ProjectUpdate
from services.api.core.db import projects, repositories
from services.api.core.repos.repository import RepositoryRepository
from services.api.core.repos.project_agent import ProjectAgentRepository

class ProjectRepository:
    def __init__(self, db: Session):
        self.db = db
        self.repository_repo = RepositoryRepository(db)
        self.agent_repo = ProjectAgentRepository(db)

    def create(self, project: ProjectCreate) -> Project:
        project_data = project.dict(exclude_unset=True)
        repository_id = None
        
        # If repository information is provided, create or get repository
        if project.repository_owner and project.repository_name:
            repo = self.repository_repo.get_by_owner_and_name(
                project.repository_owner,
                project.repository_name
            )
            if not repo:
                repo = self.repository_repo.create({
                    "url": project.repository_url,
                    "owner": project.repository_owner,
                    "name": project.repository_name
                })
            repository_id = repo.id

        # Remove repository fields from project data
        for field in ["repository_url", "repository_owner", "repository_name"]:
            if field in project_data:
                del project_data[field]

        # Add repository_id if we have one
        if repository_id:
            project_data["repository_id"] = repository_id

        result = self.db.execute(projects.insert().values(**project_data))
        self.db.commit()
        return self.get(result.lastrowid)

    def get(self, project_id: int) -> Optional[Project]:
        query = select([projects, repositories]).select_from(
            projects.outerjoin(repositories, projects.c.repository_id == repositories.c.id)
        ).where(projects.c.id == project_id)
        
        result = self.db.execute(query).first()
        if not result:
            return None

        project_dict = {
            "id": result.id,
            "name": result.name,
            "description": result.description,
            "repository_id": result.repository_id,
            "created_at": result.created_at,
            "updated_at": result.updated_at,
        }

        if result.repository_id:
            project_dict["repository"] = {
                "id": result.repository_id,
                "url": result.url,
                "owner": result.owner,
                "name": result.name,
                "created_at": result.created_at,
                "updated_at": result.updated_at,
            }

        project = Project(**project_dict)
        project.agents = self.agent_repo.get_by_project(project_id)
        return project

    def list_all(self) -> List[Project]:
        query = select([projects])
        results = self.db.execute(query).fetchall()
        return [self.get(row.id) for row in results]

    def update(self, project_id: int, project_data: ProjectUpdate) -> Optional[Project]:
        update_data = project_data.dict(exclude_unset=True)
        repository_id = None

        # If repository information is provided, create or get repository
        if project_data.repository_owner and project_data.repository_name:
            repo = self.repository_repo.get_by_owner_and_name(
                project_data.repository_owner,
                project_data.repository_name
            )
            if not repo:
                repo = self.repository_repo.create({
                    "url": project_data.repository_url,
                    "owner": project_data.repository_owner,
                    "name": project_data.repository_name
                })
            repository_id = repo.id

        # Remove repository fields from update data
        for field in ["repository_url", "repository_owner", "repository_name"]:
            if field in update_data:
                del update_data[field]

        # Add repository_id if we have one
        if repository_id:
            update_data["repository_id"] = repository_id

        query = projects.update().where(projects.c.id == project_id).values(**update_data)
        result = self.db.execute(query)
        self.db.commit()
        
        return self.get(project_id) if result.rowcount > 0 else None

    def delete(self, project_id: int) -> bool:
        query = projects.delete().where(projects.c.id == project_id)
        result = self.db.execute(query)
        self.db.commit()
        return result.rowcount > 0