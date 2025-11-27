# Jensen Agent — API Reference

Version: **1.2.1 (stable)**  
Model: **gpt-5**

This document summarizes all public endpoints exposed by the Jensen Agent service.

---

## Overview
A small FastAPI microservice exposing `/health`, `/version`, `/` (home), and `/chat`, protected by the `X-Agent-Token` header.

**Base URLs**
- **Local (on NAS):** `http://127.0.0.1:8000`
- **LAN:** `http://192.168.68.77:8000`
- **Reverse Proxy:** `https://ccity.synology.me`

**Docs & Schema**
- Swagger UI: `<BASE>/docs`
- OpenAPI JSON: `<BASE>/openapi.json`

**Auth**
- Header: `X-Agent-Token: <your-agent-token>` (example: `jensen4254`)
- Missing/invalid token → **401 Unauthorized**

**Rate limits**
- Requests/minute per token: **30**  
- Burst cap within 60s window: **60**  
- Exceeding limits → **429 Too Many Requests**

**Error envelope** (non‑2xx responses)
```json
{
  "error": {
    "code": "STRING_CODE",
    "message": "Human friendly message",
    "details": { "optional": "context" }
  }
}
```

---

## System Endpoints

### GET `/health`
Quick liveness probe.

**200 Response**
```json
{"ok": true}
```

**cURL**
```bash
curl -sS http://127.0.0.1:8000/health
```

---

### GET `/version`
Returns agent build information.

**200 Response**
```json
{
  "name": "Jensen Agent",
  "version": "1.2.1",
  "model": "gpt-5",
  "timeout_seconds": 20.0
}
```

**cURL**
```bash
curl -sS http://127.0.0.1:8000/version
```

---

### GET `/`
Minimal HTML home with links to `/health`, `/version`, and `/docs`.

**200 Response**
`text/html` page

---

## Chat Endpoint

### POST `/chat`
Create a simple assistant reply to a user message.

**Headers**
- `Content-Type: application/json`
- `X-Agent-Token: <token>`

**Request body**
```json
{
  "message": "hello"
}
```

**200 Response**
```json
{
  "message": "Hello! How can I assist you today?"
}
```

**Common status codes**
- `200 OK` – success
- `401 Unauthorized` – missing/invalid `X-Agent-Token`
- `422 Unprocessable Entity` – malformed JSON/body
- `429 Too Many Requests` – rate limit exceeded
- `500 Internal Server Error` – upstream/other error

**cURL (local)**
```bash
curl -sS -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -H 'X-Agent-Token: jensen4254' \
  -d '{"message":"hello"}'
```

**cURL (reverse proxy)**  
If your RP is HTTPS with a self‑signed cert, add `-k`:
```bash
curl -k -sS -X POST https://ccity.synology.me/chat \
  -H 'Content-Type: application/json' \
  -H 'X-Agent-Token: jensen4254' \
  -d '{"message":"hello"}'
```

---

## CORS
If CORS is enabled, allowed origins are set from `.env`:
```
ENABLE_CORS=yes
CORS_ORIGINS=https://ccity.synology.me,https://192.168.68.77
```

---

## Notes
- The service runs under Docker (container `jensen-agent`) and publishes port **8000** by default.
- Reverse proxy must forward to the container’s **8000** and present a valid certificate (or use `-k` for testing).
- Update `MODEL_NAME` / timeouts via `.env`; rebuild/restart to apply.

