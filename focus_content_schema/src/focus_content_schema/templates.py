"""Layer 2 — strict per-template validation of exercise ``content``.

Why this is the only line of defence: the Focus Languages backend stores an
``ExerciseTemplate.content_schema`` but **never enforces it**. The import API
checks only that ``content`` is a dict. So a ``multiple_choice`` with no
``correct_index`` imports cleanly, and then every learner answer is graded
wrong forever, silently. Everything below exists to stop that.

Contract for every validator:
  * takes the content dict, returns a list of human-readable error strings
  * collects **all** errors — never returns after the first
  * never raises, whatever garbage it is handed

Absolute-URL rule matches the backend's own test
(``LocalVideoService.get_playback_url``): a value is absolute when it starts
with ``http://`` or ``https://``.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Callable

# The eight templates this pipeline may produce.
VALID_TEMPLATES = (
    "multiple_choice",
    "true_false",
    "fill_blank",
    "matching",
    "reorder",
    "listening",
    "pronunciation",
    "dictation",
)

# final_test exists in the backend but cannot be generated: its content is
# {"exercise_ids": [...]} referencing UUIDs of exercises that do not exist
# until after this lesson is imported.
FINAL_TEST_REJECTION = (
    "template 'final_test' cannot be generated automatically: its content "
    "references UUIDs of exercises that do not exist until after import. "
    "Create it from the admin panel once the lesson exists."
)

BLANK_MARKER = "___"


# --------------------------------------------------------------------------- #
# shared helpers
# --------------------------------------------------------------------------- #
def is_absolute_url(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def _is_asset_ref(value: Any) -> bool:
    """An unresolved builder placeholder: {"asset": "logical_id"}."""
    return (
        isinstance(value, dict)
        and set(value) == {"asset"}
        and isinstance(value.get("asset"), str)
        and bool(value["asset"].strip())
    )


def _nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_real_bool(value: Any) -> bool:
    """True only for an actual bool. Guards against "true" and 1, both of
    which the backend's ``bool(...)`` coercion would silently accept."""
    return isinstance(value, bool)


def _is_real_int(value: Any) -> bool:
    """bool is a subclass of int in Python, so True would pass isinstance;
    an index of True==1 is never what anyone meant."""
    return isinstance(value, int) and not isinstance(value, bool)


def _check_media_field(
    content: dict, key: str, errors: list[str], *,
    required: bool, allow_asset_refs: bool, label: str,
) -> None:
    """Validate a URL-bearing field, allowing an unresolved asset ref while
    the payload is still in IR form."""
    if key not in content or content[key] in (None, ""):
        if required:
            errors.append(f"{label}: '{key}' is required")
        return
    value = content[key]
    if allow_asset_refs and _is_asset_ref(value):
        return
    if not is_absolute_url(value):
        hint = " (or an {\"asset\": \"...\"} reference)" if allow_asset_refs else ""
        errors.append(
            f"{label}: '{key}' must be an absolute http(s) URL{hint}, got "
            f"{value!r}"
        )


def _check_options(
    content: dict, errors: list[str], label: str, *, min_options: int = 2
) -> list | None:
    options = content.get("options")
    if not isinstance(options, list):
        errors.append(f"{label}: 'options' must be a list of strings")
        return None
    if len(options) < min_options:
        errors.append(
            f"{label}: needs at least {min_options} options, got {len(options)}"
        )
    non_strings = [o for o in options if not _nonempty_str(o)]
    if non_strings:
        errors.append(f"{label}: every option must be a non-empty string")
    # Normalised duplicate check: two options a learner cannot tell apart make
    # the question unanswerable regardless of exact casing/spacing.
    seen = Counter(
        o.strip().casefold() for o in options if isinstance(o, str)
    )
    dupes = sorted(k for k, n in seen.items() if n > 1)
    if dupes:
        errors.append(
            f"{label}: duplicate options: {', '.join(repr(d) for d in dupes)}"
        )
    return options


def _check_correct_index(
    content: dict, options: list | None, errors: list[str], label: str
) -> None:
    if "correct_index" not in content:
        errors.append(f"{label}: 'correct_index' is required")
        return
    idx = content["correct_index"]
    if not _is_real_int(idx):
        errors.append(
            f"{label}: 'correct_index' must be an integer, got {idx!r}"
        )
        return
    if options is not None and not (0 <= idx < len(options)):
        errors.append(
            f"{label}: 'correct_index' {idx} is out of range for "
            f"{len(options)} options"
        )


