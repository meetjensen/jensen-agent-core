from fastapi import APIRouter, HTTPException, Header
from typing import Optional
import os

from app.services.job_runner import runner

router = APIRouter()

def _require_token(tok: Optional[str]):
    expected = os.getenv("AGENT_TOKEN", "jensen4254")
    if not tok or tok != expected:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/ops/jobs/enqueue")
def enqueue_job(x_agent_token: Optional[str] = Header(None, alias="X-Agent-Token"),
                type: str = "noop",
                sleep_ms: int = 100):
    _require_token(x_agent_token)
    jid = runner.enqueue({"type": type, "sleep_ms": sleep_ms})
    return {"job_id": jid, "status": "queued"}

@router.get("/ops/jobs")
def list_jobs(limit: int = 200):
    """Overrides the read-only placeholder with live queue state."""
    return runner.list(limit=limit)

@router.get("/ops/jobs/{job_id}")
def job_status(job_id: str):
    j = runner.get(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="job not found")
    return j

# --- trailing-slash aliases (avoid 307) ---
@router.get("/ops/jobs/")
def list_jobs_slash(limit: int = 200):
    return list_jobs(limit)

@router.get("/ops/jobs/{job_id}/")
def job_status_slash(job_id: str):
    return job_status(job_id)

@router.post("/ops/jobs/enqueue/")
def enqueue_job_slash(x_agent_token: str | None = Header(None, alias="X-Agent-Token"),
                      type: str = "noop", sleep_ms: int = 100):
    return enqueue_job(x_agent_token, type, sleep_ms)
