"""focus_content_schema — validation and payload building between an LLM's
raw content output and the Focus Languages import API.

Five layers:

    1. ir            — what the LLM emits (content only, no order/URLs/keys)
    2. templates     — strict per-template validation of exercise content
    3. builder       — IR + media manifest -> import payload
    4. payload       — the final gate before the HTTP call
    5. prompt        — JSON Schema + few-shot fragment for the LLM prompt

Typical use::

    from focus_content_schema import (
        validate_ir_dict, build_import_payload, validate_payload,
    )

    errors = validate_ir_dict(llm_output)
    if errors:
        raise ValueError(errors)

    payload = build_import_payload(
        llm_output, manifest,
        level="A1",
        unit={"title": "Travel"},
        lesson={"title": "At the airport"},
        idempotency_key="batch-2026-07/A1/lesson-01",
    )

    errors = validate_payload(payload)      # last gate
    if errors:
        raise ValueError(errors)
"""
from .builder import BuildError, build_import_payload
from .examples import GOLDEN_CONTENT, example_ir, example_media_manifest
from .ir import (
    AssetRef,
    ExerciseComponentIR,
    ExerciseIR,
    LessonIR,
    ScriptSegmentIR,
    TextComponentIR,
    VideoComponentIR,
    VocabularyComponentIR,
    VocabularyItemIR,
    export_ir_json_schema,
)
from .payload import (
    VALID_COMPONENT_TYPES,
    VALID_LEVELS,
    validate_ir_dict,
    validate_payload,
)
from .prompt import render_prompt_fragment
from .templates import (
    FINAL_TEST_REJECTION,
    VALID_TEMPLATES,
    is_absolute_url,
    validate_exercise_content,
)

__version__ = "1.0.0"

__all__ = [
    "AssetRef",
    "BuildError",
    "ExerciseComponentIR",
    "ExerciseIR",
    "FINAL_TEST_REJECTION",
    "GOLDEN_CONTENT",
    "LessonIR",
    "ScriptSegmentIR",
    "TextComponentIR",
    "VALID_COMPONENT_TYPES",
    "VALID_LEVELS",
    "VALID_TEMPLATES",
    "VideoComponentIR",
    "VocabularyComponentIR",
    "VocabularyItemIR",
    "build_import_payload",
    "example_ir",
    "example_media_manifest",
    "export_ir_json_schema",
    "is_absolute_url",
    "render_prompt_fragment",
    "validate_exercise_content",
    "validate_ir_dict",
    "validate_payload",
]
