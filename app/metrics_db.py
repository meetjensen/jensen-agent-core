import os
from sqlalchemy import create_engine, text

DB_URL = os.getenv("DATABASE_URL","")
ENABLED = os.getenv("INTEGRATIONS_ENABLED","false").lower()=="true"

def job_counters():
    if not (ENABLED and DB_URL):
        return {"total":0, "queued":0, "running":0, "ok":0, "error":0}
    e = create_engine(DB_URL, pool_pre_ping=True, future=True)
    with e.connect() as c:
        total = c.execute(text("select count(*) from jobs")).scalar() or 0
        rows  = c.execute(text("select status, count(*) from jobs group by status")).all()
    by = {r[0]: int(r[1]) for r in rows}
    # normalize keys we care about
    return {
        "total": total,
        "queued": by.get("queued", 0),
        "running": by.get("running", 0),
        "ok":     by.get("ok", 0),
        "error":  by.get("error", 0),
    }
