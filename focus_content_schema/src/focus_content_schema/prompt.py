"""Layer 5 — the LLM prompt contract.

The prompt is *generated from the IR models*, so the schema the model is shown
and the schema the validator enforces cannot drift apart. Change ``ir.py`` and
the prompt changes with it on the next render.
"""
from __future__ import annotations

import json

from .examples import GOLDEN_CONTENT, example_ir
from .ir import export_ir_json_schema
from .templates import FINAL_TEST_REJECTION, VALID_TEMPLATES

_RULES = """\
Hard rules — output that breaks any of these is rejected automatically:

* Emit ONLY the IR JSON object described by the schema. No prose, no markdown
  fence, no commentary.
* Never emit `order`, `storage_key`, `publish_mode` or `idempotency_key`.
  Sequence comes from list position; the build step assigns everything else.
* Never emit a URL. Reference media by logical id: {"asset": "some_id"}.
  Use ids that describe the asset, e.g. "vocab_passport_image".
* Unknown fields are rejected — emit exactly the fields in the schema.
* `final_test` is not available. """ + FINAL_TEST_REJECTION + """

Per-template content rules:

* multiple_choice : >= 2 options, all distinct, `correct_index` an integer
                    inside the options range, non-empty `question`.
* true_false      : `answer` must be a JSON boolean — true/false, never
                    "true" or 1. Non-empty `statement`.
* fill_blank      : `sentence` must contain the blank marker `___`, non-empty
                    `answer`. `options` is optional; omit it and the app builds
                    a word bank automatically. If you do supply it, it must
                    include the answer.
* matching        : >= 2 pairs, and EVERY pair needs both a non-empty `left`
                    and a non-empty `right`. Duplicate `left` values are
                    rejected as ambiguous.
* reorder         : `correct_order` must be a permutation of `words` — exactly
                    the same words, same counts, different order.
* listening       : `audio_url` as an {"asset": ...} reference, non-empty
                    `question`, >= 2 options, `correct_index` in range.
* pronunciation   : non-empty `target_text`; `reference_audio_url` optional,
                    as an {"asset": ...} reference when present.
* dictation       : non-empty `answer`. Optional `hint`,
                    `show_hint_after_attempts` (non-negative integer), and
                    `audio_url` as an {"asset": ...} reference. With no audio
                    the app speaks the answer with text-to-speech.

Video `segments` (optional): seconds, ascending, non-overlapping, and the last
`end` must not exceed the video `duration`. Both `narration_en` and
`subtitle_ar` are required on every segment.
"""


def render_prompt_fragment(
    *,
    include_schema: bool = True,
    include_examples: bool = True,
    include_content_examples: bool = True,
) -> str:
    """Render the schema + rules + few-shot examples as a prompt fragment.

    Drop this into the system prompt of whatever model generates lessons.
    """
    parts: list[str] = [
        "You produce lesson content for Focus Languages, an English-learning "
        "app for Arabic speakers. You return a single JSON object in the "
        "intermediate representation (IR) defined below.",
        "",
        _RULES,
    ]

    if include_schema:
        parts += [
            "",
            "JSON Schema the output must validate against:",
            "```json",
            json.dumps(export_ir_json_schema(), indent=2, ensure_ascii=False),
            "```",
        ]

    if include_content_examples:
        parts += [
            "",
            "Valid `content` for each template:",
            "```json",
            json.dumps(GOLDEN_CONTENT, indent=2, ensure_ascii=False),
            "```",
            "(In the IR, replace any URL with an {\"asset\": \"id\"} "
            "reference.)",
        ]

    if include_examples:
        parts += [
            "",
            "A complete, valid IR document:",
            "```json",
            json.dumps(example_ir(), indent=2, ensure_ascii=False),
            "```",
        ]

    parts += [
        "",
        f"Available templates: {', '.join(VALID_TEMPLATES)}.",
    ]
    return "\n".join(parts)
