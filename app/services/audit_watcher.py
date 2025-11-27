import os, json, time, threading
from pathlib import Path
from typing import Dict, Any

DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))
AUDIT = Path(os.getenv("ACTIONS_AUDIT_PATH", str(DATA_DIR / "actions.db.jsonl")))

# normalize host path -> container path (safety)
_host = "/volume1/JENSEN/agents/my-agent"
s = str(AUDIT)
if s.startswith(_host):
    AUDIT = Path("/app" + s[len(_host):])

_started = False
_lock = threading.Lock()
_seen: Dict[str, str] = {}  # job_id -> last_status

def _append(rec: Dict[str, Any]):
    try:
        AUDIT.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass

def _tick():
    # late-import to avoid circular refs
    from app.services.job_runner import runner
    while True:
        try:
            # prefer in-memory snapshot; fall back to file
            try:
                jobs = runner.snapshot()
            except Exception:
                try:
                    p = DATA_DIR / "jobs.json"
                    jobs = json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    jobs = []

            now = int(time.time())
            for j in jobs:
                jid = j.get("id")
                if not jid:
                    continue
                st  = j.get("status", "queued")
                last = _seen.get(jid)

                # first sighting: write queued, and also write the current terminal state
                if last is None:
                    _append({"ts": int(j.get("created", now)), "event":"queued", "job_id": jid,
                             "status":"queued", "payload": j.get("payload",{})})
                    if st == "running":
                        _append({"ts": int(j.get("started", now)), "event":"started", "job_id": jid,
                                 "status":"running", "payload": j.get("payload",{})})
                    elif st == "done":
                        code = (j.get("result") or {}).get("code")
                        _append({"ts": int(j.get("ended", now)), "event":"done", "job_id": jid,
                                 "status":"done", "result":{"code": code}, "payload": j.get("payload",{})})
                    elif st == "error":
                        _append({"ts": int(j.get("ended", now)), "event":"error", "job_id": jid,
                                 "status":"error", "error": j.get("error"), "payload": j.get("payload",{})})

                # transitions after first sighting
                elif last != st:
                    if st == "running":
                        _append({"ts": int(j.get("started", now)), "event":"started", "job_id": jid,
                                 "status":"running", "payload": j.get("payload",{})})
                    elif st == "done":
                        code = (j.get("result") or {}).get("code")
                        _append({"ts": int(j.get("ended", now)), "event":"done", "job_id": jid,
                                 "status":"done", "result":{"code": code}, "payload": j.get("payload",{})})
                    elif st == "error":
                        _append({"ts": int(j.get("ended", now)), "event":"error", "job_id": jid,
                                 "status":"error", "error": j.get("error"), "payload": j.get("payload",{})})

                _seen[jid] = st
        except Exception:
            pass
        time.sleep(0.5)

def start():
    global _started
    with _lock:
        if _started: return
        t = threading.Thread(target=_tick, name="audit-watcher", daemon=True)
        t.start()
        _started = True
