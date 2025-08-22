import os
from typing import Any
try:
    from .postgres import PostgresNotesRepo
    from .memory import InMemoryNotesRepo
except ImportError:
    from services.api.repo.postgres import PostgresNotesRepo
    from services.api.repo.memory import InMemoryNotesRepo

def notes_repo() -> Any:
    dsn = os.getenv("DB_URL")
    if dsn:
        return PostgresNotesRepo(dsn)
    return InMemoryNotesRepo()
