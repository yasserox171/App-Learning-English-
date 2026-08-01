"""Layer 4 — the last gate before any HTTP call.

Reproduces every rule the backend *does* enforce (so a rejection is caught
locally in milliseconds rather than after a round trip) **plus** every rule the
backend does not enforce but silently depends on — chiefly the per-template
``content`` rules from Layer 2, which the import API never checks.

Run this on the exact dict you are about to POST. It returns every problem it
can find, and never raises.
"""
from __future__ import annotations

from typing import Any

from .templates import (
    VALID_TEMPLATES,
    is_absolute_url,
    validate_exercise_content,
)

# Mirrors backend Level codes and LessonComponent.Type.
VALID_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")
VALID_COMPONENT_TYPES = ("text", "vocabulary", "video", "exercise")
VALID_PUBLISH_MODES = ("draft", "direct")
VALID_ON_DUPLICATE = ("skip", "replace")
VALID_VIDEO_STATUS = ("processing", "ready")


def _nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_envelope(payload: dict, errors: list[str]) -> None:
    level = payload.get("level")
    if not level:
        errors.append("'level' is required (e.g. 'A1')")
    elif level not in VALID_LEVELS:
        errors.append(
            f"'level' must be one of {', '.join(VALID_LEVELS)}, got {level!r}"
        )

    unit = payload.get("unit")
    if not isinstance(unit, dict) or not _nonempty_str(unit.get("title")):
        errors.append("'unit' object with a non-empty 'title' is required")

    lesson = payload.get("lesson")
    if not isinstance(lesson, dict) or not _nonempty_str(lesson.get("title")):
        errors.append("'lesson' object with a non-empty 'title' is required")

    mode = payload.get("publish_mode")
    if mode is not None and mode not in VALID_PUBLISH_MODES:
        errors.append(
            f"'publish_mode' must be one of {', '.join(VALID_PUBLISH_MODES)}, "
            f"got {mode!r}"
        )

    on_dup = payload.get("on_duplicate")
    if on_dup is not None and on_dup not in VALID_ON_DUPLICATE:
        errors.append(
            f"'on_duplicate' must be one of {', '.join(VALID_ON_DUPLICATE)}, "
            f"got {on_dup!r}"
        )

    key = payload.get("idempotency_key")
    if key is not None and not _nonempty_str(key):
        errors.append("'idempotency_key' must not be blank when provided")


def _validate_video(comp: dict, where: str, errors: list[str]) -> None:
    key = comp.get("storage_key")
    if not _nonempty_str(key):
        errors.append(f"{where}: video needs a non-empty 'storage_key'")
    elif is_absolute_url(key):
        # Legal for the backend, but it bypasses VideoService and pins the
        # host into the row — almost always the manifest 'url' by mistake.
        errors.append(
            f"{where}: 'storage_key' is an absolute URL ({key!r}); it should "
            f"be the relative key so VideoService can resolve it"
        )

    duration = comp.get("duration")
    if duration is not None and (
        not isinstance(duration, int)
        or isinstance(duration, bool)
        or duration < 0
    ):
        errors.append(
            f"{where}: 'duration' must be a non-negative integer, got "
            f"{duration!r}"
        )

    status = comp.get("status")
    if status is not None and status not in VALID_VIDEO_STATUS:
        errors.append(
            f"{where}: 'status' must be one of "
            f"{', '.join(VALID_VIDEO_STATUS)}, got {status!r}"
        )

    script = comp.get("script")
    if script in (None, {}):
        return
    if not isinstance(script, dict):
        errors.append(f"{where}: 'script' must be an object")
        return
    segments = script.get("segments")
    if segments is None:
        return
    if not isinstance(segments, list):
        errors.append(f"{where}: 'script.segments' must be a list")
        return

    previous_end = None
    for i, seg in enumerate(segments):
        at = f"{where}.script.segments[{i}]"
        if not isinstance(seg, dict):
            errors.append(f"{at}: must be an object")
            continue
        start, end = seg.get("start"), seg.get("end")
        numeric = True
        for name, value in (("start", start), ("end", end)):
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                errors.append(f"{at}: '{name}' must be a number, got {value!r}")
                numeric = False
        if numeric:
            if start >= end:
                errors.append(
                    f"{at}: 'start' ({start}) must be less than 'end' ({end})"
                )
            if previous_end is not None and start < previous_end:
                errors.append(
                    f"{at}: overlaps the previous segment ending at "
                    f"{previous_end} — segments must be sorted and "
                    f"non-overlapping"
                )
            previous_end = end
        for name in ("narration_en", "subtitle_ar"):
            if not _nonempty_str(seg.get(name)):
                errors.append(f"{at}: '{name}' must be a non-empty string")

    duration_ok = isinstance(duration, int) and not isinstance(duration, bool)
    if previous_end is not None and duration_ok and previous_end > duration:
        errors.append(
            f"{where}: last segment ends at {previous_end}s but the video is "
            f"only {duration}s long"
        )


