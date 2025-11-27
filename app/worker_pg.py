from __future__ import annotations
import os, asyncio, httpx
from typing import Dict, Any, List
from sqlalchemy import select
from app._db import get_engine, jobs, get_action_by_id, set_job_status

POLL = int(os.getenv("JOB_POLL_SEC","2"))
ENABLED = os.getenv("INTEGRATIONS_ENABLED","false").lower()=="true"

async def _run_http(job: Dict[str,Any], action: Dict[str,Any]):
    cfg = action.get("config") or {}
    url = cfg.get("url"); method = (cfg.get("method") or "GET").upper()
    headers = cfg.get("headers") or {}
    data = job.get("input") or {}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.request(method, url, headers=headers,
                                     json=(data if method!="GET" else None),
                                     params=(data if method=="GET" else None))
        body = r.json() if "application/json" in r.headers.get("content-type","") else r.text
        await asyncio.to_thread(set_job_status, job["id"], "ok", {"status_code": r.status_code, "body": body})
    except Exception as e:
        await asyncio.to_thread(set_job_status, job["id"], "error", {"error": str(e)})

async def worker_loop():
    if not ENABLED: return
    eng = get_engine()
    if not eng: return
    while True:
        rows: List[Dict[str,Any]] = []
        try:
            with eng.begin() as c:
                res = c.execute(select(jobs).where(jobs.c.status=="queued").order_by(jobs.c.id.asc()).limit(5))
                rows = [dict(r) for r in res.mappings().all()]
                for j in rows:
                    c.execute(jobs.update().where(jobs.c.id==j["id"]).values(status="running"))
        except Exception:
            rows = []

        for j in rows:
            a = get_action_by_id(j["action_id"])
            if not a:
                await asyncio.to_thread(set_job_status, j["id"], "error", {"error":"action_missing"})
                continue
            if (a.get("kind") or "http") == "http":
                await _run_http(j, a)
            else:
                await asyncio.to_thread(set_job_status, j["id"], "error", {"error":"unsupported_kind"})
        await asyncio.sleep(POLL)
