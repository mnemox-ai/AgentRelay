#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
until python -c "
import socket, sys, os
url = os.environ.get('DATABASE_URL', '')
# Extract host:port from postgresql+asyncpg://user:pass@host:port/db
parts = url.split('@')[-1].split('/')[0]
host, port = parts.split(':')
s = socket.socket()
s.settimeout(2)
s.connect((host, int(port)))
s.close()
" 2>/dev/null; do
  echo "  PostgreSQL not ready, retrying in 2s..."
  sleep 2
done
echo "PostgreSQL is up."

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting uvicorn..."
exec uvicorn agentrelay.api.app:app --host 0.0.0.0 --port 8000
