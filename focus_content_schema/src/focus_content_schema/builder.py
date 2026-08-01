"""Layer 3 — turn a validated IR plus a media manifest into an import payload.

The builder owns everything the LLM was not allowed to produce: ``order``
numbers, real media values, and the lesson/unit/level envelope.

The single most likely bug in this whole pipeline is swapping the two media
forms, because both are strings that look like paths:

    video component  storage_key  <- manifest["storage_key"]   RELATIVE
    vocabulary       image_url    <- manifest["url"]           ABSOLUTE
    vocabulary       audio_url    <- manifest["url"]           ABSOLUTE
    exercise         audio_url    <- manifest["url"]           ABSOLUTE
    exercise  reference_audio_url <- manifest["url"]           ABSOLUTE

They are not interchangeable. ``Video.storage_key`` is resolved through
``VideoService`` at request time (so hosting can move without rewriting rows),
while the vocabulary fields are Django ``URLField``s that reject a relative
path outright. :func:`_resolve_storage_key` and :func:`_resolve_url` assert the
shape of what they pull out of the manifest, so a swap fails loudly here
instead of producing a lesson with broken media.
"""
from __future__ import annotations

from typing import Any

from .ir import LessonIR
from .templates import is_absolute_url

PUBLISH_MODES = ("draft", "direct")
ON_DUPLICATE = ("skip", "replace")


class BuildError(Exception):
    """Raised when a payload cannot be built correctly. Never partially
    emitted: a dangling asset reference or a malformed manifest entry is a
    hard stop, not a warning."""


# --------------------------------------------------------------------------- #
# manifest resolution
# --------------------------------------------------------------------------- #
def _manifest_entry(manifest: dict, asset_id: str, *, where: str) -> dict:
    if asset_id not in manifest:
        known = ", ".join(sorted(manifest)) or "(manifest is empty)"
        raise BuildError(
            f"{where}: unresolved asset id {asset_id!r}. Known assets: {known}"
        )
    entry = manifest[asset_id]
    if not isinstance(entry, dict):
        raise BuildError(
            f"{where}: manifest entry for {asset_id!r} must be the upload API "
            f"response object, got {type(entry).__name__}"
        )
    return entry


def _resolve_storage_key(manifest: dict, asset_id: str, *, where: str) -> str:
    """Relative key for Video.storage_key. Rejects an absolute URL, which is
    the symptom of using the manifest's `url` here by mistake."""
    entry = _manifest_entry(manifest, asset_id, where=where)
    value = entry.get("storage_key")
    if not isinstance(value, str) or not value.strip():
        raise BuildError(
            f"{where}: manifest entry {asset_id!r} has no 'storage_key'. "
            f"A video component needs the relative key, not the URL."
        )
    if is_absolute_url(value):
        raise BuildError(
            f"{where}: 'storage_key' for {asset_id!r} is an absolute URL "
            f"({value!r}). Video.storage_key must be relative — it is resolved "
            f"through VideoService. Did you put the manifest 'url' here?"
        )
    return value.lstrip("/")


def _resolve_url(manifest: dict, asset_id: str, *, where: str) -> str:
    """Absolute URL for the URLField-backed fields. Rejects a relative path,
    the symptom of using the manifest's `storage_key` here by mistake."""
    entry = _manifest_entry(manifest, asset_id, where=where)
    value = entry.get("url")
    if not isinstance(value, str) or not value.strip():
        raise BuildError(
            f"{where}: manifest entry {asset_id!r} has no 'url'. This field is "
            f"a Django URLField and needs the absolute URL."
        )
    if not is_absolute_url(value):
        raise BuildError(
            f"{where}: 'url' for {asset_id!r} is not absolute ({value!r}). "
            f"This field is a URLField and rejects relative paths. Did you put "
            f"the manifest 'storage_key' here?"
        )
    return value


def _maybe_asset(value: Any) -> str | None:
    """Extract the logical id from an {"asset": ...} reference, else None."""
    if isinstance(value, dict) and isinstance(value.get("asset"), str):
        return value["asset"]
    return None


# --------------------------------------------------------------------------- #
# video script
# --------------------------------------------------------------------------- #
def _build_script(segments: list, duration: int, *, where: str) -> dict:
    """Validate and emit ``script`` for a video component.

    The backend stores this JSON unvalidated and the player only reads
    ``script.segments``, so bad timings degrade to silently missing subtitles.
    Checked here instead: ordered, non-overlapping, inside the video.
    """
    if not segments:
        return {}

    out = []
    previous_end = None
    for i, seg in enumerate(segments):
        start = float(seg.start)
        end = float(seg.end)
        if start >= end:
            raise BuildError(
                f"{where}: segments[{i}] start ({start}) must be less than "
                f"end ({end})"
            )
        if previous_end is not None and start < previous_end:
            raise BuildError(
                f"{where}: segments[{i}] starts at {start} which overlaps the "
                f"previous segment ending at {previous_end} — segments must be "
                f"sorted and non-overlapping"
            )
        previous_end = end
        out.append({
            "start": start,
            "end": end,
            "narration_en": seg.narration_en,
            "subtitle_ar": seg.subtitle_ar,
        })

    if previous_end is not None and previous_end > duration:
        raise BuildError(
            f"{where}: last segment ends at {previous_end}s but the video is "
            f"only {duration}s long"
        )
    return {"segments": out}


