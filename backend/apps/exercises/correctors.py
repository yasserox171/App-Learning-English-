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

import re
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


def _phonetic(text: str) -> str:
    """Lowercase, strip punctuation, and fold 'th' to one symbol so the
    tolerant distance can treat th/s/z (etc.) as near-misses."""
    t = re.sub(r"[^a-z0-9 ]", "", _norm(text))
    return re.sub(r"\s+", " ", t).replace("th", "θ").strip()

# Common Arabic-speaker confusions: substitutions between these pairs cost a
# fraction of a full edit (UX prompt feature 11 — phonetic tolerance).
_TOLERATED = {
    frozenset(p)
    for p in [
        ("θ", "s"), ("θ", "z"), ("θ", "t"),
        ("p", "b"), ("v", "f"), ("g", "j"), ("e", "i"), ("o", "u"),
    ]
}
_TOLERATED_COST = 0.3


def _tolerant_distance(a: str, b: str) -> float:
    """Levenshtein with reduced substitution cost for tolerated confusions."""
    n, m = len(a), len(b)
    prev = [float(j) for j in range(m + 1)]
    for i in range(1, n + 1):
        cur = [float(i)] + [0.0] * m
        for j in range(1, m + 1):
            if a[i - 1] == b[j - 1]:
                sub = 0.0
            elif frozenset((a[i - 1], b[j - 1])) in _TOLERATED:
                sub = _TOLERATED_COST
            else:
                sub = 1.0
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + sub)
        prev = cur
    return prev[m]


def pronunciation_score(spoken: str, target: str) -> float:
    """0..1 similarity, forgiving of common Arabic-speaker mispronunciations."""
    s, t = _phonetic(spoken), _phonetic(target)
    if not t:
        return 0.0
    if s == t:
        return 1.0
    dist = _tolerant_distance(s, t)
    return max(0.0, 1.0 - dist / max(len(s), len(t)))


@register("pronunciation")
class PronunciationCorrector(Corrector):
    """Flexible mic scoring: Levenshtein + Arabic phonetic tolerance.

    Accepts {"spoken_text": str} (or legacy {"transcript": str}); pass mark is
    70%, with partial credit equal to the similarity score."""

    PASS = 0.7

    def check(self, content, answer):
        spoken = answer.get("spoken_text", answer.get("transcript"))
        if spoken is not None:
            score = pronunciation_score(str(spoken), content.get("target_text", ""))
            return score >= self.PASS, score
        # No transcript: lenient credit for having recorded an attempt.
        if answer.get("recorded"):
            return True, 1.0
        return False, 0.0


@register("dictation")
class DictationCorrector(Corrector):
    """Write-what-you-hear: normalized text comparison (case & punctuation
    insensitive)."""

    def check(self, content, answer):
        def clean(text):
            return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", _norm(text))).strip()

        correct = clean(answer.get("answer", "")) == clean(
            content.get("answer", "")
        )
        return correct, 1.0 if correct else 0.0


def answer_text(code: str, content: dict) -> str:
    """Human-readable correct answer for post-attempt reveal / full hints."""
    if code in ("multiple_choice", "listening"):
        options = content.get("options", [])
        idx = content.get("correct_index")
        if isinstance(idx, int) and 0 <= idx < len(options):
            return str(options[idx])
        return ""
    if code == "true_false":
        return "true" if content.get("answer") else "false"
    if code in ("fill_blank", "dictation"):
        return str(content.get("answer", ""))
    if code == "matching":
        return "، ".join(
            f"{p.get('left')} → {p.get('right')}"
            for p in content.get("pairs", [])
        )
    if code == "reorder":
        return " ".join(str(w) for w in content.get("correct_order", []))
    if code == "pronunciation":
        return str(content.get("target_text", ""))
    return ""


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
