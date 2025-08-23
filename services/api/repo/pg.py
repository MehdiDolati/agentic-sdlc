import os
from typing import List, Optional
from uuid import uuid4
import psycopg

class NotesRepoPG:
    def __init__(self):
        dsn = os.getenv("DATABASE_URL", "postgresql://app:app@db:5432/appdb")
        # psycopg3: context-managed connections
        self._dsn = dsn
        self._ensure_table()

    def _ensure_table(self):
        sql = """
        CREATE TABLE IF NOT EXISTS notes(
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL
        );
        """
        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                conn.commit()

    def list(self) -> List[dict]:
        with psycopg.connect(self._dsn) as conn, conn.cursor() as cur:
            cur.execute("SELECT id,title,content FROM notes ORDER BY id;")
            return [{"id": r[0], "title": r[1], "content": r[2]} for r in cur.fetchall()]

    def get(self, note_id: str) -> Optional[dict]:
        with psycopg.connect(self._dsn) as conn, conn.cursor() as cur:
            cur.execute("SELECT id,title,content FROM notes WHERE id=%s;", (note_id,))
            row = cur.fetchone()
            return {"id": row[0], "title": row[1], "content": row[2]} if row else None

    def create(self, title: str, content: str) -> dict:
        _id = str(uuid4())
        with psycopg.connect(self._dsn) as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO notes(id,title,content) VALUES(%s,%s,%s);",
                (_id, title, content),
            )
            conn.commit()
        return {"id": _id, "title": title, "content": content}

    def update(self, note_id: str, title: str, content: str) -> Optional[dict]:
        with psycopg.connect(self._dsn) as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE notes SET title=%s, content=%s WHERE id=%s;",
                (title, content, note_id),
            )
            if cur.rowcount == 0:
                return None
            conn.commit()
        return {"id": note_id, "title": title, "content": content}

    def delete(self, note_id: str) -> bool:
        with psycopg.connect(self._dsn) as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM notes WHERE id=%s;", (note_id,))
            deleted = cur.rowcount > 0
            conn.commit()
            return deleted
