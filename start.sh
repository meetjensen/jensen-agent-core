#!/bin/sh
set -e

echo ">>> Loading environment from /app/.env"
if [ -f /app/.env ]; then
  tmp="/tmp/.env.clean"
  # Strip CRs
  awk '{ sub("\r$", ""); print }' /app/.env > "$tmp"
  # Generate an export script for valid KEY=VALUE lines only
  awk -F= '
    /^[ \t]*($|#)/{ next }                   # skip blank lines and comments
    {
      k=$1; v=substr($0, index($0,"=")+1)
      gsub(/^[ \t]+|[ \t]+$/, "", k)         # trim spaces around key
      gsub(/^[ \t]+|[ \t]+$/, "", v)         # trim spaces around value ends
      sub(/^[\"\047]+/, "", v); sub(/[\"\047]+$/, "", v)  # strip wrapping quotes
      gsub(/\r$/, "", v)
      if (k ~ /^[A-Za-z_][A-Za-z0-9_]*$/) {
        printf("export %s=%s\n", k, v)
      }
    }
  ' "$tmp" > /tmp/export_env.sh

  # shellcheck disable=SC1091
  . /tmp/export_env.sh
fi

# Ensure /app on PYTHONPATH
case ":$PYTHONPATH:" in
  *:/app:*) : ;;
  *) export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}/app" ;;
esac

echo ">>> Environment loaded, starting FastAPI..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
