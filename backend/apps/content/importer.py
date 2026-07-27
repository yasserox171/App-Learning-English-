"""Programmatic lesson import (v2 §5) — validation + build, shared by the
Content Import API. Mirrors the JSON schema of the import_content management
command, but returns structured errors instead of CommandError and supports
the draft/direct publish modes.
"""
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


class ImportValidationError(Exception):
    def __init__(self, errors):
        self.errors = errors if isinstance(errors, list) else [errors]
        super().__init__("; ".join(self.errors))


def validate_lesson_json(data: dict) -> list[str]:
    """Validate the lesson payload against the existing content schema.
    Returns a list of error strings (empty = valid)."""
    errors = []
    if not isinstance(data, dict):
        return ["Payload must be a JSON object"]

    level_code = data.get("level")
    if not level_code:
        errors.append("'level' is required (e.g. 'A1')")
    elif not Level.objects.filter(code=level_code).exists():
        errors.append(f"Level '{level_code}' does not exist")

    unit = data.get("unit")
    if not isinstance(unit, dict) or not unit.get("title"):
        errors.append("'unit' object with a 'title' is required")

    lesson = data.get("lesson")
    if not isinstance(lesson, dict) or not lesson.get("title"):
        errors.append("'lesson' object with a 'title' is required")

    template_codes = set(
        ExerciseTemplate.objects.values_list("code", flat=True)
    )
    components = data.get("components", [])
    if not isinstance(components, list):
        errors.append("'components' must be a list")
        components = []
    for i, comp in enumerate(components):
        ctype = comp.get("type")
        if ctype not in COMPONENT_TYPES:
            errors.append(
                f"components[{i}]: unknown type '{ctype}' "
                f"(allowed: {', '.join(sorted(COMPONENT_TYPES))})"
            )
            continue
        if ctype == "exercise":
            for j, ex in enumerate(comp.get("exercises", [])):
                tcode = ex.get("template")
                if tcode not in template_codes:
                    errors.append(
                        f"components[{i}].exercises[{j}]: unknown template "
                        f"'{tcode}'"
                    )
                if not isinstance(ex.get("content"), dict):
                    errors.append(
                        f"components[{i}].exercises[{j}]: 'content' object "
                        "is required"
                    )
        elif ctype == "vocabulary":
            for j, item in enumerate(comp.get("items", [])):
                if not item.get("word"):
                    errors.append(
                        f"components[{i}].items[{j}]: 'word' is required"
                    )
    return errors


@transaction.atomic
def import_lesson(data: dict, *, status: str) -> Lesson:
    """Build the Level→Unit→Lesson→components tree from validated JSON."""
    errors = validate_lesson_json(data)
    if errors:
        raise ImportValidationError(errors)

    level = Level.objects.get(code=data["level"])
    u = data["unit"]
    unit, _ = Unit.objects.get_or_create(
        level=level,
        title=u["title"],
        defaults={"order": u.get("order", 0),
                  "description": u.get("description", "")},
    )
    ls = data["lesson"]
    lesson = Lesson.objects.create(
        unit=unit,
        title=ls["title"],
        order=ls.get("order", 0),
        description=ls.get("description", ""),
        status=status,
    )

    templates = {t.code: t for t in ExerciseTemplate.objects.all()}
    for comp in data.get("components", []):
        component = LessonComponent.objects.create(
            lesson=lesson,
            type=comp["type"],
            order=comp.get("order", 0),
            config=comp.get("config", {}),
        )
        if comp["type"] == LessonComponent.Type.TEXT:
            TextBlock.objects.create(
                component=component, content=comp.get("content", "")
            )
        elif comp["type"] == LessonComponent.Type.VOCABULARY:
            for i, v in enumerate(comp.get("items", []), start=1):
                VocabularyItem.objects.create(
                    component=component,
                    word=v["word"],
                    translation=v.get("translation", ""),
                    example_sentence=v.get("example_sentence", ""),
                    image_url=v.get("image_url") or "",
                    audio_url=v.get("audio_url") or "",
                    syllables=v.get("syllables") or "",
                    pronunciation_tip_ar=v.get("pronunciation_tip_ar") or "",
                    difficulty=v.get("difficulty") or "",
                    order=v.get("order", i),
                )
        elif comp["type"] == LessonComponent.Type.VIDEO:
            Video.objects.create(
                component=component,
                title=comp.get("title", ""),
                duration=comp.get("duration", 0),
                storage_key=comp.get("storage_key", ""),
                status=comp.get("status", Video.Status.READY),
                script=comp.get("script") or {},
            )
        elif comp["type"] == LessonComponent.Type.EXERCISE:
            for i, ex in enumerate(comp.get("exercises", []), start=1):
                Exercise.objects.create(
                    component=component,
                    template=templates[ex["template"]],
                    content=ex.get("content", {}),
                    points=ex.get("points", 1),
                    order=ex.get("order", i),
                )
    return lesson
