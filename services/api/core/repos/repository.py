from typing import Optional, List, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.orm import Session
from services.api.core.db import repositories

class RepositoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, repo_data: Dict[str, Any]) -> Dict[str, Any]:
        result = self.db.execute(repositories.insert().values(**repo_data))
        self.db.commit()
        return self.get(repo_data["id"])

    def get(self, repo_id: str) -> Optional[Dict[str, Any]]:
        query = select(repositories).where(repositories.c.id == repo_id)
        result = self.db.execute(query).first()
        return dict(result._mapping) if result else None

    def get_by_owner_and_name(self, owner: str, name: str) -> Optional[Dict[str, Any]]:
        query = select(repositories).where(
            and_(
                repositories.c.owner == owner,
                repositories.c.name == name
            )
        )
        result = self.db.execute(query).first()
        return dict(result._mapping) if result else None

    def list(self, limit=20, offset=0, **filters):
        # Build SQLAlchemy filter conditions
        conditions = []
        for key, value in filters.items():
            if key == "$or" and isinstance(value, list):
                or_conditions = []
                for cond in value:
                    for k, v in cond.items():
                        or_conditions.append(getattr(repositories.c, k) == v)
                if or_conditions:
                    from sqlalchemy import or_
                    conditions.append(or_(*or_conditions))
            else:
                conditions.append(getattr(repositories.c, key) == value)
        query = select(repositories)
        if conditions:
            from sqlalchemy import and_
            query = query.where(and_(*conditions))
        query = query.limit(limit).offset(offset)
        results = self.db.execute(query).fetchall()
        total = len(results)
        return [dict(row._mapping) for row in results], total

    def update(self, repo_id: str, repo_data: dict) -> Optional[Dict[str, Any]]:
        if "url" in repo_data:
            repo_data["url"] = str(repo_data["url"])
        query = repositories.update().where(repositories.c.id == repo_id).values(**repo_data)
        self.db.execute(query)
        self.db.commit()
        return self.get(repo_id)

    def delete(self, repo_id: str) -> bool:
        query = repositories.delete().where(repositories.c.id == repo_id)
        result = self.db.execute(query)
        self.db.commit()
        return result.rowcount > 0