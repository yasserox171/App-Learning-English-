"""Exercise serializers (master prompt §9, §10).

Student-facing content is sanitized: correct answers are never sent to the
client. Correction happens server-side via the attempt endpoint (Phase 4).
"""
from rest_framework import serializers

from .models import Exercise, ExerciseAttempt, ExerciseTemplate

# Keys that reveal the answer and must be stripped from student-facing content.
ANSWER_KEYS = ("correct_index", "answer", "correct_order")

# Fallback distractors when a lesson has too few vocabulary words.
_FILLER_WORDS = ["the", "a", "is", "you", "it", "and", "to", "in"]


def _lesson_vocab_words(exercise):
    """All vocabulary words in the exercise's lesson (for fill_blank options)."""
    try:
        lesson = exercise.component.lesson
    except Exception:
        return []
    from apps.content.models import VocabularyItem

    return list(
        VocabularyItem.objects.filter(component__lesson=lesson)
        .values_list("word", flat=True)
    )


class ExerciseTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExerciseTemplate
        fields = ("id", "code", "name", "content_schema", "is_active")


class ExerciseSerializer(serializers.ModelSerializer):
    """Sanitized exercise for students (no answer fields)."""

    template_code = serializers.CharField(source="template.code", read_only=True)
    content = serializers.SerializerMethodField()

    class Meta:
        model = Exercise
        fields = ("id", "template_code", "content", "points", "order")

    def get_content(self, obj):
        import random

        content = dict(obj.content or {})
        code = obj.template.code if obj.template_id else ""

        # listening: tell the client which word to speak (TTS), without
        # exposing the correct index.
        if code == "listening":
            options = content.get("options") or []
            idx = content.get("correct_index")
            if isinstance(idx, int) and 0 <= idx < len(options):
                content["audio_text"] = options[idx]

        # dictation: the client SPEAKS the answer (that's the exercise) but
        # never sees it in text form.
        if code == "dictation" and not content.get("audio_url"):
            content["audio_text"] = str(content.get("answer", ""))

        # fill_blank: provide a tappable word bank (answer + distractors).
        if code == "fill_blank" and not content.get("options"):
            answer = str(content.get("answer", "")).strip()
            pool = [
                w for w in _lesson_vocab_words(obj)
                if w.strip().casefold() != answer.casefold()
            ]
            random.shuffle(pool)
            distractors = pool[:2]
            i = 0
            while len(distractors) < 2 and i < len(_FILLER_WORDS):
                w = _FILLER_WORDS[i]
                if w.casefold() != answer.casefold() and w not in distractors:
                    distractors.append(w)
                i += 1
            if answer:
                options = [answer, *distractors]
                random.shuffle(options)
                content["options"] = options

        for key in ANSWER_KEYS:
            content.pop(key, None)
        return content


class ExerciseAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExerciseAttempt
        fields = ("id", "exercise", "answer", "is_correct", "score", "attempted_at")
        read_only_fields = ("is_correct", "score", "attempted_at")
