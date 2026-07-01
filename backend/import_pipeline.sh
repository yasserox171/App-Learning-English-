#!/data/data/com.termux/files/usr/bin/bash
# Import ALL pipeline-generated lessons + media into the LMS in one shot.
#
# Expects the focus_pipeline layout:
#   <CONTENT_DIR>/<LEVEL>/unit_XX_name/lesson.json   (array of lessons)
#   <CONTENT_DIR>/<LEVEL>/unit_XX_name/media/{images,audio,video}/...
#
# Each unit's media is copied to a UNIQUE destination
# (media/imported/<LEVEL>/<unit>) so identical filenames across units never
# collide, and the relative paths inside lesson.json resolve correctly.
#
# Usage (run from the backend/ directory):
#   bash import_pipeline.sh [CONTENT_DIR] [MEDIA_BASE_URL] [--no-replace]
#
# Defaults:
#   CONTENT_DIR    = ~/focus_pipeline/content
#   MEDIA_BASE_URL = http://127.0.0.1:8000/media
#   --replace is ON by default (re-running is safe / idempotent). Pass
#   --no-replace to keep existing components and append instead.
set -euo pipefail

cd "$(dirname "$0")"

CONTENT_DIR="${HOME}/focus_pipeline/content"
MEDIA_BASE_URL="http://127.0.0.1:8000/media"
REPLACE="--replace"

# Parse args: positionals in order, plus the --no-replace flag anywhere.
positional=()
for arg in "$@"; do
  case "$arg" in
    --no-replace) REPLACE="" ;;
    *) positional+=("$arg") ;;
  esac
done
[ "${#positional[@]}" -ge 1 ] && CONTENT_DIR="${positional[0]}"
[ "${#positional[@]}" -ge 2 ] && MEDIA_BASE_URL="${positional[1]}"

if [ ! -d "$CONTENT_DIR" ]; then
  echo "ERROR: content directory not found: $CONTENT_DIR" >&2
  exit 1
fi

# Activate the virtualenv if present (created by termux_setup.sh).
if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  . .venv/bin/activate
fi

echo ">>> Importing from: $CONTENT_DIR"
echo ">>> Media base URL: $MEDIA_BASE_URL"
[ -n "$REPLACE" ] && echo ">>> Mode: replace (idempotent)"

count=0
shopt -s nullglob
for level_dir in "$CONTENT_DIR"/*/; do
  level="$(basename "$level_dir")"
  for unit_dir in "$level_dir"*/; do
    json="${unit_dir}lesson.json"
    [ -f "$json" ] || continue
    unit="$(basename "$unit_dir")"

    media_args=()
    [ -d "${unit_dir}media" ] && media_args=(--media-dir "${unit_dir}media")

    echo ">>> [$level] $unit"
    python manage.py import_content "$json" \
      "${media_args[@]}" \
      --media-dest "imported/${level}/${unit}" \
      --media-base-url "$MEDIA_BASE_URL" \
      ${REPLACE}
    count=$((count + 1))
  done
done

echo ""
echo "=================================================================="
echo " Done. Imported $count unit file(s)."
echo " Start the server:  python manage.py runserver 127.0.0.1:8000"
echo "=================================================================="
