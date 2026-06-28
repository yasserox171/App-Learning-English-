#!/data/data/com.termux/files/usr/bin/bash
# One-shot backend setup for running on an Android phone via Termux.
# Uses SQLite (no PostgreSQL needed). Run from the backend/ directory:
#   bash termux_setup.sh
set -e

# Always operate from the directory this script lives in (the backend/ dir),
# so paths are stable regardless of where it was invoked from.
cd "$(dirname "$0")"
BACKEND_DIR="$(pwd)"

echo ">>> Installing system packages (python, git)..."
pkg update -y
pkg install -y python git

echo ">>> Creating virtual environment..."
python -m venv .venv
. .venv/bin/activate

echo ">>> Installing Python dependencies (Termux / SQLite)..."
pip install --upgrade pip
pip install -r requirements-termux.txt

echo ">>> Writing .env (SQLite, absolute DB path)..."
cat > .env <<EOF
DJANGO_SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(40))")
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,10.0.2.2
DATABASE_URL=sqlite:///${BACKEND_DIR}/db.sqlite3
EOF

echo ">>> Verifying configuration..."
python -c "import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings');django.setup();from django.conf import settings;assert 'sqlite' in settings.DATABASES['default']['ENGINE'], 'NOT using SQLite — .env not loaded';print('OK: using', settings.DATABASES['default']['ENGINE'])"

echo ">>> Applying migrations..."
python manage.py migrate

echo ">>> Seeding data (levels, templates, demo users, sample lesson)..."
python manage.py seed

echo ">>> Self-check (register endpoint)..."
python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
django.setup()
from rest_framework.test import APIClient
c = APIClient()
r = c.post('/api/v1/auth/register', {'email':'selfcheck@example.com','password':'pass12345','full_name':'Check'}, format='json', HTTP_HOST='localhost')
assert r.status_code == 201, f'register failed: {r.status_code} {r.content[:200]}'
from apps.users.models import User; User.objects.filter(email='selfcheck@example.com').delete()
print('OK: register works (201)')
"

echo ""
echo "=================================================================="
echo " Setup complete!"
echo " Start the server (run from this backend/ directory):"
echo "   cd $BACKEND_DIR"
echo "   . .venv/bin/activate && python manage.py runserver 127.0.0.1:8000"
echo ""
echo " Then open the app — it talks to http://127.0.0.1:8000/api/v1"
echo " Demo login:  student@lms.test / student12345"
echo "=================================================================="
