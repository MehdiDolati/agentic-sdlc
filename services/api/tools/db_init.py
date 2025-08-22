import os, glob, psycopg2

def run():
    dsn = os.getenv("DB_URL")
    if not dsn:
        print("[db_init] DB_URL not set; skipping migrations")
        return
    files = sorted(glob.glob("sql/*.sql"))
    if not files:
        print("[db_init] no sql/*.sql files found; nothing to run")
        return
    with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
        for f in files:
            with open(f, "r", encoding="utf-8") as h:
                sql = h.read()
            print(f"[db_init] applying {f}")
            cur.execute(sql)
        conn.commit()
    print("[db_init] done")

if __name__ == "__main__":
    run()
