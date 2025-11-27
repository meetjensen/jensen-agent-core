from fastapi import APIRouter, Query
from pathlib import Path
import json

router = APIRouter()

ARCH_META = Path("/app/data/archives.jsonl")

@router.get("/ops/archives")
def get_archives(limit: int = Query(50, ge=1, le=500)):
    if not ARCH_META.exists():
        return {"archives": []}
    rows = []
    try:
        with ARCH_META.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return {"archives": []}
    # newest first, bounded by limit
    return {"archives": list(reversed(rows[-limit:]))}

from fastapi.responses import HTMLResponse

@router.get("/ui/archives", response_class=HTMLResponse)
def archives_ui(limit: int = 50):
    data = get_archives(limit=limit)  # reuse the JSON function above
    rows = data.get("archives", [])
    html_rows = ""
    for r in rows:
        html_rows += f"""
          <tr>
            <td style="white-space:nowrap">{r.get('ts','')}</td>
            <td>{r.get('archive','')}</td>
            <td style="text-align:right">{r.get('size','')}</td>
            <td><code style="font-size:12px">{r.get('sha256','')}</code></td>
          </tr>
        """
    return f"""
      <html>
        <head>
          <title>Jensen Archives</title>
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <style>
            body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; padding: 24px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ border-bottom: 1px solid #eee; padding: 10px; font-size:14px; }}
            th {{ text-align: left; background:#f9fbff }}
          </style>
        </head>
        <body>
          <h2>Nightly Archives</h2>
          <p>Newest first. Limit={limit}.</p>
          <table>
            <thead>
              <tr><th>Time</th><th>Path</th><th style="text-align:right">Size (bytes)</th><th>SHA-256</th></tr>
            </thead>
            <tbody>
              {html_rows or '<tr><td colspan="4">No archives yet.</td></tr>'}
            </tbody>
          </table>
        </body>
      </html>
    """
