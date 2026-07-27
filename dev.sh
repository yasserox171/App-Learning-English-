#!/usr/bin/env bash
# Start the whole stack for local development: Django API + admin panel + web
# app. Ctrl-C stops all three.
#
#   ./dev.sh                 # sqlite, ports 8100 / 5173 / 3100
#   API_PORT=8000 ./dev.sh   # override any port
#
# Postgres instead of sqlite: export DATABASE_URL before running.
set -euo pipefail
cd "$(dirname "$0")"

API_PORT="${API_PORT:-8100}"
ADMIN_PORT="${ADMIN_PORT:-5173}"
WEB_PORT="${WEB_PORT:-3100}"
API_ORIGIN="http://127.0.0.1:${API_PORT}"
export DATABASE_URL="${DATABASE_URL:-sqlite:///test_db.sqlite3}"

if [ ! -x backend/.venv/bin/python ]; then
  echo "backend/.venv missing — run:"
  echo "  python3 -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements.txt"
  exit 1
fi

echo "▶ migrate + seed (idempotent)"
(cd backend && .venv/bin/python manage.py migrate --no-input -v0 \
              && .venv/bin/python manage.py seed)

pids=()
cleanup() { echo; echo "▶ stopping…"; kill "${pids[@]}" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

echo "▶ API      → ${API_ORIGIN}"
(cd backend && .venv/bin/python manage.py runserver "127.0.0.1:${API_PORT}") &
pids+=($!)

if [ -d admin/node_modules ]; then
  echo "▶ admin    → http://127.0.0.1:${ADMIN_PORT}"
  (cd admin && PORT="$ADMIN_PORT" API_ORIGIN="$API_ORIGIN" npm run dev >/dev/null) &
  pids+=($!)
else
  echo "  (skipping admin — run 'npm install' in admin/)"
fi

if [ -d web/node_modules ]; then
  echo "▶ web      → http://127.0.0.1:${WEB_PORT}"
  (cd web && API_ORIGIN="$API_ORIGIN" npx next dev -p "$WEB_PORT" >/dev/null) &
  pids+=($!)
else
  echo "  (skipping web — run 'npm install' in web/)"
fi

echo
echo "admin login: admin@focus.test / adminpanel12345"
echo "student login: student@lms.test / student12345"
echo "Ctrl-C to stop."
wait