# --------------------------------------------------------------------------- #
# per-template validators
# --------------------------------------------------------------------------- #
def _multiple_choice(content: dict, *, allow_asset_refs: bool) -> list[str]:
    """{"question": str, "options": [str, ...], "correct_index": int}"""
    errors: list[str] = []
    label = "multiple_choice"
    if not _nonempty_str(content.get("question")):
        errors.append(f"{label}: 'question' must be a non-empty string")
    options = _check_options(content, errors, label)
    _check_correct_index(content, options, errors, label)
    return errors


def _true_false(content: dict, *, allow_asset_refs: bool) -> list[str]:
    """{"statement": str, "answer": bool}"""
    errors: list[str] = []
    label = "true_false"
    if not _nonempty_str(content.get("statement")):
        errors.append(f"{label}: 'statement' must be a non-empty string")
    if "answer" not in content:
        errors.append(f"{label}: 'answer' is required")
    elif not _is_real_bool(content["answer"]):
        errors.append(
            f"{label}: 'answer' must be a real boolean (true/false), not "
            f"{content['answer']!r}"
        )
    return errors


def _fill_blank(content: dict, *, allow_asset_refs: bool) -> list[str]:
    """{"sentence": str containing '___', "answer": str, "options"?: [str]}

    ``options`` is genuinely optional: when absent the backend builds a word
    bank from the lesson's vocabulary at serialization time, so its absence is
    valid, not missing. When supplied it must contain the answer.
    """
    errors: list[str] = []
    label = "fill_blank"
    sentence = content.get("sentence")
    if not _nonempty_str(sentence):
        errors.append(f"{label}: 'sentence' must be a non-empty string")
    elif BLANK_MARKER not in sentence:
        errors.append(
            f"{label}: 'sentence' must contain the blank marker "
            f"'{BLANK_MARKER}'"
        )
    answer = content.get("answer")
    if not _nonempty_str(answer):
        errors.append(f"{label}: 'answer' must be a non-empty string")

    if "options" in content and content["options"] is not None:
        options = _check_options(content, errors, label)
        if options and _nonempty_str(answer):
            present = any(
                isinstance(o, str)
                and o.strip().casefold() == answer.strip().casefold()
                for o in options
            )
            if not present:
                errors.append(
                    f"{label}: 'options' must contain the answer "
                    f"{answer!r}"
                )
    return errors


def _matching(content: dict, *, allow_asset_refs: bool) -> list[str]:
    """{"pairs": [{"left": str, "right": str}, ...]}

    The strictest validator here, on purpose. The backend grader reads
    ``p["left"]`` / ``p["right"]`` with bracket access, so a pair missing a
    side raises KeyError *during grading* — a 500 for a learner mid-lesson.
    """
    errors: list[str] = []
    label = "matching"
    pairs = content.get("pairs")
    if not isinstance(pairs, list):
        errors.append(f"{label}: 'pairs' must be a list")
        return errors
    if len(pairs) < 2:
        errors.append(f"{label}: needs at least 2 pairs, got {len(pairs)}")

    lefts: list[str] = []
    for i, pair in enumerate(pairs):
        if not isinstance(pair, dict):
            errors.append(f"{label}: pairs[{i}] must be an object")
            continue
        for side in ("left", "right"):
            if side not in pair:
                errors.append(
                    f"{label}: pairs[{i}] is missing '{side}' — the grader "
                    f"uses bracket access and would raise KeyError"
                )
            elif not _nonempty_str(pair[side]):
                errors.append(
                    f"{label}: pairs[{i}]['{side}'] must be a non-empty "
                    f"string, got {pair[side]!r}"
                )
        if _nonempty_str(pair.get("left")):
            lefts.append(pair["left"].strip().casefold())

    dupes = sorted(k for k, n in Counter(lefts).items() if n > 1)
    if dupes:
        # Grading compares sets, so duplicate lefts silently change the
        # denominator and make partial credit wrong.
        errors.append(
            f"{label}: duplicate left values: "
            f"{', '.join(repr(d) for d in dupes)}"
        )
    return errors


