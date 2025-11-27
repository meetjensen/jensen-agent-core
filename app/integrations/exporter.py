import os, json, time, hashlib
from typing import Dict, Any, List

ENABLED = os.getenv("EXPORT_ENABLED","false").lower() == "true"
TARGETS = [t.strip() for t in os.getenv("EXPORT_TARGETS","").split(",") if t.strip()]

# HTTP target
EXPORT_HTTP_URL = os.getenv("EXPORT_HTTP_URL","")  # optional; if blank, HTTP target is skipped

# S3 target
AWS_ACCESS_KEY_ID     = os.getenv("AWS_ACCESS_KEY_ID","")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY","")
AWS_REGION            = os.getenv("AWS_REGION","us-west-2")
S3_BUCKET             = os.getenv("S3_BUCKET","")
S3_PREFIX             = os.getenv("S3_PREFIX","exports/")

def _result(name: str, ok: bool, detail: str, extra: Dict[str,Any]=None) -> Dict[str,Any]:
    d = {"target": name, "ok": ok, "detail": detail}
    if extra: d.update(extra)
    return d

def _now_key() -> str:
    ts = time.strftime("%Y%m%d-%H%M%S")
    return f"{S3_PREFIX.rstrip('/')}/export_{ts}.json"

async def send_http(payload: Dict[str,Any]) -> Dict[str,Any]:
    if not EXPORT_HTTP_URL:
        return _result("http", False, "EXPORT_HTTP_URL not set")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(EXPORT_HTTP_URL, json=payload)
            return _result("http", r.status_code < 300, f"status={r.status_code}", {"status_code": r.status_code})
    except Exception as e:
        return _result("http", False, f"error={type(e).__name__}:{e}")

def send_s3(payload: Dict[str,Any]) -> Dict[str,Any]:
    if not (AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and S3_BUCKET):
        return _result("s3", False, "missing S3 creds or bucket")
    try:
        import boto3
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        key  = _now_key()
        s3 = boto3.client("s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION)
        r = s3.put_object(Bucket=S3_BUCKET, Key=key, Body=body, ContentType="application/json")
        etag = r.get("ETag","").strip('"')
        sha256 = hashlib.sha256(body).hexdigest()
        # optional checksum sidecar
        s3.put_object(Bucket=S3_BUCKET, Key=key + ".sha256", Body=(sha256+"\n").encode("utf-8"), ContentType="text/plain")
        return _result("s3", True, "uploaded", {"key": key, "etag": etag, "sha256": sha256})
    except Exception as e:
        return _result("s3", False, f"error={type(e).__name__}:{e}")

async def run_export(payload: Dict[str,Any]) -> List[Dict[str,Any]]:
    if not ENABLED:
        return [_result("system", False, "EXPORT_ENABLED=false")]
    results: List[Dict[str,Any]] = []
    for t in TARGETS:
        if t == "http":
            results.append(await send_http(payload))
        elif t == "s3":
            results.append(send_s3(payload))
        else:
            results.append(_result(t, False, "unsupported target"))
    return results

def dry_check() -> List[Dict[str,Any]]:
    out = []
    out.append(_result("enabled", ENABLED, f"targets={','.join(TARGETS) if TARGETS else '(none)'}"))
    out.append(_result("http", bool(EXPORT_HTTP_URL), f"url={'set' if EXPORT_HTTP_URL else 'missing'}"))
    s3_missing = not (AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and S3_BUCKET)
    out.append(_result("s3", not s3_missing, "creds/bucket ok" if not s3_missing else "missing cfg"))
    return out
