"""Layer 1 — the intermediate representation an LLM is asked to emit.

The IR is deliberately *content only*. Everything positional, infrastructural
or operational is the builder's job, so the model never has to invent it and
can never get it wrong:

  * no ``order`` anywhere — sequence is list position
  * no ``storage_key`` and no absolute URLs — media is referenced by a logical
    id (``{"asset": "vocab_passport_image"}``) that the builder resolves
  * no ``publish_mode`` / ``idempotency_key`` — those are pipeline concerns

Those exclusions are enforced mechanically: every model sets
``extra="forbid"``, so an IR carrying ``order`` or ``storage_key`` fails
validation rather than being silently ignored.
"""
from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

# Templates the pipeline may emit. `final_test` is deliberately absent — see
# templates.FINAL_TEST_REJECTION.
IR_TEMPLATES = (
    "multiple_choice",
    "true_false",
    "fill_blank",
    "matching",
    "reorder",
    "listening",
    "pronunciation",
    "dictation",
)

NonEmptyStr = Annotated[str, Field(min_length=1)]


class _Strict(BaseModel):
    """Reject unknown keys everywhere — this is what stops the LLM smuggling
    in `order`, `storage_key`, `publish_mode` or a hallucinated field."""

    model_config = ConfigDict(extra="forbid")


class AssetRef(_Strict):
    """A logical reference to a media file, resolved by the builder against
    the media manifest. The LLM never sees a URL or a storage key."""

    asset: NonEmptyStr = Field(
        description="Logical asset id, e.g. 'vocab_passport_image'. Must be a "
                    "key in the media manifest at build time.",
    )


class ScriptSegmentIR(_Strict):
    """One timed subtitle line. Seconds, relative to the start of the video."""

    start: float = Field(ge=0, description="Start time in seconds.")
    end: float = Field(gt=0, description="End time in seconds; must be > start.")
    narration_en: NonEmptyStr = Field(description="English narration.")
    subtitle_ar: NonEmptyStr = Field(description="Arabic subtitle.")


class TextComponentIR(_Strict):
    """A markdown prose block."""

    type: Literal["text"]
    content: NonEmptyStr = Field(description="Markdown body.")


class VocabularyItemIR(_Strict):
    word: NonEmptyStr = Field(description="The English term.")
    translation: NonEmptyStr = Field(description="Arabic translation.")
    example_sentence: str = Field(default="", description="Optional usage example.")
    image: AssetRef | None = Field(
        default=None, description="Optional illustration asset."
    )
    audio: AssetRef | None = Field(
        default=None, description="Optional pronunciation audio asset."
    )
    syllables: str = Field(default="", description="e.g. 'pass-port'.")
    pronunciation_tip_ar: str = Field(default="", description="Arabic tip.")
    difficulty: str = Field(default="", description="Free-form marker.")


class VocabularyComponentIR(_Strict):
    type: Literal["vocabulary"]
    items: list[VocabularyItemIR] = Field(min_length=1)


class VideoComponentIR(_Strict):
    type: Literal["video"]
    asset: AssetRef = Field(description="The video file asset.")
    title: str = Field(default="")
    duration: int = Field(ge=1, description="Length in whole seconds.")
    segments: list[ScriptSegmentIR] = Field(
        default_factory=list,
        description="Optional timed subtitles; becomes script.segments.",
    )


class ExerciseIR(_Strict):
    """One exercise. ``content`` stays an open dict because each template has
    its own shape — it is checked by the Layer 2 validators, which is where
    the real strictness lives."""

    template: Literal[IR_TEMPLATES]  # type: ignore[valid-type]
    content: dict[str, Any]
    points: int = Field(default=1, ge=0)


class ExerciseComponentIR(_Strict):
    type: Literal["exercise"]
    exercises: list[ExerciseIR] = Field(min_length=1)


ComponentIR = Annotated[
    Union[
        TextComponentIR,
        VocabularyComponentIR,
        VideoComponentIR,
        ExerciseComponentIR,
    ],
    Field(discriminator="type"),
]


class LessonIR(_Strict):
    """What the LLM returns: the ordered body of one lesson, nothing else.

    Lesson/unit/level metadata is supplied by the pipeline at build time, so
    it is not part of the model's job.
    """

    components: list[ComponentIR] = Field(min_length=1)


def export_ir_json_schema() -> dict:
    """JSON Schema for :class:`LessonIR` — the single source of truth shared
    by the LLM prompt and this validator (Layer 5)."""
    return LessonIR.model_json_schema()
