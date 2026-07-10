#!/bin/bash

# GovAssist Ethiopia - Integration Health Check Script

echo "Checking Service Connectivity..."

# 1. Check Postgres
if command -v pg_isready > /dev/null; then
  pg_isready -h localhost -p 5432 && echo "✅ Postgres is reachable" || echo "❌ Postgres is NOT reachable"
else
  echo "⚠️ pg_isready not installed, skipping Postgres check"
fi

# 2. Check Redis
if command -v redis-cli > /dev/null; then
  redis-cli -h localhost -p 6379 ping | grep PONG > /dev/null && echo "✅ Redis is reachable" || echo "❌ Redis is NOT reachable"
else
  echo "⚠️ redis-cli not installed, skipping Redis check"
fi

# 3. Check Minio
curl -s -o /dev/null -w "%{http_code}" http://localhost:9000/minio/health/live | grep 200 > /dev/null && echo "✅ Minio is reachable" || echo "❌ Minio is NOT reachable"

# 4. Check Weaviate
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/v1/.well-known/live | grep 200 > /dev/null && echo "✅ Weaviate is reachable" || echo "❌ Weaviate is NOT reachable"

# 5. Check Backend API
curl -s -o /dev/null -w "%{http_code}" http://localhost:3001/playbooks | grep -E "200|401" > /dev/null && echo "✅ Backend API is reachable" || echo "❌ Backend API is NOT reachable"

# Summary
echo "Health check complete."
