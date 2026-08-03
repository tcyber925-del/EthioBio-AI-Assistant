#!/usr/bin/env sh
set -e

# Rewrite Render's provided DATABASE_URL (postgresql://) into the asyncpg dialect
# the app expects (postgresql+asyncpg://). Derive DATABASE_SYNC_URL from it.
if [ -n "${DATABASE_URL:-}" ] && ! printf '%s' "$DATABASE_URL" | grep -q '+asyncpg'; then
  DATABASE_URL=$(printf '%s' "$DATABASE_URL" | sed 's#^postgresql://#postgresql+asyncpg://#; s#^postgres://#postgresql+asyncpg://#')
  export DATABASE_URL
fi
if [ -z "${DATABASE_SYNC_URL:-}" ] && [ -n "${DATABASE_URL:-}" ]; then
  DATABASE_SYNC_URL=$(printf '%s' "$DATABASE_URL" | sed 's#^postgresql+asyncpg://#postgresql://#')
  export DATABASE_SYNC_URL
fi

exec "$@"
