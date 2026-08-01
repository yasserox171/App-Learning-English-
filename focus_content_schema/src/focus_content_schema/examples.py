"""Known-good exercise content, one per template.

Seven of these are lifted verbatim from the Focus Languages seed command
(``backend/apps/common/management/commands/seed.py``), which is the only real
reference content in the project.

Two deliberate divergences, both documented rather than hidden:

1. ``listening.audio_url`` and ``pronunciation.reference_audio_url`` are
   relative in the seed (``"samples/airport-announcement.mp3"``). They predate
   the media upload API. The pipeline now produces absolute URLs, and the
   Layer 2 validators require them, so the examples here use absolute URLs.
   ``SEEDED_RELATIVE_MEDIA`` keeps the original values so a test can assert the
   old form is rejected.

2. ``dictation`` has no example anywhere in the codebase — the seed skips it
   and ``apps/common/tests.py`` asserts it is the one template without sample
   data. The shape here is derived from its seeded ``content_schema`` row and
   documented in ``templates._dictation``.
"""
from copy import deepcopy

MEDIA_BASE = "http://84.8.223.62/media"

GOLDEN_CONTENT: dict[str, dict] = {
    "multiple_choice": {
        "question": "What does 'Airport' mean?",
        "options": ["مدرسة", "مطار", "مستشفى"],
        "correct_index": 1,
    },
    "true_false": {
        "statement": "A boarding pass is needed to fly.",
        "answer": True,
    },
    "fill_blank": {
        "sentence": "I ___ a passenger.",
        "answer": "am",
    },
    "matching": {
        "pairs": [
            {"left": "Airport", "right": "مطار"},
            {"left": "Passport", "right": "جواز السفر"},
        ]
    },
    "reorder": {
        "words": ["am", "I", "a", "passenger"],
        "correct_order": ["I", "am", "a", "passenger"],
    },
    "listening": {
        # seed has "samples/airport-announcement.mp3" (relative) — see above
        "audio_url": f"{MEDIA_BASE}/audio/airport-announcement.mp3",
        "question": "Which gate is mentioned?",
        "options": ["A1", "B2", "C3"],
        "correct_index": 1,
    },
    "pronunciation": {
        "target_text": "Boarding pass",
        # seed has "samples/boarding-pass.mp3" (relative) — see above
        "reference_audio_url": f"{MEDIA_BASE}/audio/boarding-pass.mp3",
    },
    "dictation": {
        # No codebase reference; shape settled by this package.
        "answer": "I am a passenger.",
        "hint": "Four words.",
        "show_hint_after_attempts": 2,
    },
}

# The original seed values, kept so tests can prove the strict absolute-URL
# rule rejects them.
SEEDED_RELATIVE_MEDIA = {
    "listening": "samples/airport-announcement.mp3",
    "pronunciation": "samples/boarding-pass.mp3",
}


def golden_content(template: str) -> dict:
    """A deep copy of one golden fixture, safe for the caller to mutate."""
    return deepcopy(GOLDEN_CONTENT[template])


def example_ir() -> dict:
    """A complete, valid IR document used as the few-shot example in the
    prompt fragment and as a fixture in the tests.

    Deep-copied on every call: callers routinely tweak the result, and sharing
    references with GOLDEN_CONTENT would let one caller silently corrupt the
    fixtures for everyone else in the process.
    """
    return deepcopy({
        "components": [
            {
                "type": "text",
                "content": (
                    "# At the airport\n\n"
                    "You need a passport and a boarding pass to fly."
                ),
            },
            {
                "type": "video",
                "asset": {"asset": "lesson_intro_video"},
                "title": "Checking in",
                "duration": 120,
                "segments": [
                    {
                        "start": 0,
                        "end": 4.5,
                        "narration_en": "Good morning, may I see your passport?",
                        "subtitle_ar": "صباح الخير، هل يمكنني رؤية جواز سفرك؟",
                    },
                    {
                        "start": 4.5,
                        "end": 9,
                        "narration_en": "Here you are.",
                        "subtitle_ar": "تفضل.",
                    },
                ],
            },
            {
                "type": "vocabulary",
                "items": [
                    {
                        "word": "passport",
                        "translation": "جواز السفر",
                        "example_sentence": "Show your passport at the gate.",
                        "image": {"asset": "vocab_passport_image"},
                        "audio": {"asset": "vocab_passport_audio"},
                        "syllables": "pass-port",
                    },
                    {
                        "word": "boarding pass",
                        "translation": "بطاقة الصعود",
                    },
                ],
            },
            {
                "type": "exercise",
                "exercises": [
                    {
                        "template": "multiple_choice",
                        "content": GOLDEN_CONTENT["multiple_choice"],
                        "points": 1,
                    },
                    {
                        "template": "fill_blank",
                        "content": GOLDEN_CONTENT["fill_blank"],
                    },
                    {
                        "template": "listening",
                        "content": {
                            # Unresolved reference — the builder substitutes it.
                            "audio_url": {"asset": "gate_announcement_audio"},
                            "question": "Which gate is mentioned?",
                            "options": ["A1", "B2", "C3"],
                            "correct_index": 1,
                        },
                    },
                ],
            },
        ]
    })


def example_media_manifest() -> dict:
    """Manifest matching :func:`example_ir`, shaped like real upload API
    responses."""
    return deepcopy({
        "lesson_intro_video": {
            "storage_key": "videos/9f2a1c04e7b3.mp4",
            "url": f"{MEDIA_BASE}/videos/9f2a1c04e7b3.mp4",
            "kind": "video",
        },
        "vocab_passport_image": {
            "storage_key": "images/ebf4f635a17d.png",
            "url": f"{MEDIA_BASE}/images/ebf4f635a17d.png",
            "kind": "image",
        },
        "vocab_passport_audio": {
            "storage_key": "audio/3c1d9a77bb02.mp3",
            "url": f"{MEDIA_BASE}/audio/3c1d9a77bb02.mp3",
            "kind": "audio",
        },
        "gate_announcement_audio": {
            "storage_key": "audio/77aa20b4cc19.mp3",
            "url": f"{MEDIA_BASE}/audio/77aa20b4cc19.mp3",
            "kind": "audio",
        },
    })
