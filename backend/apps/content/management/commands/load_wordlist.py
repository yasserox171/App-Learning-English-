"""Load the CEFR word classification list (v2 §1.1).

Usage:
    python manage.py load_wordlist                  # bundled starter list
    python manage.py load_wordlist path/to/list.csv # full Oxford-style list

CSV columns: word,cefr_level[,translation_ar]. Idempotent (upserts by word).
The bundled starter list covers common A1-C1 vocabulary; swap in a complete
Oxford 3000/5000 or CEFR-J export for production coverage.
"""
import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.content.models import WordLevel

BUNDLED = Path(__file__).resolve().parents[2] / "data" / "cefr_words.csv"
VALID_LEVELS = {"A1", "A2", "B1", "B2", "C1", "C2"}


class Command(BaseCommand):
    help = "Load/refresh the CEFR word list used for selective translation."

    def add_arguments(self, parser):
        parser.add_argument("csv_file", nargs="?", default=str(BUNDLED))

    def handle(self, *args, **options):
        path = Path(options["csv_file"])
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        created = updated = skipped = 0
        with path.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                word = (row.get("word") or "").strip().lower()
                level = (row.get("cefr_level") or "").strip().upper()
                translation = (row.get("translation_ar") or "").strip()
                if not word or level not in VALID_LEVELS:
                    skipped += 1
                    continue
                _, was_created = WordLevel.objects.update_or_create(
                    word=word,
                    defaults={"cefr_level": level, "translation_ar": translation},
                )
                created += was_created
                updated += not was_created

        self.stdout.write(self.style.SUCCESS(
            f"Word list loaded: {created} created, {updated} updated, "
            f"{skipped} skipped. Total: {WordLevel.objects.count()}"
        ))
