#!/usr/bin/env sh
set -e

# Rewrite Render's provided DATABASE_URL (postgresql://) into the asyncpg dialect
# the app expects (postgresql+asyncpg://). Derive DATABASE_SYNC_URL from it.
if [ -n "${DATABASE_URL:-}" ] && ! printf '%s' "$DATABASE_URL" | grep -Eq '^postgres(ql)?\+asyncpg://'; then
  DATABASE_URL=$(printf '%s' "$DATABASE_URL" | sed 's#^postgresql://#postgresql+asyncpg://#; s#^postgres://#postgresql+asyncpg://#')
  export DATABASE_URL
fi
if [ -z "${DATABASE_SYNC_URL:-}" ] && [ -n "${DATABASE_URL:-}" ]; then
  DATABASE_SYNC_URL=$(printf '%s' "$DATABASE_URL" | sed 's#^postgresql+asyncpg://#postgresql://#')
  export DATABASE_SYNC_URL
fi

# DNS preflight: new instances can hit transient resolver failures; resolve the
# database host (and a control host) with retries and log the outcome.
if [ -n "${DATABASE_URL:-}" ]; then
  DB_HOST=$(printf '%s' "$DATABASE_URL" | sed -E 's#^[a-z+]+://[^@]*@([^:/]+).*#\1#')
  for HOST in "$DB_HOST" "api.telegram.org"; do
    n=0
    until getent ahostsv4 "$HOST" >/dev/null 2>&1; do
      n=$((n + 1))
      if [ "$n" -ge 10 ]; then
        echo "DNS_PREFLIGHT_FAIL host=$HOST after $n attempts"
        exit 1
      fi
      echo "DNS_PREFLIGHT_RETRY host=$HOST attempt=$n"
      sleep 5
    done
    echo "DNS_PREFLIGHT_OK host=$HOST ips=$(getent ahostsv4 "$HOST" | awk '{print $1}' | sort -u | tr '\n' ',')"
  done
fi

exec "$@"
