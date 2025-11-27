#!/usr/bin/env bash
set -euo pipefail
cd /volume1/JENSEN/agents/my-agent

echo "[preflight] AST parse..."
python - <<'PY'
import ast, pathlib
ast.parse(pathlib.Path("app/main.py").read_text(encoding="utf-8"))
print("AST OK")
PY

echo "[preflight] .env checks..."
if [ ! -f .env ]; then
  echo "[preflight] ERROR: .env missing" >&2; exit 1
fi

# exactly one OPENAI_API_KEY and non-empty, near the top
cnt=$(grep -c '^OPENAI_API_KEY=' .env || true)
if [ "$cnt" -ne 1 ]; then
  echo "[preflight] ERROR: expected exactly one OPENAI_API_KEY line, found $cnt" >&2
  grep -n '^OPENAI_API_KEY=' .env || true
  exit 1
fi
if grep -q '^OPENAI_API_KEY=$' .env; then
  echo "[preflight] ERROR: OPENAI_API_KEY is empty" >&2; exit 1
fi

awk '
  BEGIN{nonc=0}
  /^[[:space:]]*#/ {next}
  {nonc++}
  /^OPENAI_API_KEY=/ { if (nonc>20) {print "[preflight] ERROR: OPENAI_API_KEY too far down (line " nonc ")"; exit 2} }
' .env
[ $? -ne 2 ] || exit 1

echo "[preflight] KEY POLICY OK"

# ---------- actions registry guard (JSON only) ----------
# Resolve container path from .env (default /app/data/actions.json)
cfg_line=$(grep -E '^ACTIONS_CONFIG_PATH=' .env | tail -n1 || true)
cfg="${cfg_line#ACTIONS_CONFIG_PATH=}"
[ -z "$cfg" ] && cfg="/app/data/actions.json"

# Map to host path
case "$cfg" in
  /app/*)  host="./${cfg#/app/}";;
  /volume1/*) host="$cfg";;        # if someone sets an absolute host path
  /*)      host="$cfg";;            # any other absolute path
  *)       host="./$cfg";;          # relative path
esac

if [ ! -f "$host" ]; then
  echo "[preflight] ERROR: ACTIONS_CONFIG_PATH missing: $cfg (host $host)" >&2
  exit 1
fi

python - "$host" <<'PY'
import sys, json, pathlib
p = pathlib.Path(sys.argv[1])
try:
    json.loads(p.read_text(encoding="utf-8"))
    print(f"[preflight] actions registry JSON OK: {p}")
except Exception as e:
    print(f"[preflight] ERROR: invalid JSON in {p}: {type(e).__name__}: {e}", file=sys.stderr)
    sys.exit(1)
PY

echo "[preflight] OK"

# --- ensure shared app network (idempotent) ---
docker network create jensen-net >/dev/null 2>&1 || true
docker network connect --alias jensen-agent-db jensen-net jensen-agent-db 2>/dev/null || true
docker network connect jensen-net jensen-agent 2>/dev/null || true

# --- prune compose-generated ghost entries like "abcdef123456_jensen-agent" ---
if command -v docker >/dev/null 2>&1; then
  ghosts=$(docker ps -a --format '{{.Names}}' | grep -E '^[0-9a-f]{12}_jensen-agent$' || true)
  if [ -n "$ghosts" ]; then
    echo "[preflight] pruning ghost containers:"
    echo "$ghosts" | while read -r g; do
      echo "  - $g"
      # detach from known networks (idempotent)
      docker network disconnect -f jensen-net "$g" 2>/dev/null || true
      docker network disconnect -f my-agent_default "$g" 2>/dev/null || true
      docker network disconnect -f bridge "$g" 2>/dev/null || true
      # remove the ghost row entirely so UI can't reference it
      docker rm -f "$g" >/dev/null 2>&1 || true
    done
  fi
fi
