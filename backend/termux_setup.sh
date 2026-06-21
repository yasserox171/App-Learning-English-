#!/data/data/com.termux/files/usr/bin/bash
# One-shot backend setup for running on an Android phone via Termux.
# Uses SQLite (no PostgreSQL needed). Run from the backend/ directory:
#   bash termux_setup.sh
set -e

echo ">>> Installing system packages (python, git)..."
pkg update -y
pkg install -y python git

echo ">>> Creating virtual environment..."
python -m venv .venv
. .venv/bin/activate

echo ">>> Installing Python dependencies (Termux / SQLite)..."
pip install --upgrade pip
pip install -r requirements-termux.txt

echo ">>> Writing .env (SQLite)..."
cat > .env <<EOF
DJANGO_SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(40))")
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_URL=sqlite:///db.sqlite3
EOF

echo ">>> Applying migrations..."
python manage.py migrate

echo ">>> Seeding data (levels, templates, demo users, sample lesson)..."
python manage.py seed

echo ""
echo "=================================================================="
echo " Setup complete!"
echo " Start the server with:"
echo "   . .venv/bin/activate && python manage.py runserver 127.0.0.1:8000"
echo ""
echo " Then open the app — it talks to http://127.0.0.1:8000/api/v1"
echo " Demo login:  student@lms.test / student12345"
echo "=================================================================="
