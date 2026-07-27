"""Selective translation logic (v2 §1.1).

Rule: a word is translated ONLY if its CEFR level is above the lesson's own
level. Words at/below the lesson level stay plain English. Manual exception
categories (idioms, multi-meaning words, the lesson's target vocabulary) are
always annotated regardless of the automatic rule.
"""
import re

from .models import Lesson, LessonComponent, WordAnnotation, WordLevel

CEFR_ORDER = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}

# Words whose most common meaning differs from frequent alternate senses —
# these get context-specific translation via LLM review (v2 §1.1).
MULTI_MEANING_WORDS = {
    "bank", "book", "spring", "light", "right", "kind", "fair", "mean",
    "park", "play", "run", "watch", "wave", "bat", "bar", "match", "row",
    "leaves", "mine", "duty", "charge", "interest", "note", "figure",
    "present", "object", "subject", "sentence", "current", "change",
}

# Common idioms / fixed expressions — translated as whole phrases even when
# each word is simple (v2 §1.1). Extend freely; the annotate script also
# accepts extra idioms via the LLM pass.
IDIOMS = {
    "piece of cake": "أمر سهل جداً",
    "break the ice": "كسر الجليد / بدء الحديث",
    "once in a while": "من حين لآخر",
    "make up your mind": "اتخذ قرارك",
    "in the long run": "على المدى الطويل",
    "under the weather": "متوعك / مريض قليلاً",
    "give up": "يستسلم / يتخلى عن",
    "look forward to": "يتطلع إلى",
    "get along with": "ينسجم مع",
    "run out of": "ينفد من",
    "come up with": "يبتكر / يتوصل إلى",
    "find out": "يكتشف",
    "take care of": "يعتني بـ",
    "on the other hand": "من ناحية أخرى",
    "as soon as possible": "في أقرب وقت ممكن",
}

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]{1,}")


def lesson_text(lesson: Lesson) -> str:
    """All learner-facing English text of a lesson (text blocks, examples,
    exercise prompts)."""
    parts = []
    for component in lesson.components.all():
        if component.type == LessonComponent.Type.TEXT:
            block = getattr(component, "text_block", None)
            if block:
                parts.append(block.content)
        elif component.type == LessonComponent.Type.VOCABULARY:
            for item in component.vocabulary_items.all():
                parts.append(item.example_sentence)
        elif component.type == LessonComponent.Type.EXERCISE:
            for exercise in component.exercises.all():
                content = exercise.content or {}
                for key in ("question", "statement", "sentence"):
                    if content.get(key):
                        parts.append(str(content[key]))
    return "\n".join(p for p in parts if p)


def tokenize(text: str) -> list[str]:
    return [w.lower() for w in _WORD_RE.findall(text)]


def annotate_lesson(lesson: Lesson, *, replace: bool = True) -> dict:
    """Run the selective-translation rules over one lesson.

    Returns counts: {auto, idiom, multi_meaning, target_vocab, needs_review}.
    Ambiguous cases are stored with needs_review=True so an LLM/human pass can
    finish them without regenerating lesson content (v2 §1.1 migration path).
    """
    level_code = lesson.unit.level.code
    lesson_rank = CEFR_ORDER.get(level_code, 1)

    if replace:
        lesson.word_annotations.all().delete()

    text = lesson_text(lesson)
    lower_text = text.lower()
    counts = {"auto": 0, "idiom": 0, "multi_meaning": 0,
              "target_vocab": 0, "needs_review": 0}
    seen: set[str] = set()

    def add(word, *, kind, cefr="", translation="", needs_review=False):
        key = word.lower()
        if key in seen:
            return
        seen.add(key)
        WordAnnotation.objects.create(
            lesson=lesson, word=word, cefr_level=cefr,
            translation_ar=translation, kind=kind, needs_review=needs_review,
        )
        counts[kind] += 1
        if needs_review:
            counts["needs_review"] += 1

    # 1) Idioms/fixed expressions present in the text — whole-phrase entries.
    for idiom, translation_ar in IDIOMS.items():
        if idiom in lower_text:
            add(idiom, kind=WordAnnotation.Kind.IDIOM,
                translation=translation_ar)

    # 2) Lesson target vocabulary — translated on first appearance even if
    #    technically at-level (these are the words being explicitly taught).
    for component in lesson.components.filter(
        type=LessonComponent.Type.VOCABULARY
    ):
        for item in component.vocabulary_items.all():
            add(item.word, kind=WordAnnotation.Kind.TARGET_VOCAB,
                translation=item.translation)

    # 3) Automatic rule over the word list.
    tokens = set(tokenize(text))
    levels = {
        w.word: w
        for w in WordLevel.objects.filter(word__in=tokens)
    }
    for token in sorted(tokens):
        entry = levels.get(token)
        if entry is None:
            continue  # unknown words stay plain (conservative default)
        word_rank = CEFR_ORDER.get(entry.cefr_level.upper(), 0)
        if word_rank <= lesson_rank:
            continue  # at/below lesson level → plain text, no affordance
        if token in MULTI_MEANING_WORDS:
            # Needs context-specific translation → LLM review pass.
            add(token, kind=WordAnnotation.Kind.MULTI_MEANING,
                cefr=entry.cefr_level, translation=entry.translation_ar,
                needs_review=True)
        else:
            add(token, kind=WordAnnotation.Kind.AUTO,
                cefr=entry.cefr_level, translation=entry.translation_ar,
                needs_review=not entry.translation_ar)

    return counts
