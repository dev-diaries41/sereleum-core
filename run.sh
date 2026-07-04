#!/usr/bin/env bash
set -e

set -a
source .env.local
set +a

sudo systemctl start postgresql
sudo systemctl start redis

if [ -z "$POSTGRES_DB" ]; then
  echo "POSTGRES_DB not set"
  exit 1
fi

DB_USER="$(whoami)"

# create db if missing
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${POSTGRES_DB}'" | grep -q 1 \
  || sudo -u postgres createdb "$POSTGRES_DB"

sudo -u postgres psql -d "$POSTGRES_DB" -c "CREATE EXTENSION IF NOT EXISTS vector;" || true

# fix schema permissions for local OS user
sudo -u postgres psql "$POSTGRES_DB" <<EOF
ALTER SCHEMA public OWNER TO postgres;
GRANT USAGE, CREATE ON SCHEMA public TO ${DB_USER};
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ${DB_USER};
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ${DB_USER};
EOF

if [ -f db/init.sql ]; then
  sudo -u postgres psql "$POSTGRES_DB" < db/init.sql
fi

export ENV=local

PYTHON=./venv/bin/python

if [ "$1" = "worker" ]; then
  exec "$PYTHON" -m dramatiq api.prompts.tasks --processes 1 --threads 1
else
  exec "$PYTHON" -m api.main
fi