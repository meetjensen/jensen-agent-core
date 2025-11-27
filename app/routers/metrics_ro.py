from fastapi import APIRouter, Response
import os
from app.services.job_runner import runner

router = APIRouter()

def _esc(v: str) -> str:
    return v.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')

@router.get("/metrics")
def metrics():
    jobs = runner.snapshot()
    counts = {"queued":0,"running":0,"done":0,"error":0}
    for j in jobs:
        counts[j.get("status","queued")] = counts.get(j.get("status","queued"),0) + 1
    ver = os.getenv("APP_VERSION","dev")
    out = []
    out += [
        '# HELP jensen_info Build info.',
        '# TYPE jensen_info gauge',
        f'jensen_info{{version="{_esc(ver)}"}} 1',
        '# HELP jensen_jobs_total Jobs currently tracked.',
        '# TYPE jensen_jobs_total gauge',
        f'jensen_jobs_total {len(jobs)}',
        '# HELP jensen_jobs_status Jobs by status.',
        '# TYPE jensen_jobs_status gauge',
    ]
    for k,v in counts.items():
        out.append(f'jensen_jobs_status{{status="{k}"}} {v}')
    return Response(content="\n".join(out) + "\n", media_type="text/plain; version=0.0.4")
