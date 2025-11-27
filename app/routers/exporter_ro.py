from typing import Any, Dict, Optional
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel
import os
from app.integrations.exporter import run_export, dry_check

router = APIRouter()

def _require_token(h: Optional[str]):
    expected = os.getenv("AGENT_TOKEN","jensen4254")
    if not h or h != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

class ExportIn(BaseModel):
    payload: Dict[str, Any]

@router.get("/ops/export/test")
async def export_test():
    """Readiness view of exporter config (no writes)."""
    return {"checks": dry_check()}

@router.post("/ops/export/run")
async def export_run(body: ExportIn, x_agent_token: Optional[str] = Header(None, alias="X-Agent-Token")):
    _require_token(x_agent_token)
    results = await run_export(body.payload or {})
    return {"results": results}
