# Jensen Agent — API Reference

Version: **1.2.1 (stable)**  
Model: **gpt‑4o‑mini**

This document summarizes all endpoints for the Jensen Agent service.

---

## Overview
A FastAPI microservice exposing `/health`, `/version`, `/` (home), and `/chat`, secured by the `X-Agent-Token` header.

**Base URLs**
- Local: `http://127.0.0.1:8000`
- LAN: `http://192.168.68.77:8000`
- Reverse Proxy: `https://ccity.synology.me`

**Common Headers**
- `Content-Type: application/json` (for `POST /chat`)
- `X-Agent-Token: <your agent token>`

---

## System Endpoints

### `GET /health`
Check if the service is alive.

**Response**
```json
{"ok": true}
```

**Status Codes**
- `200 OK`

---

### `GET /version`
Return app metadata.

**Response**
```json
{
  "name": "Jensen Agent",
  "version": "1.2.1",
  "model": "gpt-5",
  "timeout_seconds": 20
}
```

**Status Codes**
- `200 OK`

---

### `GET /`
Simple HTML landing page with links to `/health`, `/version`, and Swagger docs at `/docs`.

**Status Codes**
- `200 OK`

---

## Chat Endpoint

### `POST /chat`
Send a single-turn chat message.

**Headers**
- `Content-Type: application/json`
- `X-Agent-Token: <your agent token>`

**Request Body**
```json
{ "message": "hello" }
```

**Successful Response**
```json
{ "message": "Hello! How can I assist you today?" }
```

**Error Envelope** (examples)
```json
{ "error": { "code": "unauthorized", "message": "Missing or invalid X-Agent-Token." } }
```
```json
{ "error": { "code": "bad_request", "message": "'message' is required." } }
```

**Status Codes**
- `200 OK` – success
- `400 Bad Request` – validation error
- `401 Unauthorized` – missing/invalid token
- `429 Too Many Requests` – rate limit exceeded
- `500 Internal Server Error` – unexpected failure

---

## Rate Limits & Timeouts
- Default rate limit: **30 RPM**, burst **60** (configured via `.env`).
- Request timeout: **20s** (also in `.env`).

---

## Curl Examples

**Health**
```bash
curl -sS http://127.0.0.1:8000/health
```

**Version**
```bash
curl -sS http://127.0.0.1:8000/version
```

**Chat (reverse proxy through HTTPS)**
```bash
curl -k -sS -X POST https://ccity.synology.me/chat \
  -H 'Content-Type: application/json' \
  -H 'X-Agent-Token: jensen4254' \
  -d '{"message":"hello"}'
```

---

## Notes
- API is documented live at `/docs` (Swagger UI) and `/redoc`.
- Keep your agent token secret. Do **not** include it in public bug reports or screenshots.
- If you change `.env` values, rebuild in **Container Manager → Project → Action → Build**.