# --------------------------------------------------------------------------- #
# components
# --------------------------------------------------------------------------- #
def _build_vocabulary(component, manifest: dict, *, where: str) -> dict:
    items = []
    for i, item in enumerate(component.items, start=1):
        built = {
            "word": item.word,
            "translation": item.translation,
            "example_sentence": item.example_sentence,
            "syllables": item.syllables,
            "pronunciation_tip_ar": item.pronunciation_tip_ar,
            "difficulty": item.difficulty,
            "order": i,
        }
        if item.image is not None:
            # URLField -> absolute url, never the storage key.
            built["image_url"] = _resolve_url(
                manifest, item.image.asset, where=f"{where}.items[{i - 1}].image"
            )
        if item.audio is not None:
            built["audio_url"] = _resolve_url(
                manifest, item.audio.asset, where=f"{where}.items[{i - 1}].audio"
            )
        items.append(built)
    return {"items": items}


def _build_exercises(component, manifest: dict, *, where: str) -> dict:
    exercises = []
    for i, ex in enumerate(component.exercises, start=1):
        content = dict(ex.content)
        # Media inside exercise content is absolute: the client renders it.
        for key in ("audio_url", "reference_audio_url"):
            asset_id = _maybe_asset(content.get(key))
            if asset_id is not None:
                content[key] = _resolve_url(
                    manifest, asset_id, where=f"{where}.exercises[{i - 1}].{key}"
                )
        exercises.append({
            "template": ex.template,
            "content": content,
            "points": ex.points,
            "order": i,
        })
    return {"exercises": exercises}


def _build_component(component, manifest: dict, order: int) -> dict:
    where = f"components[{order - 1}]"
    built: dict[str, Any] = {"type": component.type, "order": order}

    if component.type == "text":
        built["content"] = component.content
    elif component.type == "vocabulary":
        built.update(_build_vocabulary(component, manifest, where=where))
    elif component.type == "video":
        # Relative key — resolved through VideoService at request time.
        built["storage_key"] = _resolve_storage_key(
            manifest, component.asset.asset, where=f"{where}.asset"
        )
        built["title"] = component.title
        built["duration"] = component.duration
        built["status"] = "ready"
        script = _build_script(component.segments, component.duration, where=where)
        if script:
            built["script"] = script
    elif component.type == "exercise":
        built.update(_build_exercises(component, manifest, where=where))
    else:  # pragma: no cover - the IR discriminator makes this unreachable
        raise BuildError(f"{where}: unknown component type {component.type!r}")

    return built


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #
def build_import_payload(
    ir: LessonIR | dict,
    media_manifest: dict[str, dict] | None = None,
    *,
    level: str,
    unit: dict,
    lesson: dict,
    idempotency_key: str | None = None,
    publish_mode: str = "draft",
    on_duplicate: str | None = None,
) -> dict:
    """Build the import-API payload from an IR and a media manifest.

    ``media_manifest`` maps logical asset id -> the media upload API response
    (``{"storage_key": ..., "url": ..., "kind": ...}``).

    Raises :class:`BuildError` on an unresolved asset, a manifest entry missing
    the field this position needs, or invalid video segment timings. It never
    emits a payload containing a dangling reference.
    """
    manifest = media_manifest or {}
    model = ir if isinstance(ir, LessonIR) else LessonIR.model_validate(ir)

    if publish_mode not in PUBLISH_MODES:
        raise BuildError(
            f"publish_mode must be one of {PUBLISH_MODES}, got {publish_mode!r}"
        )
    if on_duplicate is not None and on_duplicate not in ON_DUPLICATE:
        raise BuildError(
            f"on_duplicate must be one of {ON_DUPLICATE}, got {on_duplicate!r}"
        )
    if not isinstance(unit, dict) or not str(unit.get("title", "")).strip():
        raise BuildError("unit must be an object with a non-empty 'title'")
    if not isinstance(lesson, dict) or not str(lesson.get("title", "")).strip():
        raise BuildError("lesson must be an object with a non-empty 'title'")

    payload: dict[str, Any] = {
        "level": level,
        "unit": {
            "title": unit["title"],
            "order": unit.get("order", 1),
            "description": unit.get("description", ""),
        },
        "lesson": {
            "title": lesson["title"],
            "order": lesson.get("order", 1),
            "description": lesson.get("description", ""),
        },
        "components": [
            _build_component(component, manifest, order)
            for order, component in enumerate(model.components, start=1)
        ],
        "publish_mode": publish_mode,
    }
    if idempotency_key:
        payload["idempotency_key"] = idempotency_key
    if on_duplicate is not None:
        payload["on_duplicate"] = on_duplicate
    return payload
