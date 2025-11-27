import asyncio, os, time, uuid, json, ssl
from pathlib import Path
from typing import Dict, Any, Optional
from urllib import request as _rq, error as _err, parse as _parse

DATA_DIR       = Path(os.getenv("DATA_DIR", "/app/data"))
JOBS_JSON      = DATA_DIR / "jobs.json"
AUDIT_JSONL    = DATA_DIR / "actions.db.jsonl"

MAX_CONCURRENCY     = int(os.getenv("MAX_CONCURRENCY", "2"))
REQUEST_TIMEOUT     = int(os.getenv("REQUEST_TIMEOUT", "30"))
MAX_RETRIES         = int(os.getenv("MAX_RETRIES", "2"))
CIRCUIT_OPEN_AFTER  = int(os.getenv("CIRCUIT_OPEN_AFTER", "4"))
CIRCUIT_COOLDOWN    = int(os.getenv("CIRCUIT_COOLDOWN_SEC", "60"))

class CircuitOpen(Exception): ...

class JobRunner:
    def __init__(self):
        self.q: asyncio.Queue = asyncio.Queue()
        self.sem = asyncio.Semaphore(MAX_CONCURRENCY)
        self.jobs: Dict[str, Dict[str, Any]] = {}
        # circuit state per host
        self.circuit: Dict[str, Dict[str, Any]] = {}
        self._loop_task: Optional[asyncio.Task] = None
        self._load()

    # ---------- persistence ----------
    def _load(self):
        try:
            if JOBS_JSON.exists():
                data = json.loads(JOBS_JSON.read_text(encoding="utf-8"))
                for j in data.get("jobs", []):
                    if j.get("status") == "running":
                        j["status"] = "queued"
                    self.jobs[j["id"]] = j
        except Exception:
            pass

    def _persist(self):
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            JOBS_JSON.write_text(
                json.dumps({"jobs": list(self.jobs.values())}, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception:
            pass

    def _audit(self, record: Dict[str, Any]):
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with AUDIT_JSONL.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass

    # ---------- public API ----------
    async def start(self):
        if self._loop_task is None or self._loop_task.done():
            self._loop_task = asyncio.create_task(self._loop())

    async def _loop(self):
        while True:
            payload = await self.q.get()
            asyncio.create_task(self._run(payload))

    def enqueue(self, payload: Dict[str, Any]) -> str:
        jid = str(uuid.uuid4())
        job = {"id": jid, "status": "queued", "created": time.time(), "payload": payload}
        self.jobs[jid] = job
        self._persist()
        self.q.put_nowait({"id": jid, **payload})
        return jid

    def list(self, limit: int = 200) -> Dict[str, Any]:
        items = list(self.jobs.values())
        items.sort(key=lambda j: j.get("created", 0), reverse=True)
        return {"jobs": items[:max(1, min(limit, 1000))]}

    def get(self, jid: str) -> Optional[Dict[str, Any]]:
        return self.jobs.get(jid)

    # ---------- runners ----------
    async def _run(self, payload: Dict[str, Any]):
        jid = payload["id"]
        async with self.sem:
            job = self.jobs.get(jid) or {"id": jid}
            job.update(status="running", started=time.time())
            self.jobs[jid] = job
            self._persist()
            t0 = time.time()
            audit = {"ts": t0, "job_id": jid, "payload": payload, "type": payload.get("type", "noop")}
            try:
                typ = payload.get("type", "noop")
                if typ == "noop":
                    ms = int(payload.get("sleep_ms", 100))
                    await asyncio.sleep(max(0, ms) / 1000)
                    result = {"msg": "slept", "sleep_ms": ms}
                elif typ == "http":
                    result = await self._run_http(payload)
                else:
                    result = {"msg": "unknown type", "type": typ}
                job["result"] = result
                job["status"] = "done"
                audit.update(status="done", result=result)
            except Exception as e:
                job["status"] = "error"
                job["error"] = f"{type(e).__name__}: {e}"
                audit.update(status="error", error=job["error"])
            finally:
                job["ended"] = time.time()
                job["duration_ms"] = int((job["ended"] - t0) * 1000)
                self.jobs[jid] = job
                self._audit(audit)
                self._persist()

    async def _run_http(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = payload.get("url"); method = (payload.get("method") or "GET").upper()
        headers = payload.get("headers") or {}
        body = payload.get("body")
        if not url or not url.startswith(("http://", "https://")):
            raise ValueError("invalid url")

        host = _parse.urlparse(url).hostname or "unknown"
        now = time.time()
        c = self.circuit.get(host) or {"fail": 0, "open_at": 0}
        # circuit gate
        if c.get("open_at", 0) and now - c["open_at"] < CIRCUIT_COOLDOWN:
            raise CircuitOpen(f"circuit open for {host}")

        # blocking I/O via thread so we don't block event loop
        def _do():
            req = _rq.Request(url=url, method=method)
            for k, v in headers.items():
                req.add_header(k, v)
            data = None
            if body is not None:
                if isinstance(body, (dict, list)):
                    btxt = json.dumps(body).encode("utf-8")
                    req.add_header("Content-Type", "application/json")
                    data = btxt
                elif isinstance(body, str):
                    data = body.encode("utf-8")
                elif isinstance(body, (bytes, bytearray)):
                    data = body
            ctx = ssl.create_default_context()
            last_exc = None
            for attempt in range(MAX_RETRIES + 1):
                try:
                    with _rq.urlopen(req, data=data, timeout=REQUEST_TIMEOUT, context=ctx) as resp:
                        code = resp.getcode()
                        text = resp.read(2048).decode("utf-8", errors="replace")
                        # success => reset circuit
                        self.circuit[host] = {"fail": 0, "open_at": 0}
                        return {"code": code, "body_preview": text}
                except (_err.HTTPError, _err.URLError, TimeoutError) as e:
                    last_exc = e
                    time.sleep(min(1.0 * (attempt + 1), 3.0))
            # mark failure and maybe open circuit
            c["fail"] = c.get("fail", 0) + 1
            if c["fail"] >= CIRCUIT_OPEN_AFTER:
                c["open_at"] = time.time()
            self.circuit[host] = c
            raise RuntimeError(f"http error after retries: {last_exc}")

        return await asyncio.to_thread(_do)

# singleton
runner = JobRunner()

# --- compat patch: ensure JobRunner.snapshot exists (for /metrics) ---
try:
    JobRunner  # type: ignore[name-defined]
    if not hasattr(JobRunner, "snapshot"):
        def _snapshot(self):
            with self.jobs_lock:
                return list(self.jobs.values())
        JobRunner.snapshot = _snapshot  # type: ignore[attr-defined]
except Exception:
    pass
# --- end compat patch ---

# --- compat patch v2: lock-free snapshot for /metrics & /ops/jobs ---
try:
    JobRunner  # type: ignore[name-defined]
    def _safe_snapshot(self):
        # 1) Try in-memory jobs (dict or list)
        jobs = getattr(self, "jobs", None)
        if isinstance(jobs, dict):
            try:
                return list(jobs.values())
            except Exception:
                pass
        if isinstance(jobs, list):
            return list(jobs)
        # 2) Fallback to on-disk jobs.json
        try:
            import os, json
            from pathlib import Path
            DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))
            p = DATA_DIR / "jobs.json"
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return []
    # override any previous monkey-patch
    JobRunner.snapshot = _safe_snapshot  # type: ignore[attr-defined]
except Exception:
    pass
# --- end compat patch v2 ---
