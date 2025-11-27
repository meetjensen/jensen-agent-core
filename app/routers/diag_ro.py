from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.services.registry import _resolve_cfg
import os, json

router = APIRouter()

@router.get("/__diag/actions")
def diag_actions():
    p, data_dir = _resolve_cfg()
    env = {
        "ACTIONS_CONFIG_PATH": os.getenv("ACTIONS_CONFIG_PATH"),
        "DATA_DIR": os.getenv("DATA_DIR"),
        "INTEGRATIONS_ENABLED": os.getenv("INTEGRATIONS_ENABLED"),
    }
    info = {
        "env": env,
        "resolved_path": str(p),
        "exists": p.exists(),
        "dir": str(data_dir),
        "size": (p.stat().st_size if p.exists() else 0),
        "mtime": (int(p.stat().st_mtime) if p.exists() else None),
        "preview": None,
    }
    if p.exists():
        try:
            txt = p.read_text(encoding="utf-8")
            info["preview"] = txt[:240]
            json.loads(txt); info["json_ok"] = True
        except Exception as e:
            info["json_ok"] = False
            info["json_err"] = f"{type(e).__name__}: {e}"
    return JSONResponse(content=info)
