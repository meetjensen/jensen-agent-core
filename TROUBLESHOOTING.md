# Jensen Agent — TROUBLESHOOTING

This page lists the quickest checks & fixes we’ve needed while bringing the agent up.

---

## 1) Is the app up?
```bash
curl -sS http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:8000/version

## 2) Reverse Proxy check (Synology)

```bash
curl -k -sS https://ccity.synology.me/health
curl -k -sS https://ccity.synology.me/version
```

If health works locally but fails via RP:

- Confirm reverse proxy mapping → port 8000.
- Recheck DSM > Control Panel > Login Portal > Reverse Proxy.
- Verify certificate binding and HTTPS target.
- Add this to `.env` if not already:
  ```
  ENABLE_CORS=yes
  CORS_ORIGINS=https://ccity.synology.me,https://192.168.68.77
  ```

---

## 3) Container issues

### Check if it’s running:

```bash
docker ps --filter "name=jensen-agent"
```

### If it crashed or won’t start:

```bash
docker logs jensen-agent | tail -n 50
```

### To remove and rebuild fresh:

```bash
docker rm -f jensen-agent || true
docker compose up -d --build
```

---

## 4) Common errors & fixes

###  `ModuleNotFoundError: No module named 'app'

**Cause:** Wrong start path in Dockerfile
**Fix:**

```Dockerfile
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### ⚙️ `ValueError: could not convert string to float: '20  # ...'

**Fix:** Remove comments on same line in `.env`

```
REQUEST_TIMEOUT=20
RATE_LIMIT_RPM=30
RATE_BURST=60
```

---

###  `TypeError: unexpected keyword argument 'proxies'`

**Fix:** Use a clean OpenAI client:

```python
from openai import OpenAI
client = OpenAI(api_key=OPENAI_API_KEY, timeout=REQUEST_TIMEOUT)
```

---

###  Dependency mismatch (httpx, fastapi)

**Fix:** Pin known good versions:

```
httpx==0.27.2
fastapi==0.115.0
```

Then rebuild:

```bash
docker compose build --no-cache && docker compose up -d
```

---

###  Stray `EOF` or heredoc lines

**Fix:** Remove any `EOF` or `cat <<` artifacts left in `.sh` or `.md` files.\
They are only used for shell input, not for permanent file content.

---

## 5) Rebuild validation checklist

After editing any file:

```bash
cd /volume1/JENSEN/agents/my-agent
docker compose up -d --build
```

Then confirm:

```bash
docker ps --filter "name=jensen-agent"
curl -sS http://127.0.0.1:8000/health
curl -k -sS https://ccity.synology.me/version
```

✅ Expect HTTP 200 and version info.

---

## 6) Test the chat endpoint

```bash
curl -sS -X POST http://127.0.0.1:8000/chat
  -H 'Content-Type: application/json'
  -H 'X-Agent-Token: jensen4254'
  -d '{"message":"hello"}'
```

Expected output:

```json
{"message":"Hello there!"}
```

If it fails:

- Check your `.env` for a valid `OPENAI_API_KEY`.
- Check `docker logs jensen-agent` for upstream errors.
- Run:
  ```bash
  docker exec -it jensen-agent pip list | grep openai
  ```
  Ensure the client version matches expected OpenAI library version.

---

## 7) When "it used to work" checklist

| Check         | Expected                 | Command                                        |
| ------------- | ------------------------ | ---------------------------------------------- |
| Health        | `{"ok":true}`            | `curl -sS /health`                             |
| Version       | JSON with version, model | `curl -sS /version`                            |
| Container     | `Up`                     | `docker ps`                                    |
| Logs          | no `Traceback`           | `docker logs -n 60 jensen-agent`               |
| Reverse Proxy | OK                       | `curl -k -sS https://ccity.synology.me/health` |
| Env           | clean                    | `cat .env`                                     |
| Rate Limits   | sane values              | `grep RATE_ .env`                              |
| Dependencies  | stable                   | `httpx==0.27.2`, `fastapi==0.115.0`            |

---

## 8) Backup and restore checks

```bash
tar czf /volume1/JENSEN/agents/my-agent/backups/jensen-agent-$(date +%F-%H%M%S).tar.gz /volume1/JENSEN/agents/my-agent
```

Manual restore:

1. Place `.tar.gz` in `/volume1/JENSEN/agents/my-agent/backups`
2. Extract manually with:
   ```bash
   tar xzf jensen-agent-YYYY-MM-DD-HHMMSS.tar.gz -C /volume1/JENSEN/agents/
   ```
3. Then restart the container.

---

## 9) Contact info

Maintainer: SkyWalker@CloudCity
Last Updated: Oct 18, 2025
Version: 1.2.1 (stable)

