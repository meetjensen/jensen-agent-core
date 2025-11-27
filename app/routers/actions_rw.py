from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Optional
import os

from app.services.registry import load_actions
from app.services.job_runner import runner

router = APIRouter()

def _require_token(tok: Optional[str]):
    expected = os.getenv("AGENT_TOKEN", "jensen4254")
    if not tok or tok != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def _enabled() -> bool:
    return (os.getenv("INTEGRATIONS_ENABLED", "false").lower() == "true")

@router.get("/ops/actions")
def ops_actions_list():
    return JSONResponse(content=load_actions())

@router.post("/ops/actions/execute")
def ops_actions_execute(id: str, x_agent_token: Optional[str] = Header(None, alias="X-Agent-Token")):
    _require_token(x_agent_token)
    if not _enabled():
        raise HTTPException(status_code=403, detail="Integrations disabled")
    reg = {a.get("id"): a for a in load_actions()}
    act = reg.get(id)
    if not act:
        raise HTTPException(status_code=404, detail="Unknown action")
    if (act.get("type") or "").lower() != "http":
        raise HTTPException(status_code=400, detail=f"Unsupported action type: {act.get('type')}")
    jid = runner.enqueue({
        "type": "http",
        "method": (act.get("method") or "GET"),
        "url": act.get("url"),
        "headers": act.get("headers") or {},
        "body": act.get("body"),
    })
    return {"action_id": id, "job_id": jid, "status": "queued"}

# trailing-slash aliases (avoid 307s)
@router.get("/ops/actions/")
def ops_actions_list_slash():
    return ops_actions_list()
@router.post("/ops/actions/execute/")
def ops_actions_execute_slash(id: str, x_agent_token: Optional[str] = Header(None, alias="X-Agent-Token")):
    return ops_actions_execute(id=id, x_agent_token=x_agent_token)
