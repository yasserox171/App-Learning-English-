"""Import a full lesson (or several) from a JSON file via the CLI.

Builds the whole hierarchy in one shot:
    Level (by code) -> Unit -> Lesson -> LessonComponent[] ->
        TextBlock / VocabularyItem[] / Video / Exercise[]

Media handling:
    Media fields may be absolute URLs (http/https, used as-is) OR relative
    paths. Relative paths are rewritten to
        {media_base_url}/{media_dest}/{path}
    and, if --media-dir is given, that directory's files are copied into
        {MEDIA_ROOT}/{media_dest}/
    Rewritten fields: vocabulary item image_url & audio_url, and exercise
    content keys "audio_url" / "reference_audio_url" (listening/pronunciation).

Usage:
    python manage.py import_content lesson.json
    python manage.py import_content lesson.json --media-dir ./media --replace
"""
import json
import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.content.models import (
    Lesson,
    LessonComponent,
    Level,
    TextBlock,
    Unit,
    Video,
    VocabularyItem,
)
from apps.exercises.models import Exercise, ExerciseTemplate

COMPONENT_TYPES = {c.value for c in LessonComponent.Type}
TEMPLATE_CODES = {c.value for c in ExerciseTemplate.Code}


class Command(BaseCommand):
    help = "Import a full lesson (or list of lessons) from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument("json_file", help="Path to the lesson JSON file")
        parser.add_argument(
            "--media-dir",
            help="Local directory of media files to copy into MEDIA_ROOT",
        )
        parser.add_argument(
            "--media-dest",
            default="imported",
            help="Subfolder under MEDIA_ROOT for media (default: imported)",
        )
        parser.add_argument(
            "--media-base-url",
            default="http://127.0.0.1:8000/media",
            help="Base URL prepended to relative media paths "
            "(default: http://127.0.0.1:8000/media)",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete a lesson's existing components before importing",
        )

    def handle(self, *args, **opts):
        path = Path(opts["json_file"])
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON: {e}")

        lessons = data if isinstance(data, list) else [data]

        # Copy media once (if provided) and build the URL prefix.
        self._media_base = opts["media_base_url"].rstrip("/")
        self._media_dest = opts["media_dest"].strip("/")
        if opts["media_dir"]:
            src = Path(opts["media_dir"])
            if not src.is_dir():
                raise CommandError(f"--media-dir not a directory: {src}")
            dest = Path(settings.MEDIA_ROOT) / self._media_dest
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dest, dirs_exist_ok=True)
            self.stdout.write(f"Copied media: {src} -> {dest}")

        for entry in lessons:
            self._import_lesson(entry, replace=opts["replace"])

        self.stdout.write(self.style.SUCCESS("Import complete."))

    # ------------------------------------------------------------------ #
    def _media_url(self, value):
        """Rewrite a relative media path to an absolute URL; pass URLs through."""
        if not value:
            return value
        if value.startswith("http://") or value.startswith("https://"):
            return value
        return f"{self._media_base}/{self._media_dest}/{value.lstrip('/')}"

    @transaction.atomic
    def _import_lesson(self, entry, *, replace):
        code = entry.get("level")
        try:
            level = Level.objects.get(code=code)
        except Level.DoesNotExist:
            raise CommandError(
                f"Level '{code}' does not exist. Available: "
                f"{', '.join(Level.objects.values_list('code', flat=True))}"
            )

        u = entry["unit"]
        unit, _ = Unit.objects.get_or_create(
            level=level, title=u["title"],
            defaults={"order": u.get("order", 0),
                      "description": u.get("description", "")},
        )

        ls = entry["lesson"]
        lesson, _ = Lesson.objects.get_or_create(
            unit=unit, title=ls["title"],
            defaults={"order": ls.get("order", 0),
                      "description": ls.get("description", "")},
        )

        if replace:
            lesson.components.all().delete()

        n_comp = n_ex = 0
        for comp in entry.get("components", []):
            ctype = comp.get("type")
            if ctype not in COMPONENT_TYPES:
                raise CommandError(
                    f"Unknown component type '{ctype}'. "
                    f"Allowed: {', '.join(sorted(COMPONENT_TYPES))}"
                )
            component = LessonComponent.objects.create(
                lesson=lesson, type=ctype,
                order=comp.get("order", 0), config=comp.get("config", {}),
            )
            n_comp += 1
            n_ex += self._build_payload(component, ctype, comp)

        self.stdout.write(
            f"  {level.code} / {unit.title} / {lesson.title}: "
            f"{n_comp} components, {n_ex} exercises"
        )

    def _build_payload(self, component, ctype, comp):
        if ctype == LessonComponent.Type.TEXT:
            TextBlock.objects.create(
                component=component, content=comp.get("content", ""))

        elif ctype == LessonComponent.Type.VOCABULARY:
            for i, v in enumerate(comp.get("items", []), start=1):
                VocabularyItem.objects.create(
                    component=component,
                    word=v["word"],
                    translation=v.get("translation", ""),
                    example_sentence=v.get("example_sentence", ""),
                    image_url=self._media_url(v.get("image_url", "")),
                    audio_url=self._media_url(v.get("audio_url", "")),
                    order=v.get("order", i),
                )

        elif ctype == LessonComponent.Type.VIDEO:
            Video.objects.create(
                component=component,
                title=comp.get("title", ""),
                duration=comp.get("duration", 0),
                # Relative paths become absolute media URLs (like other media);
                # VideoService passes absolute URLs through unchanged.
                storage_key=self._media_url(comp.get("storage_key", "")),
                status=comp.get("status", Video.Status.READY),
            )

        elif ctype == LessonComponent.Type.EXERCISE:
            count = 0
            for i, ex in enumerate(comp.get("exercises", []), start=1):
                tcode = ex.get("template")
                if tcode not in TEMPLATE_CODES:
                    raise CommandError(
                        f"Unknown template '{tcode}'. "
                        f"Allowed: {', '.join(sorted(TEMPLATE_CODES))}"
                    )
                template = ExerciseTemplate.objects.get(code=tcode)
                Exercise.objects.create(
                    component=component,
                    template=template,
                    content=self._rewrite_content_media(ex.get("content", {})),
                    points=ex.get("points", 1),
                    order=ex.get("order", i),
                )
                count += 1
            return count
        return 0

    def _rewrite_content_media(self, content):
        """Rewrite known audio keys inside exercise content."""
        if isinstance(content, dict):
            for key in ("audio_url", "reference_audio_url"):
                if content.get(key):
                    content[key] = self._media_url(content[key])
        return content