def _reorder(content: dict, *, allow_asset_refs: bool) -> list[str]:
    """{"words": [str, ...], "correct_order": [str, ...]}

    ``correct_order`` must be a permutation of ``words`` — compared as a
    multiset, so duplicated words are handled and a same-length-but-different
    list is caught.
    """
    errors: list[str] = []
    label = "reorder"
    words = content.get("words")
    order = content.get("correct_order")

    if not isinstance(words, list) or not words:
        errors.append(f"{label}: 'words' must be a non-empty list of strings")
    elif any(not _nonempty_str(w) for w in words):
        errors.append(f"{label}: every entry in 'words' must be a non-empty string")

    if not isinstance(order, list) or not order:
        errors.append(
            f"{label}: 'correct_order' must be a non-empty list of strings"
        )
    elif any(not _nonempty_str(w) for w in order):
        errors.append(
            f"{label}: every entry in 'correct_order' must be a non-empty string"
        )

    if isinstance(words, list) and isinstance(order, list) and words and order:
        if Counter(words) != Counter(order):
            missing = sorted((Counter(words) - Counter(order)).elements())
            extra = sorted((Counter(order) - Counter(words)).elements())
            detail = []
            if missing:
                detail.append(f"missing from correct_order: {missing}")
            if extra:
                detail.append(f"not in words: {extra}")
            errors.append(
                f"{label}: 'correct_order' must be a permutation of 'words' "
                f"({'; '.join(detail) or 'different multisets'})"
            )
    return errors


def _listening(content: dict, *, allow_asset_refs: bool) -> list[str]:
    """{"audio_url": absolute, "question": str, "options": [str],
        "correct_index": int}"""
    errors: list[str] = []
    label = "listening"
    _check_media_field(
        content, "audio_url", errors,
        required=True, allow_asset_refs=allow_asset_refs, label=label,
    )
    if not _nonempty_str(content.get("question")):
        errors.append(f"{label}: 'question' must be a non-empty string")
    options = _check_options(content, errors, label)
    _check_correct_index(content, options, errors, label)
    return errors


def _pronunciation(content: dict, *, allow_asset_refs: bool) -> list[str]:
    """{"target_text": str, "reference_audio_url"?: absolute}"""
    errors: list[str] = []
    label = "pronunciation"
    if not _nonempty_str(content.get("target_text")):
        errors.append(f"{label}: 'target_text' must be a non-empty string")
    _check_media_field(
        content, "reference_audio_url", errors,
        required=False, allow_asset_refs=allow_asset_refs, label=label,
    )
    return errors


def _dictation(content: dict, *, allow_asset_refs: bool) -> list[str]:
    """{"answer": str, "audio_url"?: absolute, "hint"?: str,
        "show_hint_after_attempts"?: int >= 0}

    Shape settled here because the codebase has **no** dictation example: the
    seed skips it and ``apps/common/tests.py`` explicitly asserts it is the
    one template without sample data. Chosen from the seeded
    ``content_schema`` row, which requires only ``answer``.

    ``audio_url`` is optional by design: when it is absent the backend
    serializer sets ``audio_text`` to the answer so the client can speak it
    with TTS, and the learner still never sees the text.
    """
    errors: list[str] = []
    label = "dictation"
    if not _nonempty_str(content.get("answer")):
        errors.append(f"{label}: 'answer' must be a non-empty string")
    _check_media_field(
        content, "audio_url", errors,
        required=False, allow_asset_refs=allow_asset_refs, label=label,
    )
    if "hint" in content and content["hint"] is not None:
        if not isinstance(content["hint"], str):
            errors.append(f"{label}: 'hint' must be a string")
    attempts = content.get("show_hint_after_attempts")
    if attempts is not None:
        if not _is_real_int(attempts) or attempts < 0:
            errors.append(
                f"{label}: 'show_hint_after_attempts' must be a non-negative "
                f"integer, got {attempts!r}"
            )
    return errors


_VALIDATORS: dict[str, Callable[..., list[str]]] = {
    "multiple_choice": _multiple_choice,
    "true_false": _true_false,
    "fill_blank": _fill_blank,
    "matching": _matching,
    "reorder": _reorder,
    "listening": _listening,
    "pronunciation": _pronunciation,
    "dictation": _dictation,
}


def validate_exercise_content(
    template: Any, content: Any, *, allow_asset_refs: bool = False
) -> list[str]:
    """Validate one exercise's ``content`` against its template.

    Returns every error found. Never raises.

    ``allow_asset_refs`` permits ``{"asset": "id"}`` in URL positions, which is
    how content looks before the builder substitutes real media URLs.
    """
    if template == "final_test":
        return [FINAL_TEST_REJECTION]
    if not isinstance(template, str) or template not in _VALIDATORS:
        return [
            f"unknown template {template!r} (allowed: "
            f"{', '.join(VALID_TEMPLATES)})"
        ]
    if not isinstance(content, dict):
        return [f"{template}: 'content' must be an object, got {type(content).__name__}"]
    try:
        return _VALIDATORS[template](content, allow_asset_refs=allow_asset_refs)
    except Exception as exc:  # pragma: no cover - defensive, must never raise
        return [f"{template}: validator crashed on malformed content ({exc!r})"]
