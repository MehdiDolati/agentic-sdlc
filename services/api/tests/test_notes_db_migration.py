from pathlib import Path
from sqlalchemy import create_engine, inspect
from app import ensure_notes_schema

def test_notes_migration_creates_table(tmp_path: Path):
    db_file = tmp_path / "notes.db"
    url = f"sqlite+pysqlite:///{db_file}"
    engine = create_engine(url, future=True)

    insp = inspect(engine)
    assert "notes" not in insp.get_table_names()

    ensure_notes_schema(engine)

    insp = inspect(engine)
    assert "notes" in insp.get_table_names()
