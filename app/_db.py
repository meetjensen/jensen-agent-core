from __future__ import annotations
import os
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    create_engine, MetaData, Table, Column, Integer, String, JSON,
    DateTime, Boolean, func, select, text
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError

DB_URL = os.getenv("DATABASE_URL", "")
ENABLED = os.getenv("INTEGRATIONS_ENABLED","false").lower()=="true"

metadata = MetaData()

actions = Table(
    "actions", metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(100), nullable=False, unique=True),
    Column("kind", String(50), nullable=False, default="http"),
    Column("config", JSON, nullable=False, default=dict),
    Column("enabled", Boolean, nullable=False, default=True),
    Column("created_at", DateTime, server_default=func.now(), nullable=False),
)

jobs = Table(
    "jobs", metadata,
    Column("id", Integer, primary_key=True),
    Column("action_id", Integer, nullable=False),
    Column("status", String(20), nullable=False, default="queued"),  # queued|running|ok|error
    Column("input", JSON, nullable=True),
    Column("result", JSON, nullable=True),
    Column("created_at", DateTime, server_default=func.now(), nullable=False),
    Column("updated_at", DateTime, server_default=func.now(), onupdate=func.now(), nullable=False),
)

audits = Table(
    "audits", metadata,
    Column("id", Integer, primary_key=True),
    Column("event", String(100), nullable=False),
    Column("detail", JSON, nullable=True),
    Column("created_at", DateTime, server_default=func.now(), nullable=False),
)

_engine: Optional[Engine] = None
def get_engine() -> Optional[Engine]:
    global _engine
    if not ENABLED or not DB_URL:
        return None
    if _engine is None:
        _engine = create_engine(DB_URL, pool_pre_ping=True, future=True)
    return _engine

def init_schema() -> bool:
    eng = get_engine()
    if not eng: return False
    try:
        metadata.create_all(eng)
        return True
    except OperationalError:
        return False

def seed_default_actions() -> None:
    eng = get_engine()
    if not eng: return
    with eng.begin() as conn:
        row = conn.execute(select(actions.c.id).limit(1)).fetchone()
        if row: return
        conn.execute(actions.insert().values(
            name="ping_json_placeholder",
            kind="http",
            config={"url": "https://jsonplaceholder.typicode.com/todos/1", "method": "GET"},
            enabled=True,
        ))

def list_actions() -> List[Dict[str, Any]]:
    eng = get_engine(); assert eng is not None
    with eng.connect() as c:
        return [dict(r) for r in c.execute(select(actions).order_by(actions.c.id.asc())).mappings().all()]

def get_action_by_id(aid: int) -> Optional[Dict[str, Any]]:
    eng = get_engine(); assert eng is not None
    with eng.connect() as c:
        r = c.execute(select(actions).where(actions.c.id==aid)).mappings().first()
        return dict(r) if r else None

def get_action_by_name(name: str) -> Optional[Dict[str, Any]]:
    eng = get_engine(); assert eng is not None
    with eng.connect() as c:
        r = c.execute(select(actions).where(actions.c.name==name)).mappings().first()
        return dict(r) if r else None

def enqueue_job(action_id: int, payload: Optional[Dict[str, Any]]) -> int:
    eng = get_engine(); assert eng is not None
    with eng.begin() as c:
        r = c.execute(jobs.insert().values(action_id=action_id, status="queued", input=payload))
        job_id = r.inserted_primary_key[0]
        c.execute(audits.insert().values(event="job_queued", detail={"job_id":job_id,"action_id":action_id}))
        return job_id

def list_jobs(limit: int = 50) -> List[Dict[str, Any]]:
    eng = get_engine(); assert eng is not None
    with eng.connect() as c:
        q = select(jobs).order_by(jobs.c.id.desc()).limit(limit)
        return [dict(r) for r in c.execute(q).mappings().all()]

def get_job(jid: int) -> Optional[Dict[str, Any]]:
    eng = get_engine(); assert eng is not None
    with eng.connect() as c:
        r = c.execute(select(jobs).where(jobs.c.id==jid)).mappings().first()
        return dict(r) if r else None

def set_job_status(jid: int, status: str, result: Optional[Dict[str,Any]]=None):
    eng = get_engine(); assert eng is not None
    with eng.begin() as c:
        c.execute(jobs.update().where(jobs.c.id==jid).values(status=status, result=result))
        evt = "job_"+("ok" if status=="ok" else status)
        c.execute(audits.insert().values(event=evt, detail={"job_id":jid,"result":result or {}}))
