import os
from fastapi import APIRouter, HTTPException
try:
    import psycopg2
except Exception as e:
    psycopg2 = None

router = APIRouter(prefix="/db", tags=["db"])

@router.get("/health")
def db_health():
    url = os.getenv("DB_URL")
    if not url:
        return {"status": "disabled"}
    if psycopg2 is None:
        raise HTTPException(status_code=500, detail="psycopg2 not installed")
    try:
        conn = psycopg2.connect(url)
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            row = cur.fetchone()
        conn.close()
        return {"status": "ok", "result": row[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")
