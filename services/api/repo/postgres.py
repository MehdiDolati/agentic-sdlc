from typing import Dict, Any, List, Optional
import psycopg2
import psycopg2.extras

class PostgresNotesRepo:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def _conn(self):
        return psycopg2.connect(self._dsn)

    def list(self) -> List[Dict[str, Any]]:
        with self._conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id::text, title, content FROM notes ORDER BY created_at DESC")
            return [dict(r) for r in cur.fetchall()]

    def create(self, title: str, content: str) -> Dict[str, Any]:
        with self._conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO notes (id, title, content) VALUES (gen_random_uuid(), %s, %s) RETURNING id::text, title, content",
                (title, content),
            )
            return dict(cur.fetchone())

    def get(self, id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id::text, title, content FROM notes WHERE id = %s", (id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def update(self, id: str, title: str, content: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "UPDATE notes SET title = %s, content = %s WHERE id = %s RETURNING id::text, title, content",
                (title, content, id),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def delete(self, id: str) -> bool:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM notes WHERE id = %s", (id,))
            return cur.rowcount > 0
