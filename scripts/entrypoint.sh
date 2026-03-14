#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
until python -c "
import socket, os, re
url = os.environ.get('DATABASE_URL', '')
# Extract host:port from any postgres URL format
m = re.search(r'@([^/:]+)(?::(\d+))?/', url)
if not m:
    raise SystemExit('Cannot parse DATABASE_URL')
host = m.group(1)
port = int(m.group(2) or 5432)
s = socket.socket()
s.settimeout(2)
s.connect((host, port))
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
