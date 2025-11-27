from fastapi import APIRouter, Query, Response
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from pathlib import Path
import os, time

router = APIRouter()

HOST_ROOT = "/volume1/JENSEN/agents/my-agent"

def _norm(s: str) -> str:
    if s and s.startswith(HOST_ROOT):
        return "/app" + s[len(HOST_ROOT):]
    return s

def _audit_path():
    cands = []
    p = os.getenv("ACTIONS_AUDIT_PATH", "").strip()
    if p: cands.append(_norm(p))
    cands += ["/app/data/actions/audit.log", "/app/data/actions.db.jsonl"]
    tried = []
    for s in cands:
        if not s: continue
        tried.append(s)
        pth = Path(s)
        if pth.exists() and pth.is_file():
            return pth, tried
    return None, tried

# ----- Streaming variant (original) -----
@router.head("/ops/export/audit")
def export_audit_head(download: bool = Query(True)):
    p, tried = _audit_path()
    if not p:
        return JSONResponse(status_code=404, content={"detail": "audit not found", "tried": tried})
    size = p.stat().st_size
    headers = {
        "Content-Type": "application/x-ndjson",
        "Content-Length": str(size),
        "X-Audit-Path": str(p),
    }
    if download:
        headers["Content-Disposition"] = f'attachment; filename="actions_audit_{int(time.time())}.ndjson"'
    return Response(status_code=200, headers=headers)

@router.get("/ops/export/audit")
def export_audit(download: bool = Query(True)):
    p, tried = _audit_path()
    if not p:
        return JSONResponse(status_code=404, content={"detail": "audit not found", "tried": tried})
    def _iter():
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                yield chunk
    headers = {"X-Audit-Path": str(p)}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="actions_audit_{int(time.time())}.ndjson"'
    return StreamingResponse(_iter(), media_type="application/x-ndjson", headers=headers)

# ----- File (non-streaming) variant: nginx-friendly -----
@router.head("/ops/export/audit/file")
def export_audit_file_head():
    p, tried = _audit_path()
    if not p:
        return JSONResponse(status_code=404, content={"detail": "audit not found", "tried": tried})
    size = p.stat().st_size
    headers = {
        "Content-Type": "application/x-ndjson",
        "Content-Length": str(size),
        "X-Audit-Path": str(p),
        "Content-Disposition": f'attachment; filename="actions_audit_{int(time.time())}.ndjson"'
    }
    return Response(status_code=200, headers=headers)

@router.get("/ops/export/audit/file")
def export_audit_file():
    p, tried = _audit_path()
    if not p:
        return JSONResponse(status_code=404, content={"detail": "audit not found", "tried": tried})
    # FileResponse sets Content-Length and plays nice with proxies
    return FileResponse(
        path=str(p),
        media_type="application/x-ndjson",
        filename=f"actions_audit_{int(time.time())}.ndjson"
    )
