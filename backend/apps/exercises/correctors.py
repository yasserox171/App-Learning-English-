"""Exercise correctors (master prompt §9).

One corrector per template ``code``. Each takes the exercise ``content`` and
the user's ``answer`` and returns ``(is_correct, fraction)`` where fraction is
0..1 (supports partial credit). Adding a new template later = a new corrector
here + a Flutter widget — no DB changes.

Expected answer shapes (sent by the client to the attempt endpoint):
    multiple_choice : {"selected_index": int}
    true_false      : {"answer": bool}
    fill_blank      : {"answer": str}
    matching        : {"pairs": [{"left": str, "right": str}, ...]}
    reorder         : {"order": [str, ...]}
    listening       : {"selected_index": int}
    pronunciation   : {"transcript": str}   (or {"recorded": true})
    final_test      : {"answers": {exercise_id: answer_obj, ...}}
"""
from __future__ import annotations

from typing import Tuple

Result = Tuple[bool, float]

_REGISTRY: dict[str, "Corrector"] = {}


def register(code):
    def deco(cls):
        _REGISTRY[code] = cls()
        return cls

    return deco


def get_corrector(code: str) -> "Corrector":
    try:
        return _REGISTRY[code]
    except KeyError:
        raise ValueError(f"No corrector registered for template '{code}'")


def _norm(text) -> str:
    return str(text).strip().casefold()


class Corrector:
    def check(self, content: dict, answer: dict) -> Result:
        raise NotImplementedError


@register("multiple_choice")
class MultipleChoiceCorrector(Corrector):
    def check(self, content, answer):
        selected = answer.get("selected_index")
        correct = selected == content.get("correct_index")
        return correct, 1.0 if correct else 0.0


@register("true_false")
class TrueFalseCorrector(Corrector):
    def check(self, content, answer):
        correct = bool(answer.get("answer")) == bool(content.get("answer"))
        return correct, 1.0 if correct else 0.0


@register("fill_blank")
class FillBlankCorrector(Corrector):
    def check(self, content, answer):
        correct = _norm(answer.get("answer", "")) == _norm(content.get("answer", ""))
        return correct, 1.0 if correct else 0.0


@register("matching")
class MatchingCorrector(Corrector):
    def check(self, content, answer):
        expected = {
            (_norm(p["left"]), _norm(p["right"])) for p in content.get("pairs", [])
        }
        given = {
            (_norm(p.get("left")), _norm(p.get("right")))
            for p in answer.get("pairs", [])
        }
        if not expected:
            return False, 0.0
        matched = len(expected & given)
        fraction = matched / len(expected)
        return fraction == 1.0, fraction


@register("reorder")
class ReorderCorrector(Corrector):
    def check(self, content, answer):
        expected = [_norm(w) for w in content.get("correct_order", [])]
        given = [_norm(w) for w in answer.get("order", [])]
        if not expected:
            return False, 0.0
        matches = sum(
            1 for i, w in enumerate(expected) if i < len(given) and given[i] == w
        )
        fraction = matches / len(expected)
        return given == expected, fraction


@register("listening")
class ListeningCorrector(Corrector):
    def check(self, content, answer):
        selected = answer.get("selected_index")
        correct = selected == content.get("correct_index")
        return correct, 1.0 if correct else 0.0


@register("pronunciation")
class PronunciationCorrector(Corrector):
    """MVP: simplified. Exact-ish transcript match, else accept a recording.

    Advanced audio analysis is a later phase (master prompt §9).
    """

    def check(self, content, answer):
        transcript = answer.get("transcript")
        if transcript is not None:
            correct = _norm(transcript) == _norm(content.get("target_text", ""))
            return correct, 1.0 if correct else 0.0
        # No transcript: lenient credit for having recorded an attempt.
        if answer.get("recorded"):
            return True, 1.0
        return False, 0.0


@register("final_test")
class FinalTestCorrector(Corrector):
    """Aggregate corrector: runs each referenced exercise's own corrector."""

    def check(self, content, answer):
        # Imported lazily to avoid a circular import at module load.
        from .models import Exercise

        exercise_ids = content.get("exercise_ids", [])
        answers = answer.get("answers", {})
        if not exercise_ids:
            return False, 0.0

        exercises = {
            str(e.id): e
            for e in Exercise.objects.filter(id__in=exercise_ids).select_related(
                "template"
            )
        }
        total = len(exercise_ids)
        acc = 0.0
        for ex_id in exercise_ids:
            ex = exercises.get(str(ex_id))
            if ex is None:
                continue
            sub_answer = answers.get(str(ex_id), {})
            corrector = get_corrector(ex.template.code)
            _, frac = corrector.check(ex.content, sub_answer)
            acc += frac
        fraction = acc / total
        return fraction == 1.0, fraction