def _validate_vocabulary(comp: dict, where: str, errors: list[str]) -> None:
    items = comp.get("items")
    if not isinstance(items, list) or not items:
        errors.append(f"{where}: vocabulary needs a non-empty 'items' list")
        return
    for i, item in enumerate(items):
        at = f"{where}.items[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{at}: must be an object")
            continue
        if not _nonempty_str(item.get("word")):
            errors.append(f"{at}: 'word' is required")
        if not _nonempty_str(item.get("translation")):
            errors.append(f"{at}: 'translation' is required")
        # image_url / audio_url are Django URLFields: relative paths are
        # rejected by the server, so catch them here.
        for field in ("image_url", "audio_url"):
            value = item.get(field)
            if value in (None, ""):
                continue
            if not is_absolute_url(value):
                errors.append(
                    f"{at}: '{field}' must be an absolute http(s) URL (it is a "
                    f"URLField), got {value!r}"
                )


def _validate_exercises(comp: dict, where: str, errors: list[str]) -> None:
    exercises = comp.get("exercises")
    if not isinstance(exercises, list) or not exercises:
        errors.append(f"{where}: exercise component needs a non-empty "
                      f"'exercises' list")
        return
    for i, ex in enumerate(exercises):
        at = f"{where}.exercises[{i}]"
        if not isinstance(ex, dict):
            errors.append(f"{at}: must be an object")
            continue
        template = ex.get("template")
        if template is None:
            errors.append(f"{at}: 'template' is required")
            continue
        points = ex.get("points")
        if points is not None and (
            not isinstance(points, int) or isinstance(points, bool) or points < 0
        ):
            errors.append(
                f"{at}: 'points' must be a non-negative integer, got {points!r}"
            )
        # The rules the backend never checks.
        for message in validate_exercise_content(
            template, ex.get("content"), allow_asset_refs=False
        ):
            errors.append(f"{at}: {message}")


def validate_payload(payload: Any) -> list[str]:
    """Validate a fully built import payload. Returns all errors; never raises.

    An empty list means it is safe to POST.
    """
    if not isinstance(payload, dict):
        return ["payload must be a JSON object"]

    errors: list[str] = []
    _validate_envelope(payload, errors)

    components = payload.get("components", [])
    if not isinstance(components, list):
        errors.append("'components' must be a list")
        return errors
    if not components:
        errors.append("'components' must not be empty")

    seen_orders: list[Any] = []
    for i, comp in enumerate(components):
        where = f"components[{i}]"
        if not isinstance(comp, dict):
            errors.append(f"{where}: must be an object")
            continue
        ctype = comp.get("type")
        if ctype not in VALID_COMPONENT_TYPES:
            errors.append(
                f"{where}: unknown type {ctype!r} (allowed: "
                f"{', '.join(VALID_COMPONENT_TYPES)})"
            )
            continue

        order = comp.get("order")
        if order is not None:
            if not isinstance(order, int) or isinstance(order, bool) or order < 0:
                errors.append(
                    f"{where}: 'order' must be a non-negative integer, got "
                    f"{order!r}"
                )
            else:
                seen_orders.append(order)

        if ctype == "text":
            if not _nonempty_str(comp.get("content")):
                errors.append(f"{where}: text needs non-empty 'content'")
        elif ctype == "vocabulary":
            _validate_vocabulary(comp, where, errors)
        elif ctype == "video":
            _validate_video(comp, where, errors)
        elif ctype == "exercise":
            _validate_exercises(comp, where, errors)

    if len(set(seen_orders)) != len(seen_orders):
        errors.append(
            "component 'order' values must be unique — duplicates make the "
            "lesson sequence non-deterministic"
        )
    return errors


def validate_ir_dict(data: Any) -> list[str]:
    """Validate raw LLM output against the IR, including template rules.

    Asset references are still unresolved at this stage, so URL-bearing fields
    may hold ``{"asset": "id"}``.
    """
    from pydantic import ValidationError

    from .ir import LessonIR

    from .templates import FINAL_TEST_REJECTION

    try:
        model = LessonIR.model_validate(data)
    except ValidationError as exc:
        errors = []
        for err in exc.errors():
            loc = ".".join(str(p) for p in err["loc"]) or "(root)"
            given = err.get("input")
            # The IR's Literal type rejects final_test, but pydantic's message
            # only lists the allowed values — it never echoes what was sent, so
            # the author would not learn *why* final_test is unavailable.
            if loc.endswith("template") and given == "final_test":
                errors.append(f"{loc}: {FINAL_TEST_REJECTION}")
                continue
            message = f"{loc}: {err['msg']}"
            # Echo the offending value; pydantic omits it for enum/literal
            # errors, which makes them hard to act on.
            if given is not None and not isinstance(given, (dict, list)):
                message += f" (got {given!r})"
            errors.append(message)
        return errors

    errors = []
    for i, comp in enumerate(model.components):
        if comp.type != "exercise":
            continue
        for j, ex in enumerate(comp.exercises):
            for message in validate_exercise_content(
                ex.template, ex.content, allow_asset_refs=True
            ):
                errors.append(f"components[{i}].exercises[{j}]: {message}")
    return errors
