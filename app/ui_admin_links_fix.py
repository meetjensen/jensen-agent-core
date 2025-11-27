from fastapi.responses import HTMLResponse
from pathlib import Path

def get_admin_links_page():
    # Try common locations (first one that exists wins)
    candidates = [
        Path("/app/app/templates/admin_links.html"),                      # image layout: COPY app /app/app
        Path("/app/templates/admin_links.html"),                          # alt layout
        Path("/volume1/JENSEN/agents/my-agent/app/templates/admin_links.html"),  # host mount
    ]
    for p in candidates:
        if p.exists():
            return HTMLResponse(p.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Admin Links Missing</h1>", status_code=500)
