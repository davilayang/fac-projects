#!/bin/sh
set -e

echo "Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."
python - <<'EOF'
import socket, time, os, sys
host = os.environ.get("DB_HOST", "localhost")
port = int(os.environ.get("DB_PORT", 5432))
for i in range(30):
    try:
        s = socket.create_connection((host, port), timeout=1)
        s.close()
        print("PostgreSQL is ready.")
        sys.exit(0)
    except OSError:
        print(f"  attempt {i + 1}/30 — retrying in 1s")
        time.sleep(1)
print("PostgreSQL did not become ready in time.")
sys.exit(1)
EOF

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting application..."
exec "$@"
