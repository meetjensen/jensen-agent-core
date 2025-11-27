import os, json
from pathlib import Path
from typing import List, Dict, Any, Tuple

def _resolve_cfg() -> Tuple[Path, Path]:
    data_dir = Path(os.getenv("DATA_DIR", "/app/data"))
    # prefer env; fall back to actions.json in data dir
    raw = os.getenv("ACTIONS_CONFIG_PATH") or str(data_dir / "actions.json")
    # normalize container path -> Path
    p = Path(raw)
    # accept common mistake: pointing at host path; translate if it begins with /volume1/...
    if str(p).startswith("/volume1/"):
        # mapped /volume1/... -> /app/...
        p = Path("/app") / Path(str(p)).relative_to("/volume1/JENSEN/agents/my-agent")
    return p, data_dir

def load_actions() -> List[Dict[str, Any]]:
    cfg, _ = _resolve_cfg()
    if not cfg.exists():
        return []
    try:
        return json.loads(cfg.read_text(encoding="utf-8")) or []
    except Exception:
        return []
