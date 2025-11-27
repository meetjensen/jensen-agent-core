from __future__ import annotations
import os
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Header, Depends, Query
from pydantic import BaseModel
from app._db import (
    ENABLED as INTEGRATIONS_ENABLED,
    init_schema, seed_default_actions,
    list_actions, get_action_by_id, get_action_by_name,
    enqueue_job, list_jobs, get_job
)

AGENT_TOKEN = os.getenv("AGENT_TOKEN","jensen4254")
router = APIRouter()

@router.on_event("startup")
def _boot():
    if not INTEGRATIONS_ENABLED: return
    if init_schema(): seed_default_actions()

@router.get("/integrations/actions")
def integrations_actions():
    if not INTEGRATIONS_ENABLED:
        return {"enabled": False, "actions": []}
    return {"enabled": True, "actions": list_actions()}

class ExecQuery(BaseModel):
    payload: Optional[Dict[str, Any]] = None

@router.post("/ops/actions/execute")
def actions_execute(
    q: ExecQuery,
    id: Optional[int] = Query(None),
    name: Optional[str] = Query(None),
    x_agent_token: Optional[str] = Header(None, alias="X-Agent-Token")
):
    if x_agent_token != AGENT_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not INTEGRATIONS_ENABLED:
        raise HTTPException(status_code=400, detail="Integrations disabled")

    act = None
    if id is not None:
        act = get_action_by_id(id)
    elif name:
        act = get_action_by_name(name)

    if not act or not act.get("enabled", True):
        raise HTTPException(status_code=404, detail="Action not found or disabled")

    jid = enqueue_job(act["id"], q.payload)
    return {"job_id": jid, "status": "queued"}

@router.get("/ops/jobs")
def ops_jobs(limit: int = 50):
    if not INTEGRATIONS_ENABLED:
        return {"jobs": []}
    return {"jobs": list_jobs(limit)}

@router.get("/ops/jobs/{job_id}")
def ops_job(job_id: int):
    if not INTEGRATIONS_ENABLED:
        raise HTTPException(status_code=400, detail="Integrations disabled")
    j = get_job(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Not found")
    return j
