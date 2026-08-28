#!/usr/bin/env bash
set -e

set -a
source .env.local
set +a

ACTION="$1"

POSTGRES_DB="${POSTGRES_DB:-}"
DB_USER="$(whoami)"
PYTHON="./venv/bin/python"

if [ -z "$ACTION" ]; then
  echo "Usage: $0 [create_db|clear|drop|start_api|start_worker]"
  exit 1
fi

start_services() {
  sudo systemctl start postgresql
  sudo systemctl start redis
}

create_db() {
  start_services

if [ -z "$POSTGRES_DB" ]; then
  echo "POSTGRES_DB not set"
  exit 1
fi

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
}


drop_db() {
  [ -z "$POSTGRES_DB" ] && echo "POSTGRES_DB not set" && exit 1
  sudo -u postgres dropdb -f "$POSTGRES_DB"
}

start_api() {
  export ENV=local
  exec "$PYTHON" -m api.main
}

start_worker() {
  export ENV=local
  exec "$PYTHON" -m dramatiq api.prompts.tasks --processes 1 --threads 1
}

case "$ACTION" in
  create)
    create_db
    ;;
  clear)
    clear_db
    ;;
  drop)
    drop_db
    ;;
  api)
    start_services
    start_api
    ;;
  worker)
    start_services
    start_worker
    ;;
  *)
    echo "Usage: $0 [create|clear|drop|api|worker]"
    exit 1
    ;;
esac