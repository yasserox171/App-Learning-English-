"""Strip the redundant code prefix from level names.

Earlier seeds/imports stored names like "A1 - Breakthrough"; the apps render
levels as "CODE — name", which produced "A1 — A1 - Breakthrough" on the home
card and certificates. Normalizing the stored name fixes every consumer.
"""
import re

from django.db import migrations


def strip_prefix(apps, schema_editor):
    Level = apps.get_model("content", "Level")
    for level in Level.objects.all():
        cleaned = re.sub(
            rf"^\s*{re.escape(level.code)}\s*[-–—:·]*\s*",
            "",
            level.name,
            flags=re.IGNORECASE,
        ).strip()
        if cleaned and cleaned != level.name:
            level.name = cleaned
            level.save(update_fields=["name"])


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0003_video_script_vocabularyitem_difficulty_and_more"),
    ]

    operations = [
        # Reverse is a no-op: nothing depends on the redundant prefix.
        migrations.RunPython(strip_prefix, migrations.RunPython.noop),
    ]
