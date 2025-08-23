from typing import Optional
try:
    from .memory import InMemoryNotesRepo
except ModuleNotFoundError:
    from services.api.repo.memory import InMemoryNotesRepo

_notes_repo: Optional[InMemoryNotesRepo] = None

def get_notes_repo() -> InMemoryNotesRepo:
    global _notes_repo
    if _notes_repo is None:
        _notes_repo = InMemoryNotesRepo()
    return _notes_repo

# export a ready-to-use singleton for simple imports
notes_repo = get_notes_repo()
