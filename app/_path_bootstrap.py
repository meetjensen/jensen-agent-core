from pathlib import Path
import os

APP_DIR = Path(__file__).resolve().parent

def _pick(candidates):
    for d in candidates:
        if d.exists():
            return d
    return candidates[0]

TEMPLATES_DIR = _pick([APP_DIR / "templates", Path("/app/templates"), Path("/app/app/templates")])
STATIC_DIR    = _pick([APP_DIR / "static",    Path("/app/static"),    Path("/app/app/static")])

# Make legacy absolute paths always resolve (safe, idempotent)
try:
    if not Path("/app/templates").exists():
        os.symlink(str(TEMPLATES_DIR), "/app/templates")
except FileExistsError:
    pass
except Exception:
    pass

try:
    if not Path("/app/static").exists():
        os.symlink(str(STATIC_DIR), "/app/static")
except FileExistsError:
    pass
except Exception:
    pass
