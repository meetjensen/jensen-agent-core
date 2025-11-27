from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pathlib import Path
import os, json

router = APIRouter()

DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))
AUDIT = Path(os.getenv("ACTIONS_AUDIT_PATH", str(DATA_DIR / "actions.db.jsonl")))

@router.get("/ops/actions/audit")
def audit_tail(limit: int = Query(100, ge=1, le=1000)):
    if not AUDIT.exists():
        return JSONResponse(content={"audit": []})
    try:
        lines = AUDIT.read_text(encoding="utf-8").splitlines()[-limit:]
        out = []
        for ln in lines:
            try:
                out.append(json.loads(ln))
            except Exception:
                pass
        return JSONResponse(content={"audit": out})
    except Exception:
        return JSONResponse(content={"audit": []})

# --- normalize host path → container path for read-side too ---
def _norm_audit_path(p):
    s = str(p)
    host = "/volume1/JENSEN/agents/my-agent"
    if s.startswith(host):
        from pathlib import Path
        return Path("/app" + s[len(host):])
    return p
AUDIT = _norm_audit_path(AUDIT)
